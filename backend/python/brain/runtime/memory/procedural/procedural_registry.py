from __future__ import annotations

import json
import threading
from pathlib import Path

from .models import ProceduralPattern


class ProceduralRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.base_dir = root / ".logs" / "fusion-runtime" / "memory"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "procedural_patterns.json"
        self._lock = threading.RLock()
        self._patterns = self._load()

    def upsert(self, pattern: ProceduralPattern) -> None:
        with self._lock:
            self._patterns[pattern.pattern_id] = pattern
            self._flush()

    def all_patterns(self) -> list[ProceduralPattern]:
        with self._lock:
            return [ProceduralPattern.from_dict(pattern.as_dict()) for pattern in self._patterns.values()]

    def lookup_by_goal_type(self, goal_type: str) -> list[ProceduralPattern]:
        with self._lock:
            return [
                ProceduralPattern.from_dict(pattern.as_dict())
                for pattern in self._patterns.values()
                if goal_type in pattern.applicable_goal_types or not pattern.applicable_goal_types
            ]

    def best_pattern_for(self, *, goal_type: str, constraint_types: list[str] | None = None) -> ProceduralPattern | None:
        candidates = self.lookup_by_goal_type(goal_type)
        if constraint_types:
            filtered = []
            for pattern in candidates:
                if not pattern.applicable_constraint_types:
                    filtered.append(pattern)
                    continue
                if any(item in pattern.applicable_constraint_types for item in constraint_types):
                    filtered.append(pattern)
            candidates = filtered
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item.success_rate, item.sample_size, item.last_updated), reverse=True)
        return candidates[0]

    def _load(self) -> dict[str, ProceduralPattern]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            str(item.get("pattern_id")): ProceduralPattern.from_dict(item)
            for item in payload.get("patterns", [])
            if isinstance(item, dict) and str(item.get("pattern_id", "")).strip()
        }

    def _flush(self) -> None:
        payload = {"patterns": [pattern.as_dict() for pattern in self._patterns.values()]}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
