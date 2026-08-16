"""学情预警引擎 — EarlyWarningService

检测三类学习异常（连续未登录 / 成绩下滑 / 错题率过高），生成预警记录、
去重并识别应通知的家长。供 /api/warning 端点与 APScheduler 定时任务复用。

预警级别判定（阈值常量，遵循设计文档 31 §5.3「宁误报不漏报」）：
    no_login:        连续未登录 >= 3 天 → warning
    score_drop:      成绩降幅 >= 10% → warning；>= 20% → critical
    high_error_rate: 错误率 >= 50% → info；>= 70% → warning
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    ExamRecord,
    RecordType,
    Student,
    StudentAnswer,
    StudentParentBinding,
    WarningLevel,
    WarningLog,
    WarningStatus,
    WarningType,
)
from app.utils.time import as_aware


class EarlyWarningService:
    """学情预警引擎（无状态，方法显式接收 db 会话）"""

    NO_LOGIN_DAYS = 3
    SCORE_DROP_THRESHOLD = 0.1
    SCORE_DROP_CRITICAL_THRESHOLD = 0.2
    HIGH_ERROR_RATE_THRESHOLD = 0.5
    HIGH_ERROR_RATE_WARNING_THRESHOLD = 0.7

    def check_all_warnings(self, db: Session) -> list[WarningLog]:
        """遍历所有 status=approved 的学生，检测三类预警并落库

        Args:
            db: SQLAlchemy 会话

        Returns:
            本次新创建的预警记录列表（去重后）
        """
        students = db.query(Student).filter(Student.status == "approved").all()
        created: list[WarningLog] = []
        for student in students:
            for trigger in self._detect_triggers(db, student):
                log = self._create_warning(db, student, trigger)
                if log is not None:
                    created.append(log)
        db.commit()
        return created

    # ── 检测 ──────────────────────────────────────────────

    def _detect_triggers(self, db: Session, student: Student) -> list[dict]:
        """按顺序检测三类预警，返回触发的 trigger 描述列表"""
        triggers: list[dict] = []
        now = datetime.now(timezone.utc)

        no_login = self._detect_no_login(student, now)
        if no_login:
            triggers.append(no_login)

        score_drop = self._detect_score_drop(db, student)
        if score_drop:
            triggers.append(score_drop)

        high_error_rate = self._detect_high_error_rate(db, student)
        if high_error_rate:
            triggers.append(high_error_rate)

        return triggers

    def _detect_no_login(self, student: Student, now: datetime) -> dict | None:
        """连续未登录：last_practice_at（为空则 created_at）距今 >= 3 天"""
        last_active = as_aware(student.last_practice_at) or as_aware(student.created_at)
        if last_active is None:
            return None
        days = (now - last_active).days
        if days < self.NO_LOGIN_DAYS:
            return None
        return {
            "warning_type": WarningType.NO_LOGIN,
            "level": WarningLevel.WARNING,
            "title": "连续未登录",
            "content": f"学生 {student.name} 已 {days} 天未使用系统",
            "data": {"days": days},
        }

    def _detect_score_drop(self, db: Session, student: Student) -> dict | None:
        """成绩下滑：最近两次 type=exam 考试记录的正确率降幅 >= 10%"""
        accuracies = self._student_batch_accuracies(db, student.id, record_type=RecordType.EXAM)
        if len(accuracies) < 2:
            return None
        # accuracies 已按 taken_at 降序：[0]=最近, [1]=前次
        recent_accuracy, prev_accuracy = accuracies[0][1], accuracies[1][1]
        if prev_accuracy == 0:
            return None  # 前次为 0 无法计算有效降幅
        drop_rate = (prev_accuracy - recent_accuracy) / prev_accuracy
        if drop_rate < self.SCORE_DROP_THRESHOLD:
            return None
        level = (
            WarningLevel.CRITICAL
            if drop_rate >= self.SCORE_DROP_CRITICAL_THRESHOLD
            else WarningLevel.WARNING
        )
        return {
            "warning_type": WarningType.SCORE_DROP,
            "level": level,
            "title": "成绩下滑",
            "content": f"学生 {student.name} 成绩较上次下滑 {drop_rate:.0%}",
            "data": {
                "prev_accuracy": round(prev_accuracy, 4),
                "recent_accuracy": round(recent_accuracy, 4),
                "drop_rate": round(drop_rate, 4),
            },
        }

    def _detect_high_error_rate(self, db: Session, student: Student) -> dict | None:
        """错题率过高：最近一次作答批次（不限类型）错误率 >= 50%"""
        accuracies = self._student_batch_accuracies(db, student.id, record_type=None)
        if not accuracies:
            return None
        _, recent_accuracy = accuracies[0]
        error_rate = 1 - recent_accuracy
        if error_rate < self.HIGH_ERROR_RATE_THRESHOLD:
            return None
        level = (
            WarningLevel.WARNING
            if error_rate >= self.HIGH_ERROR_RATE_WARNING_THRESHOLD
            else WarningLevel.INFO
        )
        return {
            "warning_type": WarningType.HIGH_ERROR_RATE,
            "level": level,
            "title": "错题率过高",
            "content": f"学生 {student.name} 最近一次作答错题率 {error_rate:.0%}",
            "data": {"error_rate": round(error_rate, 4)},
        }

    # ── 数据查询 ──────────────────────────────────────────

    def _student_batch_accuracies(
        self, db: Session, student_id: str, record_type: RecordType | None
    ) -> list[tuple[ExamRecord, float]]:
        """学生各作答批次的 (记录, 正确率)，按 taken_at 降序

        record_type 为 None 时取全部批次（考试+练习），否则仅该类型。
        """
        answers = (
            db.query(StudentAnswer, ExamRecord)
            .join(ExamRecord, StudentAnswer.exam_record_id == ExamRecord.id)
            .filter(StudentAnswer.student_id == student_id)
            .all()
        )
        grouped: dict[str, dict] = {}
        for answer, record in answers:
            if record_type is not None and record.type != record_type:
                continue
            key = record.id
            if key not in grouped:
                grouped[key] = {"record": record, "total": 0, "correct": 0}
            grouped[key]["total"] += 1
            if answer.is_correct:
                grouped[key]["correct"] += 1

        result: list[tuple[ExamRecord, float]] = []
        for g in grouped.values():
            if g["total"] > 0:
                result.append((g["record"], g["correct"] / g["total"]))
        result.sort(key=lambda item: as_aware(item[0].taken_at), reverse=True)
        return result

    # ── 创建与去重 ────────────────────────────────────────

    def _create_warning(self, db: Session, student: Student, trigger: dict) -> WarningLog | None:
        """去重后创建预警记录，识别家长绑定并置通知标记

        同 student + 同 type 且 status=pending 已存在则不重复创建。
        """
        existing = (
            db.query(WarningLog)
            .filter(
                WarningLog.student_id == student.id,
                WarningLog.warning_type == trigger["warning_type"],
                WarningLog.status == WarningStatus.PENDING,
            )
            .first()
        )
        if existing:
            return None

        bindings = (
            db.query(StudentParentBinding)
            .filter(
                StudentParentBinding.student_id == student.id,
                StudentParentBinding.status == "active",
            )
            .all()
        )

        log = WarningLog(
            student_id=student.id,
            warning_type=trigger["warning_type"],
            level=trigger["level"],
            title=trigger["title"],
            content=trigger["content"],
            data={**trigger["data"], "parent_binding_count": len(bindings)},
            notified_parent=len(bindings) > 0,
        )
        db.add(log)
        return log
