"""Immutable, non-executable discovery control-plane contracts."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SourceProvenance:
    source: str
    source_endpoint: str
    fetched_at: str
    cached: bool
    catalog_revision: str | None = None


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    candidate_id: str
    source: str
    source_record_id: str
    name: str
    description: str = ""
    category: str | None = None
    provider: str | None = None
    service: str | None = None
    documentation_url: str | None = None
    auth_hint: str | None = None
    https_hint: str | None = None
    cors_hint: str | None = None
    schema_available: bool = False
    schema_locator: str | None = None
    preferred_version: str | None = None
    openapi_version: str | None = None
    source_added_at: str | None = None
    source_updated_at: str | None = None
    discovered_at: str = ""
    issues: tuple[str, ...] = field(default_factory=tuple)
    source_provenance: SourceProvenance | None = None
    trust: str = field(default="discovery_only", init=False)
    review_state: str = field(default="manual_review_required", init=False)
    execution_authorized: bool = field(default=False, init=False)
    registration_authorized: bool = field(default=False, init=False)
    network_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CandidateSearchResult:
    candidate: DiscoveryCandidate
    relevance_score: int


@dataclass(frozen=True, slots=True)
class CandidateReviewDossier:
    candidate: DiscoveryCandidate
    terms_review_required: bool = field(default=True, init=False)
    security_review_required: bool = field(default=True, init=False)
    privacy_review_required: bool = field(default=True, init=False)
    implementation_review_required: bool = field(default=True, init=False)
    manual_review_required: bool = field(default=True, init=False)
    execution_authorized: bool = field(default=False, init=False)
    registration_authorized: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def candidate_id(source: str, source_record_id: str) -> str:
    material = f"discovery-candidate-v1\x00{source}\x00{source_record_id}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()
