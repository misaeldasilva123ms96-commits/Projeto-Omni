from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..persistence import atomic_write_json, atomic_write_text, file_lock, locked_json_update


LEARNING_SCHEMA_VERSION = 2


def default_learning_store() -> dict[str, Any]:
    return {
        "schema_version": LEARNING_SCHEMA_VERSION,
        "patterns": {},
        "good_decisions": [],
        "response_styles": {},
        "evaluations": [],
        "capability_usage": {},
        "strategy_versions": [],
        "meta": {
            "last_updated": "",
            "current_evolution_version": 0,
        },
    }


class HybridMemory:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.user_path = self.base_dir / "user.json"
        self.preferences_path = self.base_dir / "preferences.json"
        self.notes_path = self.base_dir / "notes.md"
        self.learning_path = self.base_dir / "learning.json"
        self.ensure_files()

    def ensure_files(self) -> None:
        defaults = {
            self.user_path: {"nome": ""},
            self.preferences_path: {"preferencias": []},
            self.learning_path: default_learning_store(),
        }
        for path, content in defaults.items():
            if path.exists():
                continue
            try:
                with file_lock(path):
                    if not path.exists():
                        atomic_write_json(path, content)
            except Exception:
                continue

        if not self.notes_path.exists():
            try:
                atomic_write_text(self.notes_path, "# User Notes\n")
            except Exception:
                pass

    def sync_from_store(self, memory_store: dict[str, object]) -> None:
        self.ensure_files()
        user = memory_store.get("user", {})
        if not isinstance(user, dict):
            user = {"nome": "", "preferencias": []}

        nome = user.get("nome", "")
        preferencias = user.get("preferencias", [])
        if not isinstance(nome, str):
            nome = ""
        if not isinstance(preferencias, list):
            preferencias = []

        try:
            atomic_write_json(self.user_path, {"nome": nome.strip()})
            atomic_write_json(
                self.preferences_path,
                {"preferencias": [str(item).strip() for item in preferencias if str(item).strip()]},
            )
            note_lines = ["# User Notes", ""]
            if nome.strip():
                note_lines.append(f"- Nome aprendido: {nome.strip()}")
            if preferencias:
                note_lines.append(
                    "- Preferencias: " + ", ".join(
                        str(item).strip() for item in preferencias if str(item).strip()
                    )
                )
            atomic_write_text(self.notes_path, "\n".join(note_lines).strip() + "\n")
        except Exception:
            return

    def _migrate_learning(self, payload: dict[str, Any]) -> dict[str, Any]:
        if int(payload.get("schema_version", 1)) >= LEARNING_SCHEMA_VERSION:
            merged = default_learning_store()
            merged.update(payload)
            if not isinstance(merged.get("meta"), dict):
                merged["meta"] = default_learning_store()["meta"]
            return merged

        migrated = default_learning_store()
        migrated["patterns"] = payload.get("patterns", {}) if isinstance(payload.get("patterns"), dict) else {}
        migrated["good_decisions"] = payload.get("good_decisions", []) if isinstance(payload.get("good_decisions"), list) else []
        migrated["response_styles"] = payload.get("response_styles", {}) if isinstance(payload.get("response_styles"), dict) else {}
        migrated["meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        return migrated

    def load_learning(self) -> dict[str, Any]:
        self.ensure_files()
        try:
            raw = self.learning_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            if isinstance(parsed, dict):
                return self._migrate_learning(parsed)
        except Exception:
            pass
        return default_learning_store()

    def save_learning(self, learning: dict[str, Any]) -> None:
        payload = self._migrate_learning(learning)
        payload["schema_version"] = LEARNING_SCHEMA_VERSION
        meta = payload.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
        meta["last_updated"] = datetime.now(timezone.utc).isoformat()
        payload["meta"] = meta
        try:
            with file_lock(self.learning_path):
                atomic_write_json(self.learning_path, payload)
        except Exception:
            return

    def record_learning(self, *, message: str, response: str, intent: str, capabilities: list[str]) -> None:
        def mutate(learning: dict[str, Any]) -> None:
            learning.update(self._migrate_learning(learning))
            self._record_learning_payload(
                learning, message=message, response=response, intent=intent, capabilities=capabilities
            )
            learning["schema_version"] = LEARNING_SCHEMA_VERSION
            learning.setdefault("meta", {})["last_updated"] = datetime.now(timezone.utc).isoformat()
        locked_json_update(self.learning_path, default_learning_store, mutate)

    def _record_learning_payload(self, learning: dict[str, Any], *, message: str, response: str, intent: str, capabilities: list[str]) -> None:
        patterns = learning.get("patterns", {})
        if not isinstance(patterns, dict):
            patterns = {}
        pattern_key = intent.strip() or "unknown"
        patterns[pattern_key] = int(patterns.get(pattern_key, 0)) + 1
        learning["patterns"] = patterns

        response_styles = learning.get("response_styles", {})
        if not isinstance(response_styles, dict):
            response_styles = {}
        response_styles[pattern_key] = {
            "last_message": message[:140],
            "last_response": response[:220],
            "capabilities": capabilities,
        }
        learning["response_styles"] = response_styles

        decisions = learning.get("good_decisions", [])
        if not isinstance(decisions, list):
            decisions = []
        decisions.append(
            {
                "intent": pattern_key,
                "message": message[:140],
                "response": response[:220],
                "capabilities": capabilities,
            }
        )
        learning["good_decisions"] = decisions[-40:]

        capability_usage = learning.get("capability_usage", {})
        if not isinstance(capability_usage, dict):
            capability_usage = {}
        for capability in capabilities:
            key = str(capability).strip()
            if not key:
                continue
            capability_usage[key] = int(capability_usage.get(key, 0)) + 1
        learning["capability_usage"] = capability_usage


    def record_evaluation(self, evaluation: dict[str, Any]) -> None:
        def mutate(learning: dict[str, Any]) -> None:
            learning.update(self._migrate_learning(learning))
            evaluations = learning.get("evaluations", [])
            if not isinstance(evaluations, list):
                evaluations = []
            evaluations.append(evaluation)
            learning["evaluations"] = evaluations[-200:]
            learning["schema_version"] = LEARNING_SCHEMA_VERSION
            learning.setdefault("meta", {})["last_updated"] = datetime.now(timezone.utc).isoformat()
        locked_json_update(self.learning_path, default_learning_store, mutate)

    def record_strategy_version(self, version_info: dict[str, Any]) -> None:
        def mutate(learning: dict[str, Any]) -> None:
            learning.update(self._migrate_learning(learning))
            strategy_versions = learning.get("strategy_versions", [])
            if not isinstance(strategy_versions, list):
                strategy_versions = []
            strategy_versions.append(version_info)
            learning["strategy_versions"] = strategy_versions[-50:]
            meta = learning.get("meta", {})
            if not isinstance(meta, dict):
                meta = {}
            meta["current_evolution_version"] = int(version_info.get("version", 0))
            meta["last_updated"] = datetime.now(timezone.utc).isoformat()
            learning["meta"] = meta
            learning["schema_version"] = LEARNING_SCHEMA_VERSION
        locked_json_update(self.learning_path, default_learning_store, mutate)
