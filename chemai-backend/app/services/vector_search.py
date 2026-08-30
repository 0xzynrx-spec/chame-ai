"""ChemAI Backend — 题目向量检索服务

基于 ChromaDB 实现题目的语义向量化存储和相似度检索。
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ChromaDB 持久化目录（相对于项目根目录）
CHROMA_PERSIST_DIR = os.environ.get(
    "CHROMA_PERSIST_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "chromadb"),
)
COLLECTION_NAME = "questions"

# 全局客户端/collection 实例（惰性初始化）
_client = None
_collection = None


def _get_client():
    """获取 ChromaDB 客户端（惰性初始化，含惰性导入）"""
    global _client
    if _client is None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection() -> "chromadb.Collection":
    """获取题目向量 collection（惰性创建）

    若 collection 不存在则自动创建，使用余弦相似度距离函数。
    """
    global _collection
    if _collection is None:
        client = _get_client()
        try:
            _collection = client.get_collection(COLLECTION_NAME)
        except Exception:
            _collection = client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Created ChromaDB collection: {COLLECTION_NAME}")
    return _collection


def check_chromadb_health() -> bool:
    """检查 ChromaDB 是否可用

    Returns:
        True 如果 ChromaDB 可正常连接和操作
    """
    try:
        get_collection()
        return True
    except Exception as e:
        logger.warning(f"ChromaDB health check failed: {e}")
        return False


def build_question_text(question: object) -> str:
    """从 Question 对象提取用于向量化的文本

    拼接题干 + 答案 + 解析（中文优先）。
    """
    content = getattr(question, "content_i18n", {}) or {}
    answer = getattr(question, "answer_i18n", {}) or {}
    analysis = getattr(question, "analysis_i18n", {}) or {}

    parts = []
    for d in [content, answer, analysis]:
        if isinstance(d, dict):
            text = d.get("zh", "") or d.get("en", "") or ""
            if text:
                parts.append(text)

    return " ".join(parts)


def _upsert_vector(
    question_id: str,
    text: str,
    knowledge_points: Optional[list[str]] = None,
) -> bool:
    """内部方法：删除旧向量后插入新向量（upsert 语义）"""
    try:
        collection = get_collection()
        try:
            collection.delete(ids=[question_id])
        except Exception:
            pass

        metadata = {}
        if knowledge_points:
            metadata["knowledge_points"] = ",".join(knowledge_points)

        collection.add(
            ids=[question_id],
            documents=[text],
            metadatas=[metadata] if metadata else None,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to upsert vector for question {question_id}: {e}")
        return False


def add_question_vector(
    question_id: str,
    text: str,
    knowledge_points: Optional[list[str]] = None,
) -> bool:
    """将题目向量添加到 ChromaDB

    Args:
        question_id: 题目 ID
        text: 题目文本（题干 + 答案 + 解析）
        knowledge_points: 可选，知识点标签列表（存入 metadata 用于过滤）

    Returns:
        True 如果成功，False 如果失败（不抛异常）
    """
    return _upsert_vector(question_id, text, knowledge_points)


def update_question_vector(
    question_id: str,
    text: str,
    knowledge_points: Optional[list[str]] = None,
) -> bool:
    """更新题目向量（upsert 语义）

    Args:
        question_id: 题目 ID
        text: 题目文本（题干 + 答案 + 解析）
        knowledge_points: 可选，知识点标签列表
    """
    return _upsert_vector(question_id, text, knowledge_points)


def delete_question_vector(question_id: str) -> bool:
    """从 ChromaDB 删除题目向量"""
    try:
        collection = get_collection()
        collection.delete(ids=[question_id])
        return True
    except Exception as e:
        logger.error(f"Failed to delete vector for question {question_id}: {e}")
        return False


def search_similar(
    query_text: str,
    limit: int = 10,
    min_score: float = 0.0,
    filter_ids: Optional[list[str]] = None,
    knowledge_points: Optional[list[str]] = None,
) -> list[dict]:
    """语义相似度搜索

    Args:
        query_text: 搜索查询文本
        limit: 返回结果数量上限（最大 50）
        min_score: 最低相似度阈值（0-1）
        filter_ids: 可选，仅在这些 ID 中搜索（用于学校隔离）
        knowledge_points: 可选，按知识点标签过滤（后置过滤）

    Returns:
        列表，每项含 id、score、document、knowledge_points
    """
    limit = min(limit, 50)
    try:
        collection = get_collection()
        where_filter = None
        if filter_ids:
            # ChromaDB 不支持任意 ID 列表过滤，改由后置过滤
            pass

        # 多取一些用于后置过滤
        n_results = limit * 3 if (filter_ids or knowledge_points) else limit

        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "metadatas"],
        )

        items = []
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for i, doc_id in enumerate(ids):
            # 后置 ID 过滤
            if filter_ids and doc_id not in filter_ids:
                continue

            # ChromaDB 余弦距离转相似度：1 - distance
            score = 1.0 - distances[i] if i < len(distances) else 0.0
            if score < min_score:
                continue

            # 提取知识点标签（从 metadata 中）
            metadata = metadatas[i] if i < len(metadatas) else {}
            doc_kps = metadata.get("knowledge_points", [])
            if isinstance(doc_kps, str):
                doc_kps = [k.strip() for k in doc_kps.split(",") if k.strip()]

            # 知识点后置过滤
            if knowledge_points:
                if not any(kp in doc_kps for kp in knowledge_points):
                    continue

            items.append({
                "id": doc_id,
                "score": round(score, 4),
                "document": documents[i] if i < len(documents) else "",
                "knowledge_points": doc_kps,
            })

        # 按相似度降序并截取
        items.sort(key=lambda x: x["score"], reverse=True)
        return items[:limit]

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []


def search_similar_by_question(
    question_id: str,
    limit: int = 10,
    min_score: float = 0.0,
    filter_ids: Optional[list[str]] = None,
) -> list[dict]:
    """以题搜题：用已有题目的向量查找相似题目

    Args:
        question_id: 源题目 ID
        limit: 返回结果数量上限
        min_score: 最低相似度阈值
        filter_ids: 可选过滤 ID 列表

    Returns:
        列表，每项含 id、score、document（不含源题目自身）
    """
    try:
        collection = get_collection()
        results = collection.get(ids=[question_id], include=["documents"])
        docs = results.get("documents", [])
        if not docs or not docs[0]:
            return []

        source_text = docs[0]
        items = search_similar(
            query_text=source_text,
            limit=limit + 1,  # 多取一个排除自身
            min_score=min_score,
            filter_ids=filter_ids,
        )

        # 排除源题目自身
        return [item for item in items if item["id"] != question_id][:limit]

    except Exception as e:
        logger.error(f"Similar-by-question search failed for {question_id}: {e}")
        return []


def rebuild_index(questions: list) -> int:
    """重建全部题目向量索引

    清空现有 collection，遍历所有 Question 重新生成 embedding。

    Args:
        questions: Question ORM 对象列表

    Returns:
        成功处理的题目数量
    """
    try:
        client = _get_client()
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        global _collection
        _collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        count = 0
        batch_ids = []
        batch_docs = []
        batch_size = 100

        for q in questions:
            text = build_question_text(q)
            if not text:
                continue
            batch_ids.append(getattr(q, "id", ""))
            batch_docs.append(text)
            count += 1

            if len(batch_ids) >= batch_size:
                _collection.add(ids=batch_ids, documents=batch_docs)
                batch_ids = []
                batch_docs = []

        if batch_ids:
            _collection.add(ids=batch_ids, documents=batch_docs)

        logger.info(f"Rebuilt vector index: {count} questions")
        return count

    except Exception as e:
        logger.error(f"Index rebuild failed: {e}")
        return 0
