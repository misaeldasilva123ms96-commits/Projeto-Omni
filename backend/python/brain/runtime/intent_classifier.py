from __future__ import annotations

import re
from typing import Any


INTENT_PATTERNS: dict[str, list[str]] = {
    "decision": [
        r"\bdevo\b",
        r"\bou\b",
        r"\bqual e melhor\b",
        r"\bo que fazer\b",
        r"\bmelhor opcao\b",
        r"\bescolher entre\b",
    ],
    "dinheiro": [
        r"\bdinheiro\b",
        r"\bnegocio\b",
        r"\brenda\b",
        r"\bganhar dinheiro\b",
        r"\binvestir\b",
        r"\bpoupar\b",
        r"\blucro\b",
    ],
    "aprendizado": [
        r"\baprender\b",
        r"\bprogramacao\b",
        r"\bpor onde comeco\b",
        r"\bestudar\b",
        r"\bcomo aprender\b",
        r"\bcurs[o0]\b",
    ],
    "explicacao": [
        r"\bcomo funciona\b",
        r"\bo que e\b",
        r"\bexplique\b",
        r"\bsignificado\b",
        r"\bdefinicao\b",
        r"\bconceito\b",
    ],
    "pessoal": [
        r"\bquem e voce\b",
        r"\bcomo voce responde\b",
        r"\bvoce e um rob[o0]\b",
        r"\bcomo voce funciona\b",
    ],
}


COMPLEX_TRIGGER_INTENTS = frozenset({"decision", "dinheiro", "aprendizado"})


class HybridIntentClassifier:
    def __init__(self) -> None:
        self._compiled: dict[str, list[re.Pattern[str]]] = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in INTENT_PATTERNS.items()
        }

    def classify(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        raw = message.strip().lower()
        intent = self._regex_classify(raw, history or [])
        return {
            "intent": intent,
            "complex": len(raw.split()) > 8 or intent in COMPLEX_TRIGGER_INTENTS,
        }

    def _regex_classify(self, raw: str, history: list[dict[str, str]]) -> str:
        for intent, patterns in self._compiled.items():
            if any(p.search(raw) for p in patterns):
                return intent

        history_text = " ".join(
            str(item.get("content", "")).lower()
            for item in history
            if isinstance(item, dict)
        )
        for intent, patterns in self._compiled.items():
            if any(p.search(history_text) for p in patterns):
                return intent

        return "conversa"
