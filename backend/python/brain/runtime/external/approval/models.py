"""Frozen contracts for human-reviewed, non-executable external API design artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class HumanReviewChecklist:
    terms_approved: bool = False
    security_approved: bool = False
    privacy_approved: bool = False
    cost_approved: bool = False
    rate_limit_approved: bool = False
    provider_documentation_approved: bool = False
    implementation_scope_approved: bool = False


@dataclass(frozen=True, slots=True)
class ApprovedServer:
    scheme: str
    hostname: str
    port: int | None
    base_path: str
    source: str = field(default="proposal_declared_server", init=False)


@dataclass(frozen=True, slots=True)
class ApprovedOperation:
    operation_key: str
    method: str
    path: str
    operation_id: str | None
    security_mode: str
    security_requirement_count: int
    anonymous_security_option_present: bool
    mutating_signal: bool


@dataclass(frozen=True, slots=True)
class HumanApprovalManifest:
    approval_id: str
    approval_manifest_format_version: str
    proposal_id: str
    proposal_format_version: str
    candidate_id: str
    source_record_id: str
    canonical_schema_sha256: str
    proposal_snapshot_sha256: str
    reviewed_by: str
    approved_at: str
    approval_method: str
    review_checklist: HumanReviewChecklist
    acknowledged_review_blockers: tuple[str, ...]
    proposal_issues: tuple[str, ...]
    approved_server: ApprovedServer
    approved_operations: tuple[ApprovedOperation, ...]
    acknowledged_mutating_operations: tuple[str, ...]
    acknowledged_security_exceptions: tuple[str, ...]
    approval_state: str = field(default="approved_for_non_executable_scaffold", init=False)
    scaffold_generation_authorized: bool = field(default=True, init=False)
    execution_authorized: bool = field(default=False, init=False)
    registration_authorized: bool = field(default=False, init=False)
    network_authority: bool = field(default=False, init=False)
    tool_registration_authorized: bool = field(default=False, init=False)
    runtime_activation_authorized: bool = field(default=False, init=False)
    credential_creation_authorized: bool = field(default=False, init=False)
    executable_code_generation_authorized: bool = field(default=False, init=False)
    reviewer_identity_cryptographically_verified: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NonExecutableProviderScaffold:
    scaffold_id: str
    scaffold_format_version: str
    approval_id: str
    proposal_id: str
    proposal_format_version: str
    candidate_id: str
    canonical_schema_sha256: str
    proposal_snapshot_sha256: str
    server: ApprovedServer
    operations: tuple[ApprovedOperation, ...]
    declared_security_scheme_types: tuple[str, ...]
    risk_signals: tuple[str, ...]
    review_blockers: tuple[str, ...]
    implementation_todos: tuple[str, ...]
    scaffold_state: str = field(default="inactive_review_artifact", init=False)
    execution_authorized: bool = field(default=False, init=False)
    registration_authorized: bool = field(default=False, init=False)
    network_authority: bool = field(default=False, init=False)
    tool_registration_authorized: bool = field(default=False, init=False)
    runtime_activation_authorized: bool = field(default=False, init=False)
    credential_creation_authorized: bool = field(default=False, init=False)
    executable_code_generation_authorized: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
