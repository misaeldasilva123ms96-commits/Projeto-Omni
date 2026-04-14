from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


KNOWN_ENGINE_MODES = {"packaged_upstream", "authority_fallback"}
KNOWN_FALLBACK_REASONS = (
    "heavy_execution_request",
    "packaged_import_failed",
    "fallback_policy_triggered",
)


def default_engine_adoption_payload(*, session_id: str = "") -> dict[str, Any]:
    return {
        "scope": "session",
        "session_id": session_id,
        "engine_counters": {
            "packaged_upstream": 0,
            "authority_fallback": 0,
            "fallback_by_reason": {reason: 0 for reason in KNOWN_FALLBACK_REASONS},
        },
    }


class EngineAdoptionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.base_dir = root / ".logs" / "fusion-runtime"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "engine_adoption.json"
        self._lock = threading.RLock()
        self._state = self._load()

    def record_selection(
        self,
        *,
        engine_mode: str,
        engine_reason: str = "",
        session_id: str = "",
    ) -> dict[str, Any]:
        normalized_mode = str(engine_mode).strip()
        if normalized_mode not in KNOWN_ENGINE_MODES:
            return self.snapshot()

        normalized_session_id = str(session_id).strip()
        normalized_reason = str(engine_reason).strip()

        with self._lock:
            current_session_id = str(self._state.get("session_id", "")).strip()
            if normalized_session_id and current_session_id and current_session_id != normalized_session_id:
                self._state = default_engine_adoption_payload(session_id=normalized_session_id)
            elif normalized_session_id and not current_session_id:
                self._state["session_id"] = normalized_session_id

            counters = self._state.setdefault("engine_counters", {})
            counters[normalized_mode] = int(counters.get(normalized_mode, 0)) + 1

            if normalized_mode == "authority_fallback" and normalized_reason in KNOWN_FALLBACK_REASONS:
                fallback = counters.setdefault(
                    "fallback_by_reason",
                    {reason: 0 for reason in KNOWN_FALLBACK_REASONS},
                )
                fallback[normalized_reason] = int(fallback.get(normalized_reason, 0)) + 1

            self.flush()
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._state, ensure_ascii=False))

    def flush(self) -> None:
        with self._lock:
            temp_path = self.path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(self.path)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return default_engine_adoption_payload()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return default_engine_adoption_payload()
        return self._normalize(payload)

    @staticmethod
    def _normalize(payload: object) -> dict[str, Any]:
        base = default_engine_adoption_payload()
        if not isinstance(payload, dict):
            return base

        base["scope"] = "session"
        base["session_id"] = str(payload.get("session_id", "")).strip()
        counters = payload.get("engine_counters")
        if isinstance(counters, dict):
            base["engine_counters"]["packaged_upstream"] = int(counters.get("packaged_upstream", 0) or 0)
            base["engine_counters"]["authority_fallback"] = int(counters.get("authority_fallback", 0) or 0)
            fallback = counters.get("fallback_by_reason")
            if isinstance(fallback, dict):
                for reason in KNOWN_FALLBACK_REASONS:
                    base["engine_counters"]["fallback_by_reason"][reason] = int(fallback.get(reason, 0) or 0)
        return base
