"""ChemAI Backend — 确定性判分引擎单元测试"""

from app.models import Judgment
from app.services.grading import (
    extract_option,
    grade_question,
    normalize_answer,
    parse_answer_sheet,
)


class TestNormalization:
    """化学/作答规范化"""

    def test_subscript_digits(self):
        """化学式下标（H₂O）与普通数字（H2O）等价"""
        assert normalize_answer("H₂O") == normalize_answer("H2O")

    def test_superscript_digits(self):
        assert normalize_answer("CO²") == normalize_answer("CO2")

    def test_whitespace_removed(self):
        assert normalize_answer("A B C") == normalize_answer("ABC")

    def test_fullwidth_letters(self):
        assert normalize_answer("Ａ") == normalize_answer("A")

    def test_option_letter_case_insensitive(self):
        assert normalize_answer("a") == normalize_answer("A")


class TestParseAnswerSheet:
    """OCR 文本 → 姓名/学号/逐题作答 解析"""

    def test_standard(self):
        parsed = parse_answer_sheet("姓名: 张三\n学号: 20250001\n1. B\n2. NaCl")
        assert parsed["name"] == "张三"
        assert parsed["student_no"] == "20250001"
        assert parsed["answers"] == [
            {"question_no": 1, "answer": "B"},
            {"question_no": 2, "answer": "NaCl"},
        ]

    def test_fullwidth_colon_and_separator(self):
        parsed = parse_answer_sheet("姓名：张三\n学号：20250001\n1、B")
        assert parsed["name"] == "张三"
        assert parsed["student_no"] == "20250001"
        assert parsed["answers"][0]["question_no"] == 1

    def test_fullwidth_question_number(self):
        parsed = parse_answer_sheet("姓名: 张三\n１、B\n２、NaCl")
        assert [a["question_no"] for a in parsed["answers"]] == [1, 2]

    def test_name_with_internal_space(self):
        # 手写 OCR 常在姓名中间插入空格，姓名不应被截断为单字
        parsed = parse_answer_sheet("姓名: 张 三\n学号: 20250001\n1. B")
        assert parsed["name"] == "张 三"

    def test_missing_name_prefix(self):
        parsed = parse_answer_sheet("张三\n1. B")
        assert parsed["name"] is None
        assert parsed["answers"][0]["question_no"] == 1


class TestExtractOption:
    """选项字母抽取"""

    def test_extract_plain(self):
        assert extract_option("A") == "A"

    def test_extract_with_punctuation(self):
        assert extract_option("B.") == "B"

    def test_extract_fullwidth(self):
        assert extract_option("Ｃ") == "C"

    def test_extract_none(self):
        assert extract_option("xyz") is None
        assert extract_option(None) is None


class TestGradeQuestion:
    """确定性判分"""

    def test_choice_correct(self):
        assert grade_question("choice", "A", "A") == Judgment.CORRECT

    def test_choice_mismatch_incorrect(self):
        assert grade_question("choice", "B", "A") == Judgment.INCORRECT

    def test_choice_unextractable_review(self):
        assert grade_question("choice", "", "A") == Judgment.REVIEW_REQUIRED
        assert grade_question("choice", "xyz", "A") == Judgment.REVIEW_REQUIRED

    def test_fill_chemistry_variant_correct(self):
        assert grade_question("fill", "H₂O", "H2O") == Judgment.CORRECT

    def test_fill_mismatch_incorrect(self):
        assert grade_question("fill", "NaCl", "NaOH") == Judgment.INCORRECT

    def test_fill_empty_review(self):
        assert grade_question("fill", "", "H2O") == Judgment.REVIEW_REQUIRED

    def test_no_reference_answer_review(self):
        assert grade_question("fill", "H2O", "") == Judgment.REVIEW_REQUIRED

    def test_subjective_review(self):
        assert grade_question("calc", "x=1", "x=1") == Judgment.REVIEW_REQUIRED

    def test_low_confidence_review(self):
        assert (
            grade_question("choice", "A", "A", confidence=0.3, confidence_threshold=0.6)
            == Judgment.REVIEW_REQUIRED
        )
