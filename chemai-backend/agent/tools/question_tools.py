"""ChemAI Agent — 出题工具组（9个）

题库搜索、联网搜索、LLM出题+审核、批量出题、保存到题库、
题库列表、删除题库、生成试卷、智能推荐。

每个工具的 docstring 遵循四段式规范：
- **何时用**：触发条件
- **会发生什么**：执行结果
- **下一步**：后续建议操作
- **NOT for**：不适用场景
"""

from __future__ import annotations

from typing import Optional

from langchain.tools import tool
from sqlalchemy.orm import Session

from app.services.llm_service import LLMService
from app.services.question_generator import persist_generated_question
from app.services.vector_search import search_similar, delete_question_vector


# ── 内部辅助函数 ──────────────────────────────────────


def _format_search_results(results: list[dict], header: str) -> str:
    """格式化搜索结果列表（search_question_bank 和 smart_recommend 共用）"""
    lines = [f"{header}\n"]
    for i, item in enumerate(results, 1):
        score = item.get("score", 0)
        doc = item.get("document", "")[:100]
        kps = item.get("knowledge_points", [])
        kp_str = "、".join(kps) if kps else "未标注"
        lines.append(f"{i}. [相似度:{score:.2f}] {doc}...")
        lines.append(f"   知识点：{kp_str}")
    return "\n".join(lines)


def _persist_items(
    db: Session,
    teacher_id: str,
    items: list[dict],
) -> tuple[list[str], int]:
    """逐题审核入库，返回 (成功题目ID列表, 失败数量)"""
    success_ids: list[str] = []
    fail_count = 0
    for item in items:
        question = persist_generated_question(db, item, teacher_id)
        if question:
            success_ids.append(question.id)
        else:
            fail_count += 1
    return success_ids, fail_count


def _normalize_chem_formulas(text: str) -> str:
    """化学式标准化：裸化学式 → 下标格式（H2O → H₂O）"""
    import re
    _sub = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    # 匹配常见化学式模式：大写字母后跟数字
    pattern = re.compile(r'(?<![A-Za-z0-9])([A-Z][a-z]?)(\d+)(?![A-Za-z0-9])')
    def _replace(m: re.Match) -> str:
        return m.group(1) + m.group(2).translate(_sub)
    return pattern.sub(_replace, text)


# ── 题库搜索 ──────────────────────────────────────────


@tool
def search_question_bank(
    query: str,
    knowledge_points: Optional[list[str]] = None,
    limit: int = 10,
    min_score: float = 0.5,
    school_id: Optional[str] = None,
) -> str:
    """语义搜索题库中的相似题目。

    **何时用**：用户需要查找题库中已有的相似题目时调用。
    **会发生什么**：返回与查询文本语义最相似的题目列表，包含题型、难度、知识点标签。
    **下一步**：可以调用 generate_question 生成新题，或 save_to_bank 保存到题库。
    **NOT for**：生成新题目（用 generate_question）、联网搜索（用 search_web_questions）。

    Args:
        query: 搜索关键词或题目描述
        knowledge_points: 可选，按知识点标签过滤
        limit: 返回结果数量（最大 50）
        min_score: 最低相似度阈值（0-1）
        school_id: 可选，学校 ID（用于学校隔离）
    """
    if not query or not query.strip():
        return "❌ 请输入搜索关键词"

    limit = min(max(1, limit), 50)

    try:
        # 学校隔离：通过 filter_ids 传递
        filter_ids: Optional[list[str]] = None
        if school_id:
            # 从数据库查询该校的题目 ID 列表
            from app.database import get_db
            from app.models.question import Question, AuditStatus
            db = next(get_db())
            try:
                school_questions = (
                    db.query(Question.id)
                    .filter(Question.school_id == school_id)
                    .filter(Question.audit_status == AuditStatus.PASSED)
                    .all()
                )
                filter_ids = [q.id for q in school_questions]
                if not filter_ids:
                    return "🔍 该校题库中暂无题目"
            finally:
                db.close()

        results = search_similar(
            query_text=query.strip(),
            limit=limit,
            min_score=min_score,
            knowledge_points=knowledge_points,
            filter_ids=filter_ids,
        )

        if not results:
            return f"🔍 未找到与「{query}」相关的题目"

        return _format_search_results(results, f"🔍 找到 {len(results)} 道相关题目：")

    except Exception as e:
        return f"❌ 搜索失败：{str(e)}"


# ── 联网搜索 ──────────────────────────────────────────


@tool
def search_web_questions(query: str) -> str:
    """从外部教育资源网站搜索题目。

    **何时用**：用户需要查找题库之外的题目资源时调用。
    **会发生什么**：调用外部搜索 API 返回相关题目链接和摘要。
    **下一步**：可以调用 save_to_bank 将找到的题目保存到题库。
    **NOT for**：搜索本地题库（用 search_question_bank）。

    Args:
        query: 搜索关键词
    """
    # 联网搜索功能暂未实现，返回提示
    return "🌐 联网搜索功能暂不支持，正在开发中。请使用 search_question_bank 搜索本地题库。"


# ── LLM 出题 ──────────────────────────────────────────


@tool
def generate_question(
    knowledge_points: list[str],
    difficulty: str = "medium",
    question_type: str = "choice",
    db: Optional[Session] = None,
    teacher_id: Optional[str] = None,
) -> str:
    """使用 LLM 生成单道化学题目并自动审核入库。

    **何时用**：需要生成一道特定知识点、特定难度的题目时调用。
    **会发生什么**：调用 LLM 生成题目，化学式自动标准化，经过四维审核后入库，返回题目详情。
    **下一步**：可以调用 batch_generate 批量出题，或 generate_variant 生成变式题。
    **NOT for**：批量出题（用 batch_generate）、组卷（用 generate_exam）。

    Args:
        knowledge_points: 知识点标签列表（必填）
        difficulty: 难度等级（easy/medium/hard/competition）
        question_type: 题型（choice/fill/calc/experiment/inference）
        db: 可选，数据库会话（Agent 运行时注入）
        teacher_id: 可选，教师 ID（Agent 运行时注入）
    """
    if not knowledge_points:
        return "❌ 请指定至少一个知识点"

    try:
        llm_service = LLMService()
        question_types = f"{question_type}:1"
        items = llm_service.generate_questions(
            question_types=question_types,
            difficulty=difficulty,
            knowledge_points=knowledge_points,
        )

        if not items:
            return "❌ LLM 未能生成题目，请重试"

        item = items[0]

        # 化学式标准化
        item["content"] = _normalize_chem_formulas(item.get("content", ""))
        item["answer"] = _normalize_chem_formulas(item.get("answer", ""))
        if item.get("analysis"):
            item["analysis"] = _normalize_chem_formulas(item["analysis"])

        # 审核入库
        if db and teacher_id:
            success_ids, fail_count = _persist_items(db, teacher_id, [item])
            if not success_ids:
                return "❌ 题目审核未通过（可能包含不安全内容），已丢弃"
            db.commit()
            return (
                f"✅ 题目生成成功！\n"
                f"- 题目ID: {success_ids[0]}\n"
                f"- 题型: {item['type']}\n"
                f"- 难度: {item['difficulty']}\n"
                f"- 知识点: {', '.join(item['knowledge_points'])}\n"
                f"- 内容: {item['content'][:100]}..."
            )
        else:
            return (
                f"📝 题目预览：\n"
                f"- 题型: {item['type']}\n"
                f"- 难度: {item['difficulty']}\n"
                f"- 知识点: {', '.join(item['knowledge_points'])}\n"
                f"- 内容: {item['content'][:200]}\n"
                f"- 答案: {item['answer'][:100]}\n"
                f"💡 请确认保存到题库"
            )

    except Exception as e:
        return f"❌ 出题失败：{str(e)}"


# ── 批量出题 ──────────────────────────────────────────


@tool
def batch_generate(
    knowledge_points: list[str],
    count: int = 5,
    difficulty: str = "medium",
    question_type: str = "choice",
    db: Optional[Session] = None,
    teacher_id: Optional[str] = None,
) -> str:
    """批量生成多道化学题目。

    **何时用**：需要一次性生成多道同类型题目时调用。
    **会发生什么**：循环调用 LLM 生成题目，化学式自动标准化，逐题审核入库，返回生成结果统计。
    **下一步**：可以调用 smart_recommend 筛选最优题目。
    **NOT for**：单道出题（用 generate_question）、组卷（用 generate_exam）。

    Args:
        knowledge_points: 知识点标签列表（必填）
        count: 生成数量（最大 20）
        difficulty: 难度等级（easy/medium/hard/competition）
        question_type: 题型（choice/fill/calc/experiment/inference）
        db: 可选，数据库会话（Agent 运行时注入）
        teacher_id: 可选，教师 ID（Agent 运行时注入）
    """
    if not knowledge_points:
        return "❌ 请指定至少一个知识点"

    count = min(max(1, count), 20)

    try:
        llm_service = LLMService()
        question_types = f"{question_type}:{count}"
        items = llm_service.generate_questions(
            question_types=question_types,
            difficulty=difficulty,
            knowledge_points=knowledge_points,
        )

        if not items:
            return "❌ LLM 未能生成题目，请重试"

        # 化学式标准化
        for item in items:
            item["content"] = _normalize_chem_formulas(item.get("content", ""))
            item["answer"] = _normalize_chem_formulas(item.get("answer", ""))
            if item.get("analysis"):
                item["analysis"] = _normalize_chem_formulas(item["analysis"])

        # 审核入库
        success_ids: list[str] = []
        fail_count = 0
        if db and teacher_id:
            success_ids, fail_count = _persist_items(db, teacher_id, items)
            if success_ids:
                db.commit()

        lines = [f"📊 批量出题完成："]
        lines.append(f"- 成功: {len(success_ids) if db else len(items)} 道")
        if fail_count > 0:
            lines.append(f"- 失败（审核未通过）: {fail_count} 道")
        if success_ids:
            lines.append(f"- 题目ID: {', '.join(success_ids[:5])}{'...' if len(success_ids) > 5 else ''}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 批量出题失败：{str(e)}"


# ── 保存到题库 ──────────────────────────────────────────


@tool
def save_to_bank(
    content: str,
    question_type: str,
    difficulty: str,
    knowledge_points: list[str],
    answer: str,
    options: Optional[list[str]] = None,
    analysis: Optional[str] = None,
    db: Optional[Session] = None,
    teacher_id: Optional[str] = None,
) -> str:
    """将题目保存到题库（含四维审核和重复检测）。

    **何时用**：用户确认保存某道题目到题库时调用。
    **会发生什么**：执行重复检测和四维审核，通过后入库，返回保存成功提示。
    **下一步**：可以调用 list_questions 查看题库列表。
    **NOT for**：生成新题目（用 generate_question）。

    Args:
        content: 题目内容（必填）
        question_type: 题型（choice/fill/calc/experiment/inference）
        difficulty: 难度等级（easy/medium/hard/competition）
        knowledge_points: 知识点标签列表（必填）
        answer: 答案（必填）
        options: 可选，选择题选项
        analysis: 可选，解析
        db: 可选，数据库会话（Agent 运行时注入）
        teacher_id: 可选，教师 ID（Agent 运行时注入）
    """
    if not content or not content.strip():
        return "❌ 请提供题目内容"
    if not answer or not answer.strip():
        return "❌ 请提供题目答案"
    if not knowledge_points:
        return "❌ 请指定至少一个知识点"

    # 化学式标准化
    content = _normalize_chem_formulas(content.strip())
    answer = _normalize_chem_formulas(answer.strip())
    if analysis:
        analysis = _normalize_chem_formulas(analysis)

    # 重复检测：语义相似度检查
    try:
        similar = search_similar(
            query_text=content,
            limit=1,
            min_score=0.85,
        )
        if similar:
            return (
                f"⚠️ 检测到相似题目（相似度: {similar[0]['score']:.2f}）\n"
                f"- 相似题目: {similar[0]['document'][:80]}...\n"
                f"💡 该题目可能已存在，请确认是否继续保存"
            )
    except Exception:
        pass  # 重复检测失败不影响保存流程

    item = {
        "type": question_type,
        "difficulty": difficulty,
        "content": content,
        "options": options or [],
        "answer": answer,
        "analysis": analysis or "",
        "knowledge_points": knowledge_points,
    }

    if db and teacher_id:
        try:
            question = persist_generated_question(db, item, teacher_id)
            if question is None:
                return "❌ 题目审核未通过（可能包含不安全内容），已丢弃"

            db.commit()
            return (
                f"✅ 题目保存成功！\n"
                f"- 题目ID: {question.id}\n"
                f"- 题型: {question_type}\n"
                f"- 难度: {difficulty}\n"
                f"- 知识点: {', '.join(knowledge_points)}"
            )
        except Exception as e:
            return f"❌ 保存失败：{str(e)}"
    else:
        return "❌ 无法保存：缺少数据库会话或教师信息"


# ── 题库列表 ──────────────────────────────────────────


@tool
def list_questions(
    school_id: Optional[str] = None,
    question_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    knowledge_point: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: Optional[Session] = None,
) -> str:
    """查询题库中的题目列表。

    **何时用**：用户需要查看题库中的题目时调用。
    **会发生什么**：返回题目列表（分页），包含题型、难度、知识点标签。
    **下一步**：可以调用 delete_question 删除题目，或 search_question_bank 搜索相似题。
    **NOT for**：语义搜索（用 search_question_bank）。

    Args:
        school_id: 可选，学校 ID（用于学校隔离）
        question_type: 可选，按题型过滤
        difficulty: 可选，按难度过滤
        knowledge_point: 可选，按知识点过滤
        page: 页码（从 1 开始）
        page_size: 每页数量（最大 50）
        db: 可选，数据库会话（Agent 运行时注入）
    """
    if not db:
        return "❌ 无法查询：缺少数据库会话"

    try:
        from app.models.question import Question, QuestionType, Difficulty, AuditStatus

        query = db.query(Question)

        if school_id:
            query = query.filter(Question.school_id == school_id)
        if question_type:
            try:
                qtype = QuestionType(question_type.lower())
                query = query.filter(Question.type == qtype)
            except ValueError:
                return f"❌ 无效的题型：{question_type}"
        if difficulty:
            try:
                diff = Difficulty(difficulty.lower())
                query = query.filter(Question.difficulty == diff)
            except ValueError:
                return f"❌ 无效的难度：{difficulty}"
        if knowledge_point:
            query = query.filter(
                Question.knowledge_points.contains(knowledge_point)
            )

        query = query.filter(Question.audit_status == AuditStatus.PASSED)

        page_size = min(max(1, page_size), 50)
        offset = (max(1, page) - 1) * page_size
        total = query.count()
        questions = query.offset(offset).limit(page_size).all()

        if not questions:
            return "📭 题库中暂无符合条件的题目"

        lines = [f"📚 题库列表（共 {total} 道，第 {page} 页）：\n"]
        for i, q in enumerate(questions, 1):
            qtype = q.type.value if hasattr(q.type, "value") else str(q.type)
            diff = q.difficulty.value if hasattr(q.difficulty, "value") else str(q.difficulty)
            content = (q.content_i18n or {}).get("zh", "")[:50]
            kps = q.knowledge_points or []
            kp_str = "、".join(kps) if kps else "未标注"

            lines.append(f"{i}. [{qtype}][{diff}] {content}...")
            lines.append(f"   知识点：{kp_str} | ID: {q.id}")

        if total > offset + page_size:
            lines.append(f"\n💡 还有更多题目，可调用 list_questions(page={page + 1}) 查看下一页")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 查询失败：{str(e)}"


# ── 删除题库 ──────────────────────────────────────────


@tool
def delete_question(
    question_id: str,
    db: Optional[Session] = None,
) -> str:
    """删除题库中的题目（软删除）。

    **何时用**：用户确认删除某道题目时调用。
    **会发生什么**：执行软删除（标记为已删除），并清理向量索引。
    **下一步**：可以调用 list_questions 查看更新后的题库列表。
    **NOT for**：批量删除（需逐个调用）。

    Args:
        question_id: 题目 ID（必填）
        db: 可选，数据库会话（Agent 运行时注入）
    """
    if not question_id or not question_id.strip():
        return "❌ 请提供题目 ID"

    if not db:
        return "❌ 无法删除：缺少数据库会话"

    try:
        from app.models.question import Question
        from datetime import datetime

        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            return f"❌ 未找到题目：{question_id}"

        if getattr(question, "is_deleted", False):
            return f"⚠️ 题目 {question_id} 已被删除"

        question.is_deleted = True
        question.deleted_at = datetime.utcnow()
        db.commit()

        try:
            delete_question_vector(question_id)
        except Exception:
            pass

        return (
            f"✅ 题目删除成功！\n"
            f"- 题目ID: {question_id}\n"
            f"- 题型: {question.type.value if hasattr(question.type, 'value') else question.type}\n"
            f"- 内容: {(question.content_i18n or {}).get('zh', '')[:50]}..."
        )

    except Exception as e:
        return f"❌ 删除失败：{str(e)}"


# ── 生成试卷 ──────────────────────────────────────────


@tool
def generate_exam(
    topics: str,
    question_count: int = 10,
    difficulty_range: str = "2-4",
    db: Optional[Session] = None,
    teacher_id: Optional[str] = None,
) -> str:
    """生成完整化学试卷。

    **何时用**：需要生成一份包含多道题目的完整试卷时调用。
    **会发生什么**：按要求生成试卷，返回试卷结构和题目列表。
    **下一步**：可以调用 export_exam_docx 导出为 Word 文档。
    **NOT for**：单道出题（用 generate_question）。

    Args:
        topics: 知识点列表（逗号分隔）
        question_count: 题目数量（最大 30）
        difficulty_range: 难度范围（如"2-4"表示中等到较难）
        db: 可选，数据库会话（Agent 运行时注入）
        teacher_id: 可选，教师 ID（Agent 运行时注入）
    """
    if not topics or not topics.strip():
        return "❌ 请指定知识点"

    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    if not topic_list:
        return "❌ 请指定至少一个知识点"

    question_count = min(max(1, question_count), 30)

    # 解析难度范围
    try:
        parts = difficulty_range.split("-")
        min_diff = int(parts[0])
        max_diff = int(parts[1]) if len(parts) > 1 else min_diff
        min_diff = max(1, min(5, min_diff))
        max_diff = max(1, min(5, max_diff))
    except (ValueError, IndexError):
        min_diff, max_diff = 2, 4

    diff_map = {1: "easy", 2: "easy", 3: "medium", 4: "hard", 5: "competition"}
    difficulty = diff_map.get((min_diff + max_diff) // 2, "medium")

    # 题型分配：确保每种题型至少 1 道
    choice_count = max(1, question_count // 2)
    fill_count = max(1, question_count // 4)
    calc_count = max(1, question_count - choice_count - fill_count)

    try:
        llm_service = LLMService()
        items = llm_service.generate_questions(
            question_types=f"choice:{choice_count},fill:{fill_count},calc:{calc_count}",
            difficulty=difficulty,
            knowledge_points=topic_list,
        )

        if not items:
            return "❌ LLM 未能生成试卷题目，请重试"

        # 化学式标准化
        for item in items:
            item["content"] = _normalize_chem_formulas(item.get("content", ""))
            item["answer"] = _normalize_chem_formulas(item.get("answer", ""))
            if item.get("analysis"):
                item["analysis"] = _normalize_chem_formulas(item["analysis"])

        # 审核入库
        success_ids: list[str] = []
        if db and teacher_id:
            success_ids, _ = _persist_items(db, teacher_id, items)
            if success_ids:
                db.commit()

        lines = [f"📄 试卷生成完成！"]
        lines.append(f"- 知识点：{', '.join(topic_list)}")
        lines.append(f"- 难度范围：{difficulty_range}")
        lines.append(f"- 预期题数：{question_count}")
        lines.append(f"- 实际生成：{len(items)} 道")

        if db and teacher_id:
            lines.append(f"- 审核通过：{len(success_ids)} 道")
            if success_ids:
                lines.append(f"- 题目ID：{', '.join(success_ids[:5])}{'...' if len(success_ids) > 5 else ''}")

        type_counts: dict[str, int] = {}
        for item in items:
            t = item.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        lines.append("\n📊 题型分布：")
        for t, c in type_counts.items():
            lines.append(f"- {t}: {c} 道")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 试卷生成失败：{str(e)}"


# ── 智能推荐 ──────────────────────────────────────────


@tool
def smart_recommend(
    topic: str,
    knowledge_points: Optional[list[str]] = None,
    count: int = 3,
    min_score: float = 0.6,
) -> str:
    """智能推荐题目——基于知识点和语义相似度推荐。

    **何时用**：需要为特定知识点推荐相关题目时调用。
    **会发生什么**：结合向量检索和知识点过滤，推荐最相关的题目。
    **下一步**：可以调用 generate_question 生成类似题目。
    **NOT for**：精确搜索（用 search_question_bank）。

    Args:
        topic: 推荐主题或关键词
        knowledge_points: 可选，按知识点标签过滤
        count: 推荐数量（最大 10）
        min_score: 最低相似度阈值（0-1）
    """
    if not topic or not topic.strip():
        return "❌ 请提供推荐主题"

    count = min(max(1, count), 10)

    try:
        results = search_similar(
            query_text=topic.strip(),
            limit=count,
            min_score=min_score,
            knowledge_points=knowledge_points,
        )

        if not results:
            return f"🔍 未找到与「{topic}」相关的推荐题目"

        return _format_search_results(results, f"💡 为您推荐 {len(results)} 道题目：")

    except Exception as e:
        return f"❌ 推荐失败：{str(e)}"


# ── 变式题生成 ──────────────────────────────────────────


@tool
def generate_variant(
    question_id: str,
    variant_count: int = 3,
    db: Optional[Session] = None,
    teacher_id: Optional[str] = None,
) -> str:
    """生成题目变式——保持知识点和难度不变，改变具体情境。

    **何时用**：需要为一道题目生成多个变式时调用。
    **会发生什么**：返回多道变式题，核心考点相同但表述不同。
    **下一步**：可以调用 batch_grade 批量批改。
    **NOT for**：从零出题（用 generate_question）。

    Args:
        question_id: 原题目 ID（必填）
        variant_count: 变式数量（最大 10）
        db: 可选，数据库会话（Agent 运行时注入）
        teacher_id: 可选，教师 ID（Agent 运行时注入）
    """
    if not question_id or not question_id.strip():
        return "❌ 请提供原题目 ID"

    variant_count = min(max(1, variant_count), 10)

    try:
        qtype = "choice"
        diff = "medium"
        kps: list[str] = []

        if db:
            from app.models.question import Question
            original = db.query(Question).filter(Question.id == question_id).first()
            if not original:
                return f"❌ 未找到原题目：{question_id}"
            qtype = original.type.value if hasattr(original.type, "value") else "choice"
            diff = original.difficulty.value if hasattr(original.difficulty, "value") else "medium"
            kps = original.knowledge_points or []

        llm_service = LLMService()
        items = llm_service.generate_variant_questions(
            variant_qid=question_id,
            question_type=qtype,
            difficulty=diff,
            knowledge_points=kps if kps else None,
            count=variant_count,
        )

        if not items:
            return "❌ LLM 未能生成变式题，请重试"

        # 化学式标准化
        for item in items:
            item["content"] = _normalize_chem_formulas(item.get("content", ""))
            item["answer"] = _normalize_chem_formulas(item.get("answer", ""))
            if item.get("analysis"):
                item["analysis"] = _normalize_chem_formulas(item["analysis"])

        # 审核入库
        success_ids: list[str] = []
        if db and teacher_id:
            success_ids, _ = _persist_items(db, teacher_id, items)
            if success_ids:
                db.commit()

        lines = [f"🔄 变式题生成完成！"]
        lines.append(f"- 原题目ID：{question_id}")
        lines.append(f"- 预期数量：{variant_count}")
        lines.append(f"- 实际生成：{len(items)} 道")

        if db and teacher_id:
            lines.append(f"- 审核通过：{len(success_ids)} 道")
            if success_ids:
                lines.append(f"- 题目ID：{', '.join(success_ids)}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 变式题生成失败：{str(e)}"


# ── 导出试卷 ──────────────────────────────────────────


@tool
def export_exam_docx(exam_id: str, filename: str = "试卷") -> str:
    """导出试卷为 Word 文档。

    **何时用**：需要将生成的试卷导出为可打印的 Word 格式时调用。
    **会发生什么**：返回 Word 文档下载链接。
    **下一步**：可以分享给学生或打印。
    **NOT for**：生成试卷（用 generate_exam）。

    Args:
        exam_id: 试卷 ID（必填）
        filename: 文件名（默认"试卷"）
    """
    return f"📄 DOCX 导出功能暂未实现。试卷 {exam_id} 已生成，可使用 HTML 导出功能预览。"
