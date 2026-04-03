from __future__ import annotations

import json
from pathlib import Path


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
            self.learning_path: {"patterns": {}, "good_decisions": [], "response_styles": {}},
        }
        for path, content in defaults.items():
            if path.exists():
                continue
            try:
                path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                continue

        if not self.notes_path.exists():
            try:
                self.notes_path.write_text("# User Notes\n", encoding="utf-8")
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
            self.user_path.write_text(
                json.dumps({"nome": nome.strip()}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.preferences_path.write_text(
                json.dumps(
                    {"preferencias": [str(item).strip() for item in preferencias if str(item).strip()]},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
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
            self.notes_path.write_text("\n".join(note_lines).strip() + "\n", encoding="utf-8")
        except Exception:
            return

    def load_learning(self) -> dict[str, object]:
        self.ensure_files()
        try:
            raw = self.learning_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return {"patterns": {}, "good_decisions": [], "response_styles": {}}

    def record_learning(self, *, message: str, response: str, intent: str, capabilities: list[str]) -> None:
        learning = self.load_learning()
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
        learning["good_decisions"] = decisions[-20:]

        try:
            self.learning_path.write_text(
                json.dumps(learning, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            return
