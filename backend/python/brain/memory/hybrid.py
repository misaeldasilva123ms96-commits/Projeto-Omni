from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brain.memory.store import normalize_user_profile


def _repair_text(value: str) -> str:
    if not value:
        return ""
    if any(marker in value for marker in ("Ã", "ï¿½")):
        try:
            repaired = value.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
            if repaired:
                return repaired
        except Exception:
            return value
    return value


class HybridMemory:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.user_path = self.base_dir / "user.json"
        self.preferences_path = self.base_dir / "preferences.json"
        self.notes_path = self.base_dir / "notes.md"
        self.learning_path = self.base_dir / "learning.json"
        self.feedback_path = self.base_dir / "feedback.json"
        self.ensure_files()

    def ensure_files(self) -> None:
        defaults = {
            self.user_path: normalize_user_profile({}),
            self.preferences_path: {"preferencias": []},
            self.learning_path: self._default_learning(),
            self.feedback_path: self._default_feedback_store(),
        }
        for path, content in defaults.items():
            if path.exists():
                continue
            path.write_text(
                json.dumps(content, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        if not self.notes_path.exists():
            self.notes_path.write_text("# User Notes\n", encoding="utf-8")

    def sync_from_store(self, memory_store: dict[str, object]) -> None:
        self.ensure_files()
        user = normalize_user_profile(memory_store.get("user", {}))

        try:
            self.user_path.write_text(
                json.dumps(user, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.preferences_path.write_text(
                json.dumps({"preferencias": user["preferencias"]}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            note_lines = ["# User Notes", ""]
            if user["nome"]:
                note_lines.append(f"- Nome aprendido: {user['nome']}")
            if user["trabalho"]:
                note_lines.append(f"- Trabalho identificado: {user['trabalho']}")
            if user["preferencias"]:
                note_lines.append("- Preferencias: " + ", ".join(user["preferencias"]))
            if user["goals"]:
                note_lines.append("- Objetivos: " + ", ".join(user["goals"]))
            if user["recurring_topics"]:
                note_lines.append("- Temas recorrentes: " + ", ".join(user["recurring_topics"]))
            note_lines.append(f"- Estilo de resposta: {user['response_style']}")
            note_lines.append(f"- Nivel de profundidade: {user['depth_preference']}")
            self.notes_path.write_text("\n".join(note_lines).strip() + "\n", encoding="utf-8")
        except Exception:
            return

    def _default_learning(self) -> dict[str, object]:
        return {
            "schema_version": 2,
            "evaluations": [],
            "capability_usage": {},
            "strategy_stats": {
                "current_version": 1,
                "versions": [],
                "strategies": {},
            },
            "patterns": {},
            "good_decisions": [],
            "response_styles": {},
            "explicit_feedback": [],
            "last_updated": None,
        }

    def _default_feedback_store(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "items": [],
            "stats": {"positive": 0, "negative": 0},
            "last_updated": None,
        }

    def load_learning(self) -> dict[str, object]:
        self.ensure_files()
        try:
            raw = self.learning_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            if not isinstance(parsed, dict):
                return self._default_learning()
        except Exception:
            return self._default_learning()

        learning = self._default_learning()
        learning.update(parsed)
        if not isinstance(learning.get("evaluations"), list):
            learning["evaluations"] = []
        if not isinstance(learning.get("capability_usage"), dict):
            learning["capability_usage"] = {}
        if not isinstance(learning.get("strategy_stats"), dict):
            learning["strategy_stats"] = self._default_learning()["strategy_stats"]
        if not isinstance(learning.get("patterns"), dict):
            learning["patterns"] = {}
        if not isinstance(learning.get("good_decisions"), list):
            learning["good_decisions"] = []
        if not isinstance(learning.get("response_styles"), dict):
            learning["response_styles"] = {}
        if not isinstance(learning.get("explicit_feedback"), list):
            learning["explicit_feedback"] = []
        return learning

    def load_feedback_store(self) -> dict[str, object]:
        self.ensure_files()
        try:
            raw = self.feedback_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return self._default_feedback_store()

    def record_learning(
        self,
        *,
        message: str,
        response: str,
        intent: str,
        capabilities: list[str],
        evaluation: dict[str, Any] | None = None,
        strategy_version: int | None = None,
        strategy_name: str | None = None,
        turn_id: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        learning = self.load_learning()
        timestamp = datetime.now(timezone.utc).isoformat()
        pattern_key = _repair_text(intent.strip() or "unknown")
        safe_message = _repair_text(message)[:220]
        safe_response = _repair_text(response)[:320]

        patterns = learning["patterns"]
        patterns[pattern_key] = int(patterns.get(pattern_key, 0)) + 1

        learning["response_styles"][pattern_key] = {
            "last_message": safe_message,
            "last_response": safe_response,
            "capabilities": capabilities,
            "updated_at": timestamp,
        }

        decisions = learning["good_decisions"]
        decisions.append(
            {
                "turn_id": turn_id,
                "session_id": session_id,
                "user_id": user_id,
                "intent": pattern_key,
                "message": safe_message,
                "response": safe_response,
                "capabilities": capabilities,
                "strategy": strategy_name,
                "timestamp": timestamp,
            }
        )
        learning["good_decisions"] = decisions[-50:]

        capability_usage = learning["capability_usage"]
        for capability in capabilities:
            record = capability_usage.get(capability, {"count": 0, "positive_feedback": 0, "negative_feedback": 0, "score": 0.0})
            record["count"] = int(record.get("count", 0)) + 1
            capability_usage[capability] = record

        if evaluation:
            evaluations = learning["evaluations"]
            evaluations.append(evaluation)
            learning["evaluations"] = evaluations[-100:]

        strategy_stats = learning["strategy_stats"]
        current_version = int(strategy_stats.get("current_version", 1) or 1)
        if strategy_version is not None:
            current_version = int(strategy_version)
        versions = strategy_stats.get("versions", [])
        if not isinstance(versions, list):
            versions = []
        if not versions or versions[-1].get("version") != current_version:
            versions.append({"version": current_version, "timestamp": timestamp})
        strategy_stats["current_version"] = current_version
        strategy_stats["versions"] = versions[-30:]
        strategies = strategy_stats.get("strategies", {})
        if not isinstance(strategies, dict):
            strategies = {}
        if strategy_name:
            strategy_entry = strategies.get(strategy_name, {"uses": 0, "positive_feedback": 0, "negative_feedback": 0, "feedback_score": 0.0})
            strategy_entry["uses"] = int(strategy_entry.get("uses", 0)) + 1
            strategy_entry["last_used_at"] = timestamp
            strategies[strategy_name] = strategy_entry
        strategy_stats["strategies"] = strategies

        if profile:
            strategy_stats["profile_snapshot"] = {
                "response_style": profile.get("response_style", "balanced"),
                "depth_preference": profile.get("depth_preference", "medium"),
                "themes": profile.get("recurring_topics", []),
            }

        learning["last_updated"] = timestamp
        self.learning_path.write_text(
            json.dumps(learning, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return learning

    def record_feedback(
        self,
        *,
        turn_id: str,
        session_id: str,
        user_id: str,
        value: str,
        text: str = "",
        strategy_name: str = "",
        capabilities: list[str] | None = None,
    ) -> dict[str, object]:
        learning = self.load_learning()
        feedback_store = self.load_feedback_store()
        timestamp = datetime.now(timezone.utc).isoformat()
        normalized_value = "up" if value == "up" else "down"
        delta = 0.1 if normalized_value == "up" else -0.1
        safe_capabilities = capabilities if isinstance(capabilities, list) else []

        entry = {
            "turn_id": turn_id,
            "session_id": session_id,
            "user_id": user_id,
            "value": normalized_value,
            "text": _repair_text(text.strip()),
            "strategy": strategy_name,
            "capabilities": safe_capabilities,
            "timestamp": timestamp,
        }

        items = feedback_store.get("items", [])
        if not isinstance(items, list):
            items = []
        items = [item for item in items if item.get("turn_id") != turn_id]
        items.append(entry)
        feedback_store["items"] = items[-200:]
        feedback_store["stats"] = {
            "positive": sum(1 for item in feedback_store["items"] if item.get("value") == "up"),
            "negative": sum(1 for item in feedback_store["items"] if item.get("value") == "down"),
        }
        feedback_store["last_updated"] = timestamp
        self.feedback_path.write_text(
            json.dumps(feedback_store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        explicit_feedback = learning.get("explicit_feedback", [])
        if not isinstance(explicit_feedback, list):
            explicit_feedback = []
        explicit_feedback = [item for item in explicit_feedback if item.get("turn_id") != turn_id]
        explicit_feedback.append(entry)
        learning["explicit_feedback"] = explicit_feedback[-200:]

        strategy_stats = learning.get("strategy_stats", self._default_learning()["strategy_stats"])
        strategies = strategy_stats.get("strategies", {})
        if not isinstance(strategies, dict):
            strategies = {}
        if strategy_name:
            strategy_entry = strategies.get(strategy_name, {"uses": 0, "positive_feedback": 0, "negative_feedback": 0, "feedback_score": 0.0})
            if normalized_value == "up":
                strategy_entry["positive_feedback"] = int(strategy_entry.get("positive_feedback", 0)) + 1
            else:
                strategy_entry["negative_feedback"] = int(strategy_entry.get("negative_feedback", 0)) + 1
            strategy_entry["feedback_score"] = round(float(strategy_entry.get("feedback_score", 0.0)) + delta, 3)
            strategy_entry["last_feedback_at"] = timestamp
            strategies[strategy_name] = strategy_entry
        strategy_stats["strategies"] = strategies
        learning["strategy_stats"] = strategy_stats

        capability_usage = learning.get("capability_usage", {})
        for capability in safe_capabilities:
            record = capability_usage.get(capability, {"count": 0, "positive_feedback": 0, "negative_feedback": 0, "score": 0.0})
            if normalized_value == "up":
                record["positive_feedback"] = int(record.get("positive_feedback", 0)) + 1
            else:
                record["negative_feedback"] = int(record.get("negative_feedback", 0)) + 1
            record["score"] = round(float(record.get("score", 0.0)) + delta, 3)
            capability_usage[capability] = record
        learning["capability_usage"] = capability_usage
        learning["last_updated"] = timestamp
        self.learning_path.write_text(
            json.dumps(learning, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return entry
