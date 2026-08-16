"""add_warning_logs

Revision ID: b7c8d9e0f1a2
Revises: f1a2b3c4d5e6
Create Date: 2026-08-16 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('warning_logs',
        sa.Column('student_id', sa.String(length=36), nullable=False, comment='触发预警的学生 ID'),
        sa.Column('warning_type', sa.Enum('NO_LOGIN', 'SCORE_DROP', 'HIGH_ERROR_RATE', name='warningtype'), nullable=False, comment='预警类型：no_login / score_drop / high_error_rate'),
        sa.Column('level', sa.Enum('INFO', 'WARNING', 'CRITICAL', name='warninglevel'), nullable=False, comment='预警级别：info / warning / critical'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='预警概要标题'),
        sa.Column('content', sa.Text(), nullable=False, comment='预警详细描述'),
        sa.Column('data', sa.JSON(), nullable=False, comment='触发预警的量化指标（如缺勤天数、成绩降幅、错误率）'),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSED', 'IGNORED', name='warningstatus'), nullable=False, comment='处理状态：pending / processed / ignored'),
        sa.Column('processed_by', sa.String(length=36), nullable=True, comment='处理人（教师 ID）'),
        sa.Column('processed_at', sa.DateTime(), nullable=True, comment='处理时间'),
        sa.Column('note', sa.Text(), nullable=False, comment='处理备注'),
        sa.Column('notified_teacher', sa.Boolean(), nullable=False, comment='是否已通知教师'),
        sa.Column('notified_parent', sa.Boolean(), nullable=False, comment='是否已通知家长'),
        sa.Column('notified_student', sa.Boolean(), nullable=False, comment='是否已通知学生'),
        sa.Column('id', sa.String(length=36), nullable=False, comment='UUID 主键'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('warning_logs')
