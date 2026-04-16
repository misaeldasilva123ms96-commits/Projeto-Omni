from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .evolution_models import EvolutionProposalRecord, EvolutionProposalStatus


class EvolutionRegistry:
    """Minimal filesystem registry for governed evolution proposals."""

    def __init__(self, root: Path) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "evolution"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "evolution_registry.json"
        self._lock = threading.RLock()
        self._proposals: dict[str, EvolutionProposalRecord] = {}
        if self.path.exists():
            self.reload_from_disk()

    def register(self, proposal: EvolutionProposalRecord) -> EvolutionProposalRecord:
        with self._lock:
            self._proposals[proposal.proposal_id] = proposal
            self.flush()
            return proposal

    def get(self, proposal_id: str) -> EvolutionProposalRecord | None:
        with self._lock:
            self._reload_if_available()
            key = str(proposal_id or "").strip()
            if not key:
                return None
            return self._proposals.get(key)

    def list(self, *, status: str | None = None, limit: int = 50) -> list[EvolutionProposalRecord]:
        with self._lock:
            self._reload_if_available()
            rows = list(self._proposals.values())
            if status:
                desired = str(status).strip().lower()
                rows = [item for item in rows if item.status == desired]
            rows.sort(key=lambda item: item.updated_at, reverse=True)
            return rows[: max(1, int(limit or 50))]

    def update_status(self, proposal_id: str, *, status: EvolutionProposalStatus) -> EvolutionProposalRecord | None:
        with self._lock:
            self._reload_if_available()
            proposal = self._proposals.get(str(proposal_id or "").strip())
            if proposal is None:
                return None
            proposal.status = status.value
            self.flush()
            return proposal

    def get_summary(self, *, recent_limit: int = 10) -> dict[str, Any]:
        with self._lock:
            self._reload_if_available()
            counts = {status.value: 0 for status in EvolutionProposalStatus}
            for proposal in self._proposals.values():
                if proposal.status in counts:
                    counts[proposal.status] += 1
            recent = [
                {
                    "proposal_id": item.proposal_id,
                    "title": item.title,
                    "status": item.status,
                    "updated_at": item.updated_at,
                    "target_area": item.target_area,
                    "proposal_type": item.proposal_type,
                    "risk_level": item.risk_level,
                    "governance": {
                        "reason": str((item.governance or {}).get("reason", "")),
                        "source": str((item.governance or {}).get("source", "")),
                        "severity": str((item.governance or {}).get("severity", "")),
                    },
                }
                for item in self.list(limit=max(1, int(recent_limit or 10)))
            ]
            return {
                "total_proposals": len(self._proposals),
                "status_counts": counts,
                "recent_proposals": recent,
            }

    def reload_from_disk(self) -> None:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as error:
                raise ValueError(f"Invalid evolution registry data: {error}") from error
            if not isinstance(payload, dict):
                raise ValueError("Invalid evolution registry data: root payload must be an object.")
            raw = payload.get("proposals", {})
            if not isinstance(raw, dict):
                raise ValueError("Invalid evolution registry data: proposals must be a mapping.")
            self._proposals = {
                str(proposal_id): EvolutionProposalRecord.from_dict(item)
                for proposal_id, item in raw.items()
                if isinstance(item, dict)
            }

    def flush(self) -> None:
        with self._lock:
            payload = {"proposals": {proposal_id: item.as_dict() for proposal_id, item in self._proposals.items()}}
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)

    def _reload_if_available(self) -> None:
        if self.path.exists():
            self.reload_from_disk()
