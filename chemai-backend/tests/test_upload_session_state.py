"""ChemAI Backend — UploadSession 状态机单元测试

校验状态转移守卫：对终态（DONE / DISCARDED）做状态变更应抛出异常，
非法非终态转换同样拒绝。
"""

import pytest

from app.models import (
    InvalidStateTransitionError,
    UploadSession,
    UploadSessionStatus,
)


def _make_session(status: UploadSessionStatus) -> UploadSession:
    """构造未落库的会话实例（仅校验状态机，不触发数据库）"""
    return UploadSession(
        status=status,
        school_id="school-1",
        teacher_id="teacher-1",
        file_path="/tmp/sheet.jpg",
        file_type="jpg",
    )


def test_terminal_state_done_rejects_transition():
    """终态 DONE 做状态变更应抛出异常"""
    session = _make_session(UploadSessionStatus.DONE)
    with pytest.raises(InvalidStateTransitionError):
        session.transition_to(UploadSessionStatus.GRADED)


def test_terminal_state_discarded_rejects_transition():
    """终态 DISCARDED 做状态变更应抛出异常"""
    session = _make_session(UploadSessionStatus.DISCARDED)
    with pytest.raises(InvalidStateTransitionError):
        session.transition_to(UploadSessionStatus.READY)


def test_valid_transition_updates_status():
    """合法转换更新状态"""
    session = _make_session(UploadSessionStatus.UPLOADED)
    session.transition_to(UploadSessionStatus.GRADING)
    assert session.status is UploadSessionStatus.GRADING


def test_invalid_non_terminal_transition_rejects():
    """非终态间的非法转换同样拒绝（GRADED → GRADING 不可回退）"""
    session = _make_session(UploadSessionStatus.GRADED)
    with pytest.raises(InvalidStateTransitionError):
        session.transition_to(UploadSessionStatus.GRADING)


def test_can_transition_to_reflects_transition_map():
    """can_transition_to 与转移表一致"""
    session = _make_session(UploadSessionStatus.GRADED)
    assert session.can_transition_to(UploadSessionStatus.DONE) is True
    assert session.can_transition_to(UploadSessionStatus.GRADING) is False
