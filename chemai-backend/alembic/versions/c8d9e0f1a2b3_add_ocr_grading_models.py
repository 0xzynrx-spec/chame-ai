"""add_ocr_grading_models

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-08-16 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. upload_sessions
    op.create_table('upload_sessions',
        sa.Column('school_id', sa.String(length=36), nullable=False, comment='所属学校 ID'),
        sa.Column('teacher_id', sa.String(length=36), nullable=False, comment='上传教师 ID'),
        sa.Column('file_path', sa.String(length=500), nullable=False, comment='落盘文件路径'),
        sa.Column('file_type', sa.String(length=20), nullable=False, comment='文件类型：jpg/png/bmp/webp/pdf'),
        sa.Column('exam_id', sa.String(length=36), nullable=True, comment='关联试卷定义 ID（题库匹配答案来源）'),
        sa.Column('class_id', sa.String(length=36), nullable=True, comment='推导出的班级 ID'),
        sa.Column('student_id', sa.String(length=36), nullable=True, comment='抽取出的学生 ID'),
        sa.Column('answer_key', sa.JSON(), nullable=True, comment='教师录入参考答案'),
        sa.Column('status', sa.Enum('UPLOADED', 'READY', 'GRADING', 'GRADED', 'DONE', 'DISCARDED', 'ERROR', name='uploadsessionstatus'), nullable=False, server_default='UPLOADED', comment='会话状态'),
        sa.Column('ocr_task_id', sa.String(length=36), nullable=True, comment='关联 OCR 任务 ID'),
        sa.Column('id', sa.String(length=36), nullable=False, comment='UUID 主键'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. ocr_tasks
    op.create_table('ocr_tasks',
        sa.Column('session_id', sa.String(length=36), nullable=False, comment='所属上传会话 ID'),
        sa.Column('school_id', sa.String(length=36), nullable=False, comment='所属学校 ID'),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='baidu', comment='OCR 提供方：baidu'),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'DONE', 'FAILED', name='ocrtaskstatus'), nullable=False, server_default='PENDING', comment='任务状态'),
        sa.Column('result_text', sa.Text(), nullable=True, comment='OCR 识别文本结果'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='失败错误信息'),
        sa.Column('id', sa.String(length=36), nullable=False, comment='UUID 主键'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.ForeignKeyConstraint(['session_id'], ['upload_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. grading_results
    op.create_table('grading_results',
        sa.Column('session_id', sa.String(length=36), nullable=False, comment='所属上传会话 ID'),
        sa.Column('school_id', sa.String(length=36), nullable=False, comment='所属学校 ID'),
        sa.Column('student_id', sa.String(length=36), nullable=True, comment='作答学生 ID'),
        sa.Column('question_id', sa.String(length=36), nullable=True, comment='关联题目 ID（题库匹配时有）'),
        sa.Column('question_no', sa.Integer(), nullable=True, comment='题号（教师录入答案时按题号对齐）'),
        sa.Column('student_answer_text', sa.Text(), nullable=False, server_default='', comment='OCR 抽取的学生作答原文'),
        sa.Column('normalized_answer', sa.Text(), nullable=False, server_default='', comment='规范化后的作答'),
        sa.Column('correct_answer_text', sa.Text(), nullable=False, server_default='', comment='参考答案'),
        sa.Column('judgment', sa.Enum('CORRECT', 'INCORRECT', 'REVIEW_REQUIRED', name='judgment'), nullable=False, server_default='REVIEW_REQUIRED', comment='判分结论'),
        sa.Column('ocr_confidence', sa.Float(), nullable=True, comment='OCR 置信度（0.0-1.0）'),
        sa.Column('confirmed', sa.Boolean(), nullable=False, server_default=sa.false(), comment='教师是否已确认'),
        sa.Column('id', sa.String(length=36), nullable=False, comment='UUID 主键'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.ForeignKeyConstraint(['session_id'], ['upload_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('grading_results')
    op.drop_table('ocr_tasks')
    op.drop_table('upload_sessions')
