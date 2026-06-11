"""Types for read-only governed vault access."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class VaultReadResult:
    path: str
    title: str
    type: str
    status: str
    owner: str
    created_at: str
    updated_at: Optional[str]
    tags: list[str]
    body: str
    frontmatter: dict[str, Any]
    allowed_for_context: bool
    blocked_reason: Optional[str]
    redacted: bool
    evidence_version: str
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
