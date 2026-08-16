"""ChemAI Backend — 答题卡 OCR 判卷编排与确定性判分

覆盖「OCR 识别 → 学生信息抽取 → 逐题判分 → 教师确认 → 回写 StudentAnswer →
触发障碍诊断」的完整后端闭环。判分纯确定性：客观题选项匹配 + 填空题归一化
比对，主观题/LLM 判分后置（见 ADR-0006）。
"""

import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Class,
    Exam,
    ExamRecord,
    GradingResult,
    Grade,
    Judgment,
    OCRTask,
    OCRTaskStatus,
    RecordType,
    Student,
    StudentAnswer,
    UploadSession,
    UploadSessionStatus,
)
from app.services.diagnosis_engine.background import diagnose_answers_background
from app.services.ocr_provider import OCRProvider, get_ocr_provider

logger = logging.getLogger(__name__)

# 识别文本低于该长度视为「识别内容不足」
_MIN_RESULT_LENGTH = 5


# ── 化学/作答规范化（确定性判分基础） ──────────────────


def _unicode_char_map() -> dict[int, str]:
    """构建 Unicode 规范化映射：全角→半角、下标/上标数字→ASCII 数字"""
    m: dict[int, str] = {}
    # 全角数字/字母 → 半角
    for code in range(0xFF10, 0xFF1A):  # ０-９
        m[code] = chr(code - 0xFF10 + ord("0"))
    for code in range(0xFF21, 0xFF3B):  # Ａ-Ｚ
        m[code] = chr(code - 0xFF21 + ord("A"))
    for code in range(0xFF41, 0xFF5B):  # ａ-ｚ
        m[code] = chr(code - 0xFF41 + ord("a"))
    # 下标数字 → ASCII（如 H₂O → H2O）
    for i, ch in enumerate("₀₁₂₃₄₅₆₇₈₉"):
        m[ord(ch)] = str(i)
    # 上标数字 → ASCII（如 CO² → CO2）
    for i, ch in enumerate("⁰¹²³⁴⁵⁶⁷⁸⁹"):
        m[ord(ch)] = str(i)
    return m


_CHAR_MAP = _unicode_char_map()


def normalize_answer(text: str | None) -> str:
    """规范化作答：Unicode 下标/全角 → ASCII、去空白、统一小写

    用于填空题/化学式的确定性比对。保留 +/= 等化学符号，不删除小数点。
    """
    if text is None:
        return ""
    s = str(text).translate(_CHAR_MAP)
    s = "".join(s.split())
    return s.lower()


def extract_option(text: str | None) -> str | None:
    """从作答文本抽取首个选项字母（A-D），无法抽取返回 None"""
    if text is None:
        return None
    s = str(text).translate(_CHAR_MAP)
    for ch in s:
        upper = ch.upper()
        if upper in "ABCD":
            return upper
    return None


def grade_question(
    question_type: str,
    student_answer: str | None,
    correct_answer: str | None,
    confidence: float | None = None,
    confidence_threshold: float | None = None,
) -> Judgment:
    """对单题做确定性判分

    Args:
        question_type: 题型（choice / fill / calc / ...）
        student_answer: OCR 抽取的学生作答
        correct_answer: 参考答案
        confidence: OCR 置信度，低于阈值判「待复核」
        confidence_threshold: 置信度阈值（默认取配置）

    Returns:
        Judgment 三态结论
    """
    threshold = confidence_threshold if confidence_threshold is not None else settings.ocr_confidence_threshold
    if confidence is not None and confidence < threshold:
        return Judgment.REVIEW_REQUIRED

    if normalize_answer(student_answer) == "":
        return Judgment.REVIEW_REQUIRED
    if normalize_answer(correct_answer) == "":
        return Judgment.REVIEW_REQUIRED

    qtype = (question_type or "choice").lower()
    if qtype == "choice":
        stu_opt = extract_option(student_answer)
        cor_opt = extract_option(correct_answer)
        if stu_opt is None or cor_opt is None:
            return Judgment.REVIEW_REQUIRED
        return Judgment.CORRECT if stu_opt == cor_opt else Judgment.INCORRECT

    if qtype == "fill":
        return (
            Judgment.CORRECT
            if normalize_answer(student_answer) == normalize_answer(correct_answer)
            else Judgment.INCORRECT
        )

    # 主观题（calc/experiment/inference）不在确定性判分范围
    return Judgment.REVIEW_REQUIRED


# ── 学生信息抽取 ─────────────────────────────────────


def parse_answer_sheet(ocr_text: str) -> dict:
    """从 OCR 文本解析姓名、学号与逐题作答（行式约定）

    约定每行格式：`姓名: 张三` / `学号: 20250001` / `1. A` 或 `1、A`。
    """
    result: dict = {"name": None, "student_no": None, "answers": []}
    if not ocr_text:
        return result

    for raw_line in ocr_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = re.search(r"姓名\s*[:：]\s*(\S+)", line)
        if m:
            result["name"] = m.group(1).strip()
            continue
        m = re.search(r"学号\s*[:：]\s*(\S+)", line)
        if m:
            result["student_no"] = m.group(1).strip()
            continue
        m = re.match(r"(\d+)\s*[.、．:：)）\]】]\s*(.*)", line)
        if m:
            result["answers"].append(
                {"question_no": int(m.group(1)), "answer": m.group(2).strip()}
            )

    return result


def extract_student_info(db: Session, school_id: str | None, ocr_text: str):
    """从 OCR 文本抽取学生姓名并在本校匹配，返回 (Student, Class) 或 (None, None)

    学生无学号字段，按姓名在本校（Student → Class → Grade → School 链）匹配。
    """
    parsed = parse_answer_sheet(ocr_text)
    name = parsed.get("name")
    if not name:
        return None, None

    query = db.query(Student)
    if school_id:
        query = (
            query.join(Class, Student.class_id == Class.id)
            .join(Grade, Class.grade_id == Grade.id)
            .filter(Grade.school_id == school_id)
        )
    name_normalized = name.replace(" ", "")
    for student in query.all():
        if (student.name or "").replace(" ", "") == name_normalized:
            return student, student.class_
    return None, None


# ── 参考答案来源 ─────────────────────────────────────


def build_answer_key(db: Session, session: UploadSession) -> list[dict]:
    """构建参考答案列表（教师录入优先，其次题库匹配）

    返回项格式：`{"question_no", "question_id", "question_type", "correct_answer"}`。
    """
    # 教师录入优先
    if session.answer_key:
        key: list[dict] = []
        for item in session.answer_key:
            key.append(
                {
                    "question_no": item.get("question_no"),
                    "question_id": item.get("question_id"),
                    "question_type": item.get("type") or "fill",
                    "correct_answer": item.get("correct_answer", ""),
                }
            )
        return key

    # 题库匹配（exam_id → 题库题目答案）
    if session.exam_id:
        exam = db.query(Exam).filter(Exam.id == session.exam_id).first()
        if not exam:
            return []
        items: list[tuple[int, object]] = []
        for eqs in exam.exam_question_sets:
            qs = eqs.question_set
            if not qs or not qs.items:
                continue
            for it in qs.items:
                if it.question:
                    items.append((it.sort_order or 0, it.question))
        items.sort(key=lambda x: x[0])
        key = []
        for idx, (_, q) in enumerate(items, start=1):
            key.append(
                {
                    "question_no": idx,
                    "question_id": q.id,
                    "question_type": q.type.value if q.type else "choice",
                    "correct_answer": (q.answer_i18n or {}).get("zh", "") if q.answer_i18n else "",
                }
            )
        return key

    return []


# ── 判卷编排 ────────────────────────────────────────


def grade_session(
    db: Session, session: UploadSession, ocr_text: str, confidence: float | None = None
) -> list[GradingResult]:
    """按参考答案对 OCR 文本逐题判分，生成 GradingResult 列表（未落库）"""
    parsed = parse_answer_sheet(ocr_text)
    answer_key = build_answer_key(db, session)
    key_by_no = {
        item["question_no"]: item for item in answer_key if item["question_no"] is not None
    }

    results: list[GradingResult] = []
    for ans in parsed["answers"]:
        no = ans["question_no"]
        key_item = key_by_no.get(no)
        correct_answer = key_item["correct_answer"] if key_item else ""
        question_type = key_item["question_type"] if key_item else "choice"
        question_id = key_item["question_id"] if key_item else None

        results.append(
            GradingResult(
                session_id=session.id,
                school_id=session.school_id,
                student_id=session.student_id,
                question_id=question_id,
                question_no=no,
                student_answer_text=ans["answer"],
                normalized_answer=normalize_answer(ans["answer"]),
                correct_answer_text=correct_answer,
                judgment=grade_question(
                    question_type, ans["answer"], correct_answer, confidence
                ),
                ocr_confidence=confidence,
                confirmed=False,
            )
        )

    # 参考答案中存在但 OCR 未抽到的题，补一条「待复核」，确保逐题覆盖
    parsed_nos = {ans["question_no"] for ans in parsed["answers"]}
    for no, key_item in key_by_no.items():
        if no in parsed_nos:
            continue
        results.append(
            GradingResult(
                session_id=session.id,
                school_id=session.school_id,
                student_id=session.student_id,
                question_id=key_item["question_id"],
                question_no=no,
                student_answer_text="",
                normalized_answer="",
                correct_answer_text=key_item["correct_answer"],
                judgment=Judgment.REVIEW_REQUIRED,
                ocr_confidence=confidence,
                confirmed=False,
            )
        )
    return results


def process_ocr_task(db: Session, task: OCRTask, provider: OCRProvider) -> None:
    """处理单个 OCR 任务：识别 → 学生抽取 → 判分 → 回写会话状态"""
    session = (
        db.query(UploadSession).filter(UploadSession.id == task.session_id).first()
    )
    if not session:
        task.status = OCRTaskStatus.FAILED
        task.error_message = "关联会话不存在"
        db.commit()
        return

    task.status = OCRTaskStatus.PROCESSING
    session.transition_to(UploadSessionStatus.GRADING)
    db.commit()

    try:
        # 优先取带置信度的识别结果；不支持置信度的提供方回退到纯文本识别
        if hasattr(provider, "recognize_with_confidence"):
            result_text, confidence = provider.recognize_with_confidence(session.file_path)
        else:
            result_text = provider.recognize(session.file_path)
            confidence = None
    except Exception as e:  # OCRNotConfiguredError / 网络 / 接口错误
        logger.exception("OCR 识别失败 task=%s", task.id)
        task.status = OCRTaskStatus.FAILED
        task.error_message = f"OCR 识别失败: {e}"
        session.transition_to(UploadSessionStatus.ERROR)
        db.commit()
        return

    if not result_text or len(result_text.strip()) < _MIN_RESULT_LENGTH:
        task.status = OCRTaskStatus.FAILED
        task.error_message = "识别内容不足，请改用人工录入"
        session.transition_to(UploadSessionStatus.ERROR)
        db.commit()
        return

    task.result_text = result_text
    task.status = OCRTaskStatus.DONE

    # 学生信息抽取
    student, cls = extract_student_info(db, session.school_id, result_text)
    if student:
        session.student_id = student.id
        session.class_id = cls.id if cls else session.class_id

    # 逐题判分（低置信度 → 待复核，见 grade_question）
    results = grade_session(db, session, result_text, confidence=confidence)
    db.add_all(results)
    session.transition_to(UploadSessionStatus.GRADED)
    db.commit()


def process_pending_ocr_tasks(db: Session, provider: OCRProvider | None = None) -> int:
    """抢占所有 pending 任务并顺序处理（供调度器 interval job 调用）"""
    if provider is None:
        provider = get_ocr_provider()
    tasks = (
        db.query(OCRTask)
        .filter(OCRTask.status == OCRTaskStatus.PENDING)
        .order_by(OCRTask.created_at)
        .all()
    )
    for task in tasks:
        process_ocr_task(db, task, provider)
    return len(tasks)


# ── 确认入库 ────────────────────────────────────────


def confirm_session_results(
    db: Session, session: UploadSession, overrides: list[dict] | None = None
) -> dict:
    """教师确认/修正判卷结果，回写 StudentAnswer 并触发障碍诊断

    Args:
        overrides: 逐题覆盖，格式 `[{"question_id"/"question_no": ..., "judgment": ...}]`

    Returns:
        {"written", "skipped", "answer_ids"}
    """
    results = (
        db.query(GradingResult).filter(GradingResult.session_id == session.id).all()
    )

    overrides_by_key: dict[tuple, str] = {}
    for ov in overrides or []:
        judgment = ov.get("judgment")
        if ov.get("question_id"):
            overrides_by_key[("id", ov["question_id"])] = judgment
        elif ov.get("question_no") is not None:
            overrides_by_key[("no", ov["question_no"])] = judgment

    exam_record: ExamRecord | None = None
    answer_ids: list[str] = []
    written = 0
    skipped = 0

    for r in results:
        # 覆盖项可按 question_id 或 question_no 定位，两者都尝试匹配
        override_judgment = None
        if r.question_id and ("id", r.question_id) in overrides_by_key:
            override_judgment = overrides_by_key[("id", r.question_id)]
        elif r.question_no is not None and ("no", r.question_no) in overrides_by_key:
            override_judgment = overrides_by_key[("no", r.question_no)]
        if override_judgment is not None:
            try:
                r.judgment = Judgment(override_judgment)
            except (ValueError, KeyError):
                pass
        r.confirmed = True

        # 待复核、缺题目/学生/班级/试卷时不可写库，保留人工处理
        if r.judgment == Judgment.REVIEW_REQUIRED:
            skipped += 1
            continue
        if (
            not r.question_id
            or not session.student_id
            or not session.class_id
            or not session.exam_id
        ):
            skipped += 1
            continue

        # 归组班级级 ExamRecord
        if exam_record is None:
            exam_record = (
                db.query(ExamRecord)
                .filter(
                    ExamRecord.exam_id == session.exam_id,
                    ExamRecord.class_id == session.class_id,
                    ExamRecord.type == RecordType.EXAM,
                )
                .first()
            )
            if not exam_record:
                # 班级级考试记录：学生粒度由 StudentAnswer.student_id 承载，EXAM 记录本身不绑定单个学生
                exam_record = ExamRecord(
                    exam_id=session.exam_id,
                    class_id=session.class_id,
                    type=RecordType.EXAM,
                    taken_at=datetime.now(timezone.utc),
                )
                db.add(exam_record)
                db.flush()

        answer = StudentAnswer(
            exam_record_id=exam_record.id,
            student_id=session.student_id,
            question_id=r.question_id,
            student_answer=r.student_answer_text,
            is_correct=(r.judgment == Judgment.CORRECT),
        )
        db.add(answer)
        db.flush()
        answer_ids.append(answer.id)
        written += 1

    session.transition_to(UploadSessionStatus.DONE)
    db.commit()

    # 触发障碍诊断（复用既有后台诊断，独立会话）
    if answer_ids and session.student_id:
        diagnose_answers_background(session.student_id, answer_ids)

    return {"written": written, "skipped": skipped, "answer_ids": answer_ids}
