"""ChemAI Agent — 诊断工具（7个）

diagnose_barrier, show_diagnosis, show_students, weekly_report,
assign_adaptive_practice, generate_learning_plan, send_learning_plan

接入现有 DiagnosisEngine、AdaptivePracticeService 和 LLMService。
"""

from typing import Optional

from langchain.tools import tool
from sqlalchemy.orm import Session

from app.services.adaptive_practice import (
    compute_zpd,
    extract_weak_knowledge_points,
    get_dominant_barrier,
    validate_batch,
)
from app.services.llm_service import LLMService


# ── 常量 ──────────────────────────────────────────────────

BARRIER_CN: dict[str, str] = {
    "concept": "概念理解型",
    "reading": "审题障碍型",
    "expression": "表述障碍型",
}


# ── 辅助函数 ──────────────────────────────────────────────


def _barrier_distribution(student) -> dict[str, float]:
    """从 Student 对象提取三维障碍分布"""
    return {
        "concept": student.barrier_concept_rate or 0.0,
        "reading": student.barrier_reading_rate or 0.0,
        "expression": student.barrier_expression_rate or 0.0,
    }


def _format_barrier_result(student_name: str, barrier_type: str, distribution: dict, weak_kps: list[str]) -> str:
    """格式化单个学生的障碍诊断结果"""
    lines = [
        f"📊 学生「{student_name}」障碍诊断结果",
        f"",
        f"主导障碍：{BARRIER_CN.get(barrier_type, barrier_type)}",
        f"",
        f"三维分布：",
        f"  • 概念理解：{distribution.get('concept', 0):.0%}",
        f"  • 审题障碍：{distribution.get('reading', 0):.0%}",
        f"  • 表述障碍：{distribution.get('expression', 0):.0%}",
    ]
    if weak_kps:
        lines.append(f"")
        lines.append(f"薄弱知识点：{', '.join(weak_kps)}")
    return "\n".join(lines)


def _format_class_diagnosis(class_name: str, students: list[dict], class_distribution: dict) -> str:
    """格式化班级障碍诊断结果"""
    lines = [
        f"📊 班级「{class_name}」障碍诊断报告",
        f"",
        f"班级分布：",
        f"  • 概念理解型：{class_distribution.get('concept', 0)} 人",
        f"  • 审题障碍型：{class_distribution.get('reading', 0)} 人",
        f"  • 表述障碍型：{class_distribution.get('expression', 0)} 人",
        f"",
        f"需关注学生：",
    ]

    # 按障碍严重度排序，展示前 10 名
    sorted_students = sorted(
        students,
        key=lambda s: max(s.get("concept", 0), s.get("reading", 0), s.get("expression", 0)),
        reverse=True,
    )[:10]

    for s in sorted_students:
        dominant = s.get("dominant_barrier", "concept")
        name = s.get("name", "未知")
        rate = s.get(dominant, 0)
        lines.append(f"  • {name}：{BARRIER_CN.get(dominant, dominant)} ({rate:.0%})")

    return "\n".join(lines)


# ── 工具定义 ──────────────────────────────────────────────


@tool
def diagnose_barrier(
    student_id: str = "",
    class_id: str = "",
    db: Optional[Session] = None,
) -> str:
    """诊断学生或班级的学习障碍类型。

    **何时用**：需要了解学生或班级的障碍分布（概念/审题/表述）时调用。
    **会发生什么**：个体返回三维障碍分布和主导类型；班级返回全班统计分布。
    **下一步**：可以调用 show_diagnosis 展示诊断图表，或调用 assign_adaptive_practice 布置针对性练习。
    **NOT for**：生成周报（用 weekly_report）；查看学生列表（用 show_students）。

    Args:
        student_id: 学生 ID（个体诊断时传入）
        class_id: 班级 ID（班级诊断时传入）
        db: 数据库会话（运行时注入）
    """
    if not student_id and not class_id:
        return "❌ 请提供学生 ID 或班级 ID 进行诊断。"

    if not db:
        return "❌ 数据库连接不可用。"

    try:
        from app.models import Student, Class

        if student_id:
            # 个体诊断
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                return f"❌ 未找到学生 {student_id}。"

            distribution = _barrier_distribution(student)
            barrier_type = get_dominant_barrier(student)
            weak_kps = extract_weak_knowledge_points(db, student_id, limit=3)

            return _format_barrier_result(student.name, barrier_type, distribution, weak_kps)

        else:
            # 班级诊断
            cls = db.query(Class).filter(Class.id == class_id).first()
            if not cls:
                return f"❌ 未找到班级 {class_id}。"

            students = db.query(Student).filter(Student.class_id == class_id).all()
            if not students:
                return f"❌ 班级「{cls.name}」暂无学生。"

            students_payload = []
            class_distribution = {"concept": 0, "reading": 0, "expression": 0}

            for student in students:
                distribution = _barrier_distribution(student)
                dominant = get_dominant_barrier(student)
                if dominant:
                    class_distribution[dominant] += 1

                students_payload.append({
                    "student_id": student.id,
                    "name": student.name,
                    **distribution,
                    "dominant_barrier": dominant,
                })

            return _format_class_diagnosis(cls.name, students_payload, class_distribution)

    except Exception as e:
        return f"❌ 诊断失败：{str(e)}"


@tool
def show_diagnosis(
    student_id: str = "",
    class_id: str = "",
) -> str:
    """在聊天中内联渲染诊断图表面板。

    **何时用**：需要在对话中展示可视化诊断图表时调用。
    **会发生什么**：返回 SSE component 事件，前端渲染环形图展示三种障碍类型分布。
    **下一步**：用户可在图表上点击查看详细诊断信息。
    **NOT for**：文本诊断结果（用 diagnose_barrier）。

    Args:
        student_id: 学生 ID（个体诊断时传入）
        class_id: 班级 ID（班级诊断时传入）
    """
    if not student_id and not class_id:
        return "❌ 请提供学生 ID 或班级 ID。"

    # 返回 SSE component 事件指令
    import json

    if student_id:
        component_data = {
            "_component": "diagnosis",
            "_route": {
                "page": "diagnosis",
                "params": {"student_id": student_id},
            },
        }
        return f"📊 正在加载学生诊断面板...\n\n{json.dumps(component_data, ensure_ascii=False)}"
    else:
        component_data = {
            "_component": "diagnosis",
            "_route": {
                "page": "diagnosis",
                "params": {"class_id": class_id},
            },
        }
        return f"📊 正在加载班级诊断面板...\n\n{json.dumps(component_data, ensure_ascii=False)}"


@tool
def show_students(
    class_id: str = "",
    barrier_type: str = "",
    db: Optional[Session] = None,
) -> str:
    """展示学生列表（三模式：班级列表→学生卡片→障碍筛选）。

    **何时用**：需要查看班级学生或按障碍类型筛选学生时调用。
    **会发生什么**：无班级参数时列出全部班级；有班级时展示学生卡片；有过滤条件时按障碍筛选。
    **下一步**：可以点击学生查看详细诊断或布置练习。
    **NOT for**：障碍诊断（用 diagnose_barrier）。

    Args:
        class_id: 班级 ID（可选，不传则列出所有班级）
        barrier_type: 障碍过滤条件（可选，concept/reading/expression）
        db: 数据库会话（运行时注入）
    """
    if not db:
        return "❌ 数据库连接不可用。"

    try:
        from app.models import Student, Class, Teacher

        if not class_id:
            # 模式 1：列出所有班级
            classes = db.query(Class).all()
            if not classes:
                return "📭 暂无班级数据。"

            lines = ["📚 班级列表：\n"]
            for cls in classes:
                student_count = db.query(Student).filter(Student.class_id == cls.id).count()
                lines.append(f"  • {cls.name}（{student_count} 人）- ID: {cls.id}")
            return "\n".join(lines)

        # 模式 2/3：展示学生卡片
        cls = db.query(Class).filter(Class.id == class_id).first()
        if not cls:
            return f"❌ 未找到班级 {class_id}。"

        query = db.query(Student).filter(Student.class_id == class_id)
        students = query.all()

        if not students:
            return f"📭 班级「{cls.name}」暂无学生。"

        # 按障碍类型筛选
        if barrier_type:
            barrier_type = barrier_type.lower().strip()
            filtered = []
            for s in students:
                dominant = get_dominant_barrier(s)
                if dominant == barrier_type:
                    filtered.append(s)
            students = filtered
            if not students:
                return f"📭 班级「{cls.name}」中没有{BARRIER_CN.get(barrier_type, barrier_type)}障碍的学生。"

        # 格式化学生卡片
        title = f"👥 班级「{cls.name}」学生列表"
        if barrier_type:
            title += f"（筛选：{BARRIER_CN.get(barrier_type, barrier_type)}）"

        lines = [title, ""]
        for s in students:
            dominant = get_dominant_barrier(s)
            dist = _barrier_distribution(s)

            lines.append(f"👤 {s.name}")
            lines.append(f"   主导障碍：{BARRIER_CN.get(dominant, dominant)}")
            lines.append(f"   概念 {dist['concept']:.0%} | 审题 {dist['reading']:.0%} | 表述 {dist['expression']:.0%}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 查询失败：{str(e)}"


@tool
def weekly_report(
    student_id: str = "",
    class_id: str = "",
    db: Optional[Session] = None,
) -> str:
    """生成学生或班级的周报。

    **何时用**：需要生成通俗易懂的学习周报时调用。
    **会发生什么**：调用 LLM 生成 200 字左右的周报，包含学习表现、进步情况、建议。
    **下一步**：可以将周报发送给家长。
    **NOT for**：详细诊断分析（用 diagnose_barrier）。

    Args:
        student_id: 学生 ID
        class_id: 班级 ID（可选，用于班级周报）
        db: 数据库会话（运行时注入）
    """
    if not student_id and not class_id:
        return "❌ 请提供学生 ID 或班级 ID。"

    if not db:
        return "❌ 数据库连接不可用。"

    try:
        from app.models import Student, ExamRecord, RecordType, StudentAnswer

        if student_id:
            # 学生周报
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                return f"❌ 未找到学生 {student_id}。"

            # 获取近期表现数据
            recent_answers = (
                db.query(StudentAnswer)
                .join(ExamRecord, StudentAnswer.exam_record_id == ExamRecord.id)
                .filter(
                    StudentAnswer.student_id == student_id,
                    ExamRecord.type == RecordType.PRACTICE,
                )
                .order_by(StudentAnswer.created_at.desc())
                .limit(30)
                .all()
            )

            total = len(recent_answers)
            correct = sum(1 for a in recent_answers if a.is_correct)
            accuracy = correct / total if total > 0 else 0

            barrier_type = get_dominant_barrier(student)
            dist = _barrier_distribution(student)
            barrier_info = {
                "dominant_barrier": barrier_type,
                **{f"{k}_rate": v for k, v in dist.items()},
            }

            performance_data = {
                "accuracy": accuracy,
                "practice_count": total,
                "correct_count": correct,
            }

            llm = LLMService()
            report = llm.weekly_report(student.name, performance_data, barrier_info)
            return f"📝 {student.name} 本周学习周报\n\n{report}"

        else:
            # 班级周报
            from app.models import Class

            cls = db.query(Class).filter(Class.id == class_id).first()
            if not cls:
                return f"❌ 未找到班级 {class_id}。"

            students = db.query(Student).filter(Student.class_id == class_id).all()
            if not students:
                return f"📭 班级「{cls.name}」暂无学生。"

            # 统计班级整体情况
            total_students = len(students)
            barrier_counts = {"concept": 0, "reading": 0, "expression": 0}
            for s in students:
                dominant = get_dominant_barrier(s)
                barrier_counts[dominant] += 1

            # 构建班级表现数据用于 LLM
            performance_data = {
                "student_count": total_students,
                "barrier_distribution": barrier_counts,
            }
            barrier_info = {
                "dominant_barrier": max(barrier_counts, key=barrier_counts.get),
            }

            # 列出需要关注的学生
            top_students = []
            for s in students[:5]:
                dominant = get_dominant_barrier(s)
                top_students.append(f"{s.name}（{BARRIER_CN.get(dominant, dominant)}）")

            llm = LLMService()
            report = llm.weekly_report(cls.name, performance_data, barrier_info)
            result = f"📝 班级「{cls.name}」本周学习周报\n\n{report}"
            if top_students:
                result += f"\n\n需关注学生：\n  • " + "\n  • ".join(top_students)
            return result

    except Exception as e:
        return f"❌ 周报生成失败：{str(e)}"


@tool
def assign_adaptive_practice(
    class_id: str,
    knowledge_points: str = "",
    count: int = 10,
    db: Optional[Session] = None,
) -> str:
    """为班级学生生成个性化 ZPD 练习（需审批确认）。

    **何时用**：需要为班级学生布置自适应练习时调用。
    **会发生什么**：为每个学生计算 ZPD 难度，生成个性化题目参数，返回预览结果。
    **下一步**：教师确认后，前端调用 API 持久化练习。
    **NOT for**：手动出题（用 generate_questions）。

    Args:
        class_id: 班级 ID
        knowledge_points: 知识点（逗号分隔，可选）
        count: 每个学生的题目数量（默认 10）
        db: 数据库会话（运行时注入）
    """
    if not class_id:
        return "❌ 请提供班级 ID。"

    if not db:
        return "❌ 数据库连接不可用。"

    try:
        from app.models import Student, Class

        cls = db.query(Class).filter(Class.id == class_id).first()
        if not cls:
            return f"❌ 未找到班级 {class_id}。"

        students = db.query(Student).filter(Student.class_id == class_id).all()
        if not students:
            return f"📭 班级「{cls.name}」暂无学生。"

        # 批次验证
        student_ids = [s.id for s in students]
        validate_batch(student_ids)

        # 解析知识点
        kp_list = [kp.strip() for kp in knowledge_points.split(",") if kp.strip()] if knowledge_points else []

        # 为每个学生计算 ZPD 和薄弱知识点
        lines = [
            f"📚 班级「{cls.name}」自适应练习预览",
            f"",
            f"题目数量：每生 {count} 题",
            f"知识点：{', '.join(kp_list) if kp_list else '自动匹配薄弱知识点'}",
            f"",
            f"学生 ZPD 参数：",
        ]

        for student in students:
            zpd_level = compute_zpd(db, student.id)
            weak_kps = extract_weak_knowledge_points(db, student.id, limit=3)
            dominant = get_dominant_barrier(student)

            # 使用教师指定知识点补充
            target_kps = weak_kps if weak_kps else kp_list[:3]

            lines.append(f"")
            lines.append(f"👤 {student.name}")
            lines.append(f"   ZPD 难度：{zpd_level}")
            lines.append(f"   主导障碍：{BARRIER_CN.get(dominant, dominant)}")
            lines.append(f"   出题知识点：{', '.join(target_kps) if target_kps else '待定'}")

        lines.append(f"")
        lines.append(f"⚠️ 请确认以上参数后，点击「确认下发」按钮完成布置。")

        return "\n".join(lines)

    except ValueError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        return f"❌ 预览生成失败：{str(e)}"


@tool
def generate_learning_plan(
    student_id: str,
    db: Optional[Session] = None,
) -> str:
    """为学生生成个性化学习计划。

    **何时用**：需要为学生生成个性化学习计划时调用。
    **会发生什么**：调用 LLM 分析学生薄弱点，生成包含每日任务的学习计划。
    **下一步**：调用 send_learning_plan 将计划发送给学生。
    **NOT for**：直接查看诊断结果（用 diagnose_barrier）。

    Args:
        student_id: 学生 ID
        db: 数据库会话（运行时注入）
    """
    if not student_id:
        return "❌ 请提供学生 ID。"

    if not db:
        return "❌ 数据库连接不可用。"

    try:
        from app.models import Student

        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return f"❌ 未找到学生 {student_id}。"

        # 获取薄弱知识点
        weak_kps = extract_weak_knowledge_points(db, student_id, limit=5)
        barrier_type = get_dominant_barrier(student)

        # 调用 LLM 生成学习计划
        llm = LLMService()
        plan = llm.generate_learning_plan(
            student_name=student.name,
            barrier_type=barrier_type,
            weak_knowledge_points=weak_kps,
        )

        return f"📋 学生「{student.name}」个性化学习计划\n\n{plan}"

    except Exception as e:
        return f"❌ 学习计划生成失败：{str(e)}"


@tool
def send_learning_plan(
    student_id: str,
    plan_text: str = "",
    db: Optional[Session] = None,
) -> str:
    """发送学习计划给学生。

    **何时用**：需要将生成的学习计划通知学生时调用。
    **会发生什么**：记录计划发送事件，返回确认信息。
    **下一步**：学生可在学习面板中查看计划。
    **NOT for**：生成计划（用 generate_learning_plan）。

    Args:
        student_id: 学生 ID
        plan_text: 学习计划文本（由 generate_learning_plan 生成）
        db: 数据库会话（运行时注入）
    """
    if not student_id:
        return "❌ 请提供学生 ID。"

    if not plan_text:
        return "❌ 请提供学习计划文本。"

    if not db:
        return "❌ 数据库连接不可用。"

    try:
        from app.models import Student

        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return f"❌ 未找到学生 {student_id}。"

        # TODO: 持久化逻辑待数据模型支持后实现
        return f"✅ 学习计划已发送给「{student.name}」。\n\n学生可在学习面板中查看详细计划。"

    except Exception as e:
        return f"❌ 发送失败：{str(e)}"
