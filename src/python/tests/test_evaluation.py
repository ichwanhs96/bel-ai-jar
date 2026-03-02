"""
Tests for bel_ai_jar.evaluation module
"""
import pytest
from unittest.mock import patch, MagicMock

from bel_ai_jar.config import Config
from bel_ai_jar.evaluation import (
    _generate_fallback_questions,
    ask_questions,
    evaluate_code_changes,
    generate_questions_from_diff,
)


SAMPLE_DIFF = """\
diff --git a/sample.py b/sample.py
index 0000000..1111111 100644
--- a/sample.py
+++ b/sample.py
@@ -0,0 +1,5 @@
+def add(a, b):
+    return a + b
+
+class Calculator:
+    pass
"""

SAMPLE_QUESTIONS = [
    {
        "question": "What does `add` do?",
        "options": ["Adds two numbers", "Subtracts", "Multiplies", "Divides"],
        "correct_answer": "Adds two numbers",
    }
]


@pytest.fixture()
def default_config():
    return Config(total_questions=1, passing_grade=100, answer_options=4)


class TestFallbackQuestions:
    def test_generates_questions_from_diff(self, default_config):
        questions = _generate_fallback_questions(SAMPLE_DIFF, default_config)
        assert isinstance(questions, list)
        # Should find at least one def/class line
        assert len(questions) >= 1

    def test_does_not_exceed_total_questions(self, default_config):
        config = Config(total_questions=1)
        questions = _generate_fallback_questions(SAMPLE_DIFF, config)
        assert len(questions) <= 1

    def test_empty_diff_returns_empty_list(self, default_config):
        questions = _generate_fallback_questions("", default_config)
        assert questions == []


class TestAskQuestions:
    def test_correct_answer_increments_count(self, capsys):
        with patch("builtins.input", side_effect=["1"]):
            # Make correct_answer match the first option so answer "1" is correct
            questions = [
                {
                    "question": "Q?",
                    "options": ["Correct", "Wrong A", "Wrong B", "Wrong C"],
                    "correct_answer": "Correct",
                }
            ]
            # Patch random.shuffle to keep option order stable
            with patch("random.shuffle"):
                score = ask_questions(questions)
        assert score == 1

    def test_wrong_answer_does_not_increment_count(self, capsys):
        with patch("builtins.input", side_effect=["2"]):
            questions = [
                {
                    "question": "Q?",
                    "options": ["Correct", "Wrong", "Wrong B", "Wrong C"],
                    "correct_answer": "Correct",
                }
            ]
            with patch("random.shuffle"):
                score = ask_questions(questions)
        assert score == 0

    def test_keyboard_interrupt_returns_zero(self):
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            questions = [
                {
                    "question": "Q?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                }
            ]
            score = ask_questions(questions)
        assert score == 0


class TestEvaluateCodeChanges:
    def test_pass_when_all_correct(self, default_config):
        with patch(
            "bel_ai_jar.evaluation.generate_questions_from_diff",
            return_value=SAMPLE_QUESTIONS,
        ):
            with patch("bel_ai_jar.evaluation.ask_questions", return_value=1):
                result = evaluate_code_changes(SAMPLE_DIFF, default_config)
        assert result is True

    def test_fail_when_score_below_passing_grade(self):
        config = Config(total_questions=1, passing_grade=100, strict_mode=True)
        with patch(
            "bel_ai_jar.evaluation.generate_questions_from_diff",
            return_value=SAMPLE_QUESTIONS,
        ):
            with patch("bel_ai_jar.evaluation.ask_questions", return_value=0):
                result = evaluate_code_changes(SAMPLE_DIFF, config)
        assert result is False

    def test_pass_when_no_questions_generated(self, default_config):
        with patch(
            "bel_ai_jar.evaluation.generate_questions_from_diff", return_value=[]
        ):
            result = evaluate_code_changes(SAMPLE_DIFF, default_config)
        assert result is True


class TestGenerateQuestionsFromDiff:
    def test_uses_llm_and_trims_to_total(self, default_config):
        many_questions = SAMPLE_QUESTIONS * 5
        with patch(
            "bel_ai_jar.evaluation.generate_questions_with_llm",
            return_value=many_questions,
        ):
            questions = generate_questions_from_diff(SAMPLE_DIFF, default_config)
        assert len(questions) == default_config.total_questions

    def test_falls_back_when_llm_returns_too_few(self, default_config):
        with patch(
            "bel_ai_jar.evaluation.generate_questions_with_llm", return_value=[]
        ):
            questions = generate_questions_from_diff(SAMPLE_DIFF, default_config)
        # Should still return some questions via fallback
        assert isinstance(questions, list)
