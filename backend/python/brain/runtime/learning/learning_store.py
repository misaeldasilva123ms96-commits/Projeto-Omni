from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import LearningEvidence, LearningSignal, LearningSignalType, LearningSnapshot, PatternRecord
from .redaction import redact_sensitive_payload


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
            handle.write(json.dumps(redact_sensitive_payload(evidence.as_dict()), ensure_ascii=False))
            handle.write("\n")

    def upsert_pattern(self, record: PatternRecord) -> None:
        self._pattern_path(record.pattern_key).write_text(
            json.dumps(redact_sensitive_payload(record.as_dict()), ensure_ascii=False, indent=2),
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
            handle.write(json.dumps(redact_sensitive_payload(signal.as_dict()), ensure_ascii=False))
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
            json.dumps(redact_sensitive_payload(snapshot.as_dict()), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class ControlledLearningStore:
    """Phase 10 append-only store for safe learning records and advisory signals."""

    def __init__(self, root: Path, *, max_records: int = 200) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "learning" / "controlled"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.records_path = self.base_dir / "learning_records.jsonl"
        self.signals_path = self.base_dir / "improvement_signals.jsonl"
        self.max_records = max(1, int(max_records))

    def append_learning_record(self, record: dict[str, Any]) -> bool:
        return self._append_jsonl(self.records_path, record)

    def append_improvement_signal(self, signal: dict[str, Any]) -> bool:
        return self._append_jsonl(self.signals_path, signal)

    def read_recent_learning_records(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return self._read_recent_jsonl(self.records_path, limit=limit)

    def read_recent_improvement_signals(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return self._read_recent_jsonl(self.signals_path, limit=limit)

    def filter_learning_records(self, *, failure_class: str | None = None, decision_issue: str | None = None, tool_used: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        failure_class = str(failure_class or "").strip()
        decision_issue = str(decision_issue or "").strip()
        tool_used = str(tool_used or "").strip()
        records = self.read_recent_learning_records(limit=max(limit, self.max_records))
        filtered: list[dict[str, Any]] = []
        for record in records:
            if failure_class and str(record.get("failure_class", "") or "").strip() != failure_class:
                continue
            decision_payload = record.get("decision_evaluation") if isinstance(record.get("decision_evaluation"), dict) else {}
            outcome_payload = record.get("execution_outcome") if isinstance(record.get("execution_outcome"), dict) else {}
            if decision_issue and str(decision_payload.get("decision_issue", "") or "").strip() != decision_issue:
                continue
            if tool_used and str(outcome_payload.get("tool_used", "") or "").strip() != tool_used:
                continue
            filtered.append(record)
            if len(filtered) >= limit:
                break
        return filtered

    def group_learning_records(self, *, field_name: str, limit: int = 100) -> dict[str, int]:
        grouped: dict[str, int] = {}
        for record in self.read_recent_learning_records(limit=max(limit, self.max_records)):
            value = self._group_value(record, field_name)
            if not value:
                continue
            grouped[value] = grouped.get(value, 0) + 1
        return grouped

    def _group_value(self, record: dict[str, Any], field_name: str) -> str:
        if field_name == "failure_class":
            return str(record.get("failure_class", "") or "").strip()
        if field_name == "decision_issue":
            payload = record.get("decision_evaluation") if isinstance(record.get("decision_evaluation"), dict) else {}
            return str(payload.get("decision_issue", "") or "").strip()
        if field_name == "tool_used":
            payload = record.get("execution_outcome") if isinstance(record.get("execution_outcome"), dict) else {}
            return str(payload.get("tool_used", "") or "").strip()
        return str(record.get(field_name, "") or "").strip()

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> bool:
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(redact_sensitive_payload(payload), ensure_ascii=False))
                handle.write("\n")
            self._trim_jsonl(path)
            return True
        except OSError:
            return False

    def _read_recent_jsonl(self, path: Path, *, limit: int) -> list[dict[str, Any]]:
        if limit <= 0 or not path.exists():
            return []
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return []
        out: list[dict[str, Any]] = []
        for line in reversed(text.splitlines()):
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                out.append(payload)
            if len(out) >= limit:
                break
        return out

    def _trim_jsonl(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except OSError:
            return
        if len(lines) <= self.max_records:
            return
        trimmed = lines[-self.max_records :]
        try:
            path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")
        except OSError:
            return
