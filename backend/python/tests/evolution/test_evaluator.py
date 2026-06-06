import pytest

from brain.evolution.evaluator import (
    Evaluator,
    EvaluationResult,
    _tokenize,
    _jaccard_similarity,
    _contains_keywords,
    _history_coherence,
    _completeness,
    _efficiency,
)


class TestTokenize:
    def test_simple(self):
        assert _tokenize("ola mundo") == ["ola", "mundo"]

    def test_punctuation_removed(self):
        assert _tokenize("ola, mundo!") == ["ola", "mundo"]

    def test_case_normalized(self):
        assert _tokenize("Ola Mundo") == ["ola", "mundo"]

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_only_punctuation(self):
        assert _tokenize("!!! ???") == []


class TestJaccardSimilarity:
    def test_identical(self):
        assert _jaccard_similarity("gato cachorro", "gato cachorro") == 1.0

    def test_partial_overlap(self):
        sim = _jaccard_similarity("gato cachorro passaro", "gato cachorro peixe")
        assert 0.5 <= sim < 1.0

    def test_no_overlap(self):
        assert _jaccard_similarity("gato", "cachorro") == 0.0

    def test_one_empty(self):
        assert _jaccard_similarity("", "gato") == 0.0

    def test_both_empty(self):
        assert _jaccard_similarity("", "") == 0.0


class TestContainsKeywords:
    def test_all_keywords_present(self):
        score = _contains_keywords("aprender python do zero", "aprender python do zero e facil")
        assert score > 0.0

    def test_no_keywords_match(self):
        score = _contains_keywords("java script", "python e legal")
        assert score <= 0.5

    def test_short_message_returns_default(self):
        assert _contains_keywords("oi", "oi, tudo bem?") == 0.6

    def test_empty_message(self):
        assert _contains_keywords("", "resposta qualquer") == 0.5


class TestHistoryCoherence:
    def test_no_history(self):
        assert _history_coherence("resposta", []) == 0.75

    def test_with_recent_context(self):
        history = [{"role": "user", "content": "fale sobre python"}]
        score = _history_coherence("python e uma linguagem", history)
        assert score > 0.5

    def test_unrelated_to_history(self):
        history = [{"role": "user", "content": "fale sobre gatos"}]
        score = _history_coherence("python e uma linguagem", history)
        assert score < 0.7


class TestCompleteness:
    def test_question_gets_bonus(self):
        score = _completeness("o que e python?", "python e uma linguagem de programacao versatil usada em varios lugares")
        assert score > 0.5

    def test_how_question_bonus(self):
        score = _completeness("como programar em python?", "para programar em python voce precisa instalar o interpretador e escrever codigo")
        assert score > 0.5

    def test_empty_message(self):
        assert _completeness("", "resposta") == 0.6

    def test_low_coverage(self):
        score = _completeness("java c++ rust go", "python e legal")
        assert score < 0.5


class TestEfficiency:
    def test_ideal_length(self):
        score, flags = _efficiency("aprender python?", "python e uma linguagem de programacao usada para web dados e automacao")
        assert score >= 0.8
        assert flags == []

    def test_too_short(self):
        score, flags = _efficiency("aprender python?", "ok")
        assert score < 0.6
        assert "too_short" in flags

    def test_empty_response(self):
        score, flags = _efficiency("aprender python?", "")
        assert score == 0.0
        assert "empty_response" in flags


class TestEvaluator:
    def test_evaluate_basic(self):
        ev = Evaluator()
        result = ev.evaluate(
            session_id="sess-001",
            message="o que e python?",
            response="Python e uma linguagem de programacao de alto nivel, interpretada e versatil, usada em diversas areas como web, dados e automacao.",
            history=[],
        )
        assert "scores" in result
        assert "overall" in result
        assert "flags" in result
        assert "turn_id" in result
        assert "session_id" in result
        assert result["session_id"] == "sess-001"

    def test_evaluate_off_topic(self):
        ev = Evaluator()
        result = ev.evaluate(
            session_id="sess-001",
            message="qual a capital do brasil?",
            response="gosto muito de programar em python porque e divertido",
            history=[],
        )
        assert "off_topic" in result["flags"]

    def test_evaluate_repeated_pattern(self):
        ev = Evaluator()
        result = ev.evaluate(
            session_id="sess-001",
            message="fale algo",
            response="sim sim sim sim sim sim sim sim sim sim sim sim sim sim sim sim sim sim",
            history=[],
        )
        assert "repeated_pattern" in result["flags"]

    def test_evaluation_result_to_dict(self):
        er = EvaluationResult(
            session_id="sess-001",
            turn_id="abc123",
            scores={"relevance": 0.8, "coherence": 0.7, "completeness": 0.9, "efficiency": 0.85},
            overall=0.81,
            flags=["too_short"],
            timestamp="2026-01-01T00:00:00+00:00",
        )
        d = er.to_dict()
        assert d["session_id"] == "sess-001"
        assert d["overall"] == 0.81
        assert "too_short" in d["flags"]
