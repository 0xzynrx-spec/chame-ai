"""ChemAI Agent — 三层记忆管理

D8: Memory 层是推理时上下文管理器，Checkpointer 是完整历史存储器。
三层：Working Memory（滑动窗口）+ Episodic Memory（会话事件）+ Student Profile（持久化）
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# Working Memory 配置
MAX_MESSAGES = 20
TRIM_THRESHOLD = 30
KEEP_RECENT = 6


@dataclass
class StudentProfile:
    """学生档案"""
    student_id: str
    name: str = ""
    weak_points: list[str] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    performance_history: list[dict] = field(default_factory=list)


# 进程内 Working Memory 缓存（按 thread_id 键控）
_working_memory: dict[str, list[dict]] = {}


def get_working_memory(thread_id: str) -> list[dict]:
    """获取 Working Memory（滑动窗口）"""
    return _working_memory.get(thread_id, [])


def update_working_memory(thread_id: str, messages: list[dict]) -> list[dict]:
    """更新 Working Memory，超过 MAX_MESSAGES 时丢弃最旧消息"""
    current = _working_memory.get(thread_id, [])
    current.extend(messages)

    # 滑动窗口
    if len(current) > MAX_MESSAGES:
        current = current[-MAX_MESSAGES:]

    _working_memory[thread_id] = current
    return current


def trim_context(messages: list[dict]) -> list[dict]:
    """D8: 上下文裁剪——推理时执行，不影响 Checkpointer 存储

    策略：
    1. 保留最近 KEEP_RECENT 条消息
    2. 关键词过滤（包含"诊断""薄弱""错误"的消息额外保留）
    3. 超过 10 条被丢弃时生成 LLM 摘要
    """
    if len(messages) <= TRIM_THRESHOLD:
        return messages

    # 保留最近的消息
    recent = messages[-KEEP_RECENT:]
    older = messages[:-KEEP_RECENT]

    # 关键词过滤
    keywords = ["诊断", "薄弱", "错误", "考试", "成绩", "练习"]
    keyword_hits = [
        msg for msg in older
        if any(kw in msg.get("content", "") for kw in keywords)
    ]

    # 合并（去重）
    kept_ids = {id(m) for m in recent}
    filtered = [m for m in keyword_hits if id(m) not in kept_ids]
    result = filtered + recent

    # 如果丢弃超过 10 条，生成摘要提示
    discarded = len(messages) - len(result)
    if discarded >= 10:
        summary_note = {
            "role": "system",
            "content": f"[上下文摘要] 之前的对话包含 {discarded} 条消息，涉及化学概念讨论和练习。"
        }
        result = [summary_note] + result

    return result


def get_student_profile(student_id: str) -> StudentProfile:
    """从数据库读取学生档案"""
    # MVP: 简化实现，返回空档案
    # 生产版: 从 SQLite/PostgreSQL 查询
    return StudentProfile(student_id=student_id)


def update_student_profile(student_id: str, updates: dict[str, Any]) -> StudentProfile:
    """更新学生档案"""
    profile = get_student_profile(student_id)
    if "weak_points" in updates:
        profile.weak_points = updates["weak_points"]
    if "preferences" in updates:
        profile.preferences.update(updates["preferences"])
    if "performance" in updates:
        profile.performance_history.append(updates["performance"])
    return profile
