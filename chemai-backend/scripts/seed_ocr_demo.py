"""QA 辅助 — 播种 OCR 判卷演示数据（开发库）

为浏览器走通「上传 → 识别(mock) → 判分 → 复核 → 确认入库」准备最小数据：
1. 一道选择题（答案 B）+ 一道填空题（答案 H2O）
2. 一个题库文件夹 + 关联题目
3. 一场考试关联该题库（供「题库匹配」答案来源使用）

幂等：已存在同名考试则跳过。仅针对开发 SQLite 库。
运行：cd chemai-backend && python scripts/seed_ocr_demo.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import (
    Exam,
    ExamQuestionSet,
    Question,
    QuestionSet,
    QuestionSetItem,
    QuestionType,
    Teacher,
)

EXAM_NAME = "OCR 演示考试"


def run() -> int:
    db = SessionLocal()
    try:
        teacher = db.query(Teacher).first()
        if teacher is None:
            print("缺少 teacher，无法播种")
            return 1

        existing = (
            db.query(Exam)
            .filter(Exam.name == EXAM_NAME, Exam.school_id == teacher.school_id)
            .first()
        )
        if existing:
            print(f"已存在考试「{EXAM_NAME}」(id={existing.id})，跳过")
            return 0

        q1 = Question(
            type=QuestionType.CHOICE,
            content_i18n={"zh": "下列物质中属于电解质的是（　）"},
            options_i18n={"zh": ["A. 盐酸", "B. 蔗糖", "C. 铜", "D. 酒精"]},
            answer_i18n={"zh": "B"},
            knowledge_points=["电解质"],
            created_by=teacher.id,
        )
        q2 = Question(
            type=QuestionType.FILL,
            content_i18n={"zh": "水的化学式"},
            answer_i18n={"zh": "H2O"},
            knowledge_points=["化学用语"],
            created_by=teacher.id,
        )
        db.add_all([q1, q2])
        db.flush()

        qs = QuestionSet(
            name="OCR 演示题库", created_by=teacher.id, school_id=teacher.school_id
        )
        db.add(qs)
        db.flush()
        db.add_all(
            [
                QuestionSetItem(question_set_id=qs.id, question_id=q1.id, sort_order=1),
                QuestionSetItem(question_set_id=qs.id, question_id=q2.id, sort_order=2),
            ]
        )
        db.flush()

        exam = Exam(name=EXAM_NAME, created_by=teacher.id, school_id=teacher.school_id)
        db.add(exam)
        db.flush()
        db.add(ExamQuestionSet(exam_id=exam.id, question_set_id=qs.id))

        db.commit()
        print(f"播种完成：exam={exam.id}, q1={q1.id}(choice/B), q2={q2.id}(fill/H2O)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run())
