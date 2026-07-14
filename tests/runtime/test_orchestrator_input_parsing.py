from __future__ import annotations

import inspect
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime import orchestrator as orchestrator_module  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator  # noqa: E402


def _orchestrator_without_runtime_setup() -> BrainOrchestrator:
    return object.__new__(BrainOrchestrator)


def test_user_learning_parsers_avoid_polynomial_regular_expressions() -> None:
    source = inspect.getsource(orchestrator_module)

    assert 're.sub(r"[?.!,:;]+$"' not in source
    assert 're.split(r"\\s+e\\s+|,|\\."' not in source
    assert 're.search(r"\\bprefiro\\s+(.+)$"' not in source


def test_user_learning_preserves_name_and_preference_extraction() -> None:
    orchestrator = _orchestrator_without_runtime_setup()
    memory: dict[str, object] = {"user": {"nome": "", "preferencias": []}}

    orchestrator._extract_user_learning(
        memory,
        "Meu nome é Ana Maria e prefiro respostas objetivas.",
    )

    assert memory == {
        "user": {
            "nome": "Ana Maria",
            "preferencias": ["respostas objetivas"],
        }
    }


def test_user_learning_parsers_handle_adversarial_bounded_input() -> None:
    orchestrator = _orchestrator_without_runtime_setup()
    punctuation = "!" * 8_000 + "x"

    assert orchestrator._normalize_text(punctuation) == punctuation
    assert orchestrator._clean_extracted_name("Ana" + (" " * 8_000) + "e Silva") == "Ana"

    memory: dict[str, object] = {"user": {"nome": "", "preferencias": []}}
    orchestrator._extract_user_learning(
        memory,
        "prefiro" + (" " * 8_000) + "respostas curtas",
    )
    assert memory["user"] == {"nome": "", "preferencias": ["respostas curtas"]}


def test_preference_parser_preserves_word_boundary_and_multiline_behavior() -> None:
    orchestrator = _orchestrator_without_runtime_setup()

    assert orchestrator._extract_preference("xprefiro detalhes") == ""
    assert orchestrator._extract_preference("eu prefiro\ndetalhes") == "detalhes"
    assert orchestrator._extract_preference("eu prefiro detalhes\nextras") == ""
    assert orchestrator._extract_preference("eu prefiro detalhes\n") == "detalhes"
    assert orchestrator._extract_preference("eu prefiro\n\t") == "\t"

    repeated_markers = ("prefiro x " * 2_000) + "\nextras"
    assert orchestrator._extract_preference(repeated_markers) == ""
