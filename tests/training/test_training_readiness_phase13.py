from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def _load_script(name: str):
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = _load_script("validate_training_candidate")
exporter = _load_script("export_training_candidates")


def clean_positive() -> dict:
    return {
        "schema_version": "omni_training_candidate_v1",
        "id": "clr-safe",
        "source": "controlled_learning_record",
        "input": "Explique o fluxo de runtime.",
        "expected_output": "O runtime decide, executa e observa com sucesso.",
        "runtime_mode": "FULL_COGNITIVE_RUNTIME",
        "selected_strategy": "DIRECT_RESPONSE",
        "selected_tool": "",
        "user_visible_success": True,
        "learning_safety": {
            "learning_classification": "positive_training_candidate",
            "positive_training_candidate": True,
            "negative_training_candidate": False,
            "runtime_mode": "FULL_COGNITIVE_RUNTIME",
            "fallback_triggered": False,
            "provider_succeeded": True,
            "tool_status": "",
            "governance_status": "",
            "error_public_code": "",
            "redaction_applied": False,
            "learning_safety_reason": "clean_high_confidence_success",
        },
        "metadata": {"execution_path": "node_execution", "provider_actual": "openai"},
    }


def assert_rejected(payload: dict) -> None:
    with pytest.raises(validator.ValidationError):
        validator.validate_training_candidate(payload, positive=True)


def test_validator_accepts_clean_positive_candidate() -> None:
    assert validator.validate_training_candidate(clean_positive(), positive=True)["ok"] is True


@pytest.mark.parametrize("runtime_mode", ["SAFE_FALLBACK", "NODE_FALLBACK", "MATCHER_SHORTCUT", "TOOL_BLOCKED", "PROVIDER_UNAVAILABLE"])
def test_validator_rejects_unsafe_positive_runtime_modes(runtime_mode: str) -> None:
    payload = clean_positive()
    payload["runtime_mode"] = runtime_mode
    payload["learning_safety"]["runtime_mode"] = runtime_mode
    payload["learning_safety"]["positive_training_candidate"] = False
    payload["learning_safety"]["learning_classification"] = "failure_memory"
    assert_rejected(payload)


def test_validator_rejects_provider_failure_tool_block_and_governance_block() -> None:
    provider_failure = clean_positive()
    provider_failure["learning_safety"]["provider_succeeded"] = False

    tool_block = clean_positive()
    tool_block["learning_safety"]["tool_status"] = "blocked"

    governance_block = clean_positive()
    governance_block["learning_safety"]["governance_status"] = "blocked"

    for payload in (provider_failure, tool_block, governance_block):
        assert_rejected(payload)


def test_validator_rejects_missing_learning_safety_and_sensitive_payloads() -> None:
    missing = clean_positive()
    missing.pop("learning_safety")
    assert_rejected(missing)

    sensitive_values = [
        ("input", "user@example.com"),
        ("input", "sk-proj-abcdefghijklmnop"),
        ("input", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature"),
        ("input", "Bearer abcdefghijklmnopqrstuvwxyz"),
        ("input", "123.456.789-09"),
        ("input", "/home/render/project/.env"),
    ]
    for key, value in sensitive_values:
        payload = clean_positive()
        payload[key] = value
        assert_rejected(payload)

    raw = clean_positive()
    raw["metadata"]["raw_payload"] = {"secret": "x"}
    assert_rejected(raw)


def test_exporter_dry_run_does_not_write_unsafe_records_and_separates_eval_cases() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "learning_records.jsonl"
        positive_record = {
            "record_id": "clr-ok",
            "input_preview": "Explique runtime",
            "notes": "Resposta segura",
            "runtime_mode": "FULL_COGNITIVE_RUNTIME",
            "selected_strategy": "DIRECT_RESPONSE",
            "selected_tool": "",
            "execution_path": "node_execution",
            "provider_actual": "openai",
            "success": True,
            "learning_safety": clean_positive()["learning_safety"],
        }
        unsafe_record = {
            "record_id": "clr-fallback",
            "input_preview": "oi",
            "notes": "fallback",
            "runtime_mode": "SAFE_FALLBACK",
            "success": False,
            "learning_safety": {
                "learning_classification": "failure_memory",
                "positive_training_candidate": False,
                "negative_training_candidate": True,
                "runtime_mode": "SAFE_FALLBACK",
                "fallback_triggered": True,
                "provider_succeeded": False,
                "tool_status": "",
                "governance_status": "",
                "error_public_code": "",
                "redaction_applied": False,
                "learning_safety_reason": "fallback_triggered",
            },
        }
        source.write_text(
            json.dumps(positive_record, ensure_ascii=False) + "\n" + json.dumps(unsafe_record, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        positive_output = root / "positive.jsonl"
        eval_output = root / "eval.jsonl"

        dry = exporter.export_candidates(source, positive_output=positive_output, eval_output=eval_output, write=False)
        assert dry["dry_run"] is True
        assert dry["positive_candidates"] == 1
        assert dry["eval_cases"] == 1
        assert not positive_output.exists()
        assert not eval_output.exists()

        written = exporter.export_candidates(source, positive_output=positive_output, eval_output=eval_output, write=True)
        assert written["dry_run"] is False
        assert positive_output.exists()
        assert eval_output.exists()
        assert len(positive_output.read_text(encoding="utf-8").splitlines()) == 1
        assert len(eval_output.read_text(encoding="utf-8").splitlines()) == 1


def test_eval_seed_files_are_valid_jsonl() -> None:
    for path in sorted((PROJECT_ROOT / "data" / "evals").glob("*.jsonl")):
        records = validator.read_jsonl(path)
        assert records, path
        for record in records:
            assert validator.validate_training_candidate(record, positive=False)["ok"] is True


def test_scripts_default_to_no_network_upload_and_dry_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "missing.jsonl"
        summary = exporter.export_candidates(source)
        assert summary["dry_run"] is True
        assert summary["records_read"] == 0
        assert summary["positive_candidates"] == 0
