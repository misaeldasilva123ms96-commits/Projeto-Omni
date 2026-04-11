from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import LearningEvidence, LearningSignal, LearningSignalType, LearningSnapshot, PatternRecord


class LearningStore:
    def __init__(self, root: Path) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "learning"
        self.evidence_dir = self.base_dir / "evidence"
        self.patterns_dir = self.base_dir / "patterns"
        self.signals_dir = self.base_dir / "signals"
        self.snapshots_dir = self.base_dir / "snapshots"
        for directory in (self.evidence_dir, self.patterns_dir, self.signals_dir, self.snapshots_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def _pattern_path(self, pattern_key: str) -> Path:
        digest = hashlib.sha1(pattern_key.encode("utf-8")).hexdigest()
        return self.patterns_dir / f"{digest}.json"

    def append_evidence(self, evidence: LearningEvidence) -> None:
        path = self.evidence_dir / f"{evidence.source_type.value}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(evidence.as_dict(), ensure_ascii=False))
            handle.write("\n")

    def upsert_pattern(self, record: PatternRecord) -> None:
        self._pattern_path(record.pattern_key).write_text(
            json.dumps(record.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_pattern(self, pattern_key: str) -> PatternRecord | None:
        path = self._pattern_path(pattern_key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return PatternRecord.from_dict(payload)

    def load_patterns(self, *, category: str | None = None) -> list[PatternRecord]:
        records: list[PatternRecord] = []
        for path in self.patterns_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            record = PatternRecord.from_dict(payload)
            if category and record.category != category:
                continue
            records.append(record)
        records.sort(key=lambda item: item.last_seen, reverse=True)
        return records

    def append_signal(self, signal: LearningSignal) -> None:
        path = self.signals_dir / f"{signal.signal_type.value}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(signal.as_dict(), ensure_ascii=False))
            handle.write("\n")

    def load_recent_signals(self, *, limit: int = 50, signal_type: str | None = None) -> list[LearningSignal]:
        signals: list[LearningSignal] = []
        files = [self.signals_dir / f"{signal_type}.jsonl"] if signal_type else list(self.signals_dir.glob("*.jsonl"))
        for path in files:
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except Exception:
                    continue
                if not isinstance(payload, dict):
                    continue
                signals.append(
                    LearningSignal(
                        signal_id=str(payload.get("signal_id", "")),
                        signal_type=LearningSignalType(str(payload.get("signal_type", ""))),
                        source_pattern_key=str(payload.get("source_pattern_key", "")),
                        confidence=float(payload.get("confidence", 0.0) or 0.0),
                        weight=float(payload.get("weight", 0.0) or 0.0),
                        recommendation=str(payload.get("recommendation", "")),
                        evidence_summary=dict(payload.get("evidence_summary", {}) or {}),
                        timestamp=str(payload.get("timestamp", "")),
                        advisory=bool(payload.get("advisory", True)),
                        metadata=dict(payload.get("metadata", {}) or {}),
                    )
                )
        signals.sort(key=lambda item: item.timestamp, reverse=True)
        return signals[:limit]

    def save_snapshot(self, snapshot: LearningSnapshot) -> None:
        (self.snapshots_dir / f"{snapshot.snapshot_id}.json").write_text(
            json.dumps(snapshot.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
