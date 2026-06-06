import pytest
from hypothesis import given, strategies as st

from brain.runtime.intent_classifier import HybridIntentClassifier


@pytest.fixture
def classifier():
    return HybridIntentClassifier()


class TestClassifierSmoke:
    def test_decision_intent(self, classifier):
        result = classifier.classify("devo investir ou poupar?")
        assert result["intent"] == "decision"
        assert result["complex"] is True

    def test_conversa_intent(self, classifier):
        result = classifier.classify("ola tudo bem?")
        assert result["intent"] == "conversa"
        assert result["complex"] is False

    def test_dinheiro_intent(self, classifier):
        result = classifier.classify("como ganhar dinheiro?")
        assert result["intent"] == "dinheiro"
        assert result["complex"] is True

    def test_aprendizado_intent(self, classifier):
        result = classifier.classify("por onde comeco a programar?")
        assert result["intent"] == "aprendizado"
        assert result["complex"] is True

    def test_explicacao_intent(self, classifier):
        result = classifier.classify("o que e machine learning?")
        assert result["intent"] == "explicacao"
        assert result["complex"] is False

    def test_pessoal_intent(self, classifier):
        result = classifier.classify("quem e voce?")
        assert result["intent"] == "pessoal"
        assert result["complex"] is False

    def test_empty_message(self, classifier):
        result = classifier.classify("")
        assert result["intent"] == "conversa"
        assert result["complex"] is False

    def test_short_message(self, classifier):
        result = classifier.classify("oi")
        assert result["intent"] == "conversa"
        assert result["complex"] is False

    def test_long_complex_message(self, classifier):
        result = classifier.classify("eu gostaria de saber qual e a melhor forma de aprender python do zero absoluto")
        assert result["complex"] is True


class TestClassifierHistory:
    def test_history_triggers_intent(self, classifier):
        result = classifier.classify(
            "e depois disso?",
            history=[{"role": "user", "content": "quero aprender python"}],
        )
        assert result["intent"] == "aprendizado"

    def test_empty_history_fallback(self, classifier):
        result = classifier.classify("e depois disso?")
        assert result["intent"] == "conversa"

    def test_history_with_multiple_entries(self, classifier):
        result = classifier.classify(
            "explique melhor",
            history=[
                {"role": "user", "content": "o que e python"},
                {"role": "assistant", "content": "python e uma linguagem"},
            ],
        )
        assert result["intent"] == "explicacao"


class TestClassifierPropertyBased:
    @given(st.text(min_size=1, max_size=50))
    def test_never_raises(self, message):
        classifier = HybridIntentClassifier()
        result = classifier.classify(message)
        assert result["intent"] in {
            "decision", "dinheiro", "aprendizado", "explicacao", "pessoal", "conversa",
        }
        assert isinstance(result["complex"], bool)

    @given(st.lists(st.fixed_dictionaries({
        "role": st.sampled_from(["user", "assistant"]),
        "content": st.text(min_size=0, max_size=30),
    }), min_size=0, max_size=5))
    def test_with_history_never_raises(self, history):
        classifier = HybridIntentClassifier()
        result = classifier.classify("test message", history=history)
        assert result["intent"] in {
            "decision", "dinheiro", "aprendizado", "explicacao", "pessoal", "conversa",
        }

    @given(st.text(min_size=1, max_size=200))
    def test_complex_threshold(self, message):
        classifier = HybridIntentClassifier()
        result = classifier.classify(message)
        word_count = len(message.strip().split())
        if word_count > 8:
            assert result["complex"] is True
        elif word_count <= 8 and result["intent"] not in {"decision", "dinheiro", "aprendizado"}:
            assert result["complex"] is False


class TestClassifierEdgeCases:
    def test_message_with_numbers(self, classifier):
        assert classifier.classify("qual e a melhor opcao 1 ou 2?")["intent"] == "decision"

    def test_message_with_special_chars(self, classifier):
        result = classifier.classify("como $$$ ganhar $$$ dinheiro $$$?")
        assert result["intent"] == "dinheiro"

    def test_uppercase_message(self, classifier):
        result = classifier.classify("DEVO INVESTIR?")
        assert result["intent"] == "decision"

    def test_mixed_case(self, classifier):
        result = classifier.classify("O Que E Python?")
        assert result["intent"] == "explicacao"
