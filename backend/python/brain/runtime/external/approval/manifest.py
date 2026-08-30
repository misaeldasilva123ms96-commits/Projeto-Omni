"""Create and verify narrowly scoped human approval manifests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from typing import Callable

from brain.runtime.external.approval.models import HumanApprovalManifest, HumanReviewChecklist
from brain.runtime.external.approval.validation import (
    ApprovalError,
    format_approved_at,
    normalize_reviewer,
    select_operations,
    select_server,
    validate_blockers,
    validate_checklist,
    validate_proposal,
)
from brain.runtime.external.schema_intake.models import ProviderDesignProposal

APPROVAL_MANIFEST_FORMAT_VERSION = "external-api-approval-manifest-v1"
APPROVAL_METHOD = "self_attested_maintenance_cli"


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def proposal_snapshot_sha256(proposal: ProviderDesignProposal) -> str:
    return hashlib.sha256(canonical_json_bytes(proposal.as_dict())).hexdigest()


def _approval_id(manifest: HumanApprovalManifest) -> str:
    payload = asdict(manifest)
    payload.pop("approval_id")
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def create_human_approval_manifest(
    proposal: ProviderDesignProposal,
    *,
    reviewed_by: str,
    confirm_server_host: str,
    selected_operations: tuple[str, ...],
    review_checklist: HumanReviewChecklist,
    acknowledged_review_blockers: tuple[str, ...] = (),
    acknowledged_mutating_operations: tuple[str, ...] = (),
    acknowledged_security_exceptions: tuple[str, ...] = (),
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> HumanApprovalManifest:
    validate_proposal(proposal)
    validate_checklist(review_checklist)
    reviewer = normalize_reviewer(reviewed_by)
    blockers = validate_blockers(proposal, acknowledged_review_blockers)
    server = select_server(proposal, confirm_server_host)
    operations, mutating, security = select_operations(
        proposal,
        selected_operations,
        acknowledged_mutating_operations,
        acknowledged_security_exceptions,
    )
    manifest = HumanApprovalManifest(
        "",
        APPROVAL_MANIFEST_FORMAT_VERSION,
        proposal.proposal_id,
        proposal.proposal_format_version,
        proposal.candidate_id,
        proposal.source_record_id,
        proposal.canonical_schema_sha256,
        proposal_snapshot_sha256(proposal),
        reviewer,
        format_approved_at(clock()),
        APPROVAL_METHOD,
        review_checklist,
        blockers,
        tuple(proposal.issues),
        server,
        operations,
        mutating,
        security,
    )
    return replace(manifest, approval_id=_approval_id(manifest))


def verify_approval_manifest(manifest: HumanApprovalManifest) -> None:
    invariants = {
        "approval_manifest_format_version": APPROVAL_MANIFEST_FORMAT_VERSION,
        "approval_method": APPROVAL_METHOD,
        "approval_state": "approved_for_non_executable_scaffold",
        "scaffold_generation_authorized": True,
        "execution_authorized": False,
        "registration_authorized": False,
        "network_authority": False,
        "tool_registration_authorized": False,
        "runtime_activation_authorized": False,
        "credential_creation_authorized": False,
        "executable_code_generation_authorized": False,
        "reviewer_identity_cryptographically_verified": False,
    }
    if any(getattr(manifest, name, None) != value for name, value in invariants.items()):
        raise ApprovalError("approval_manifest_integrity_error")
    try:
        normalized_reviewer = normalize_reviewer(manifest.reviewed_by)
        parsed = datetime.fromisoformat(manifest.approved_at.replace("Z", "+00:00"))
        normalized_time = format_approved_at(parsed)
        validate_checklist(manifest.review_checklist)
    except (ApprovalError, ValueError) as exc:
        raise ApprovalError("approval_manifest_integrity_error") from exc
    if (
        normalized_reviewer != manifest.reviewed_by
        or normalized_time != manifest.approved_at
        or manifest.acknowledged_review_blockers
        != tuple(sorted(set(manifest.acknowledged_review_blockers)))
        or manifest.proposal_issues != tuple(manifest.proposal_issues)
        or manifest.acknowledged_mutating_operations
        != tuple(sorted(set(manifest.acknowledged_mutating_operations)))
        or manifest.acknowledged_security_exceptions
        != tuple(sorted(set(manifest.acknowledged_security_exceptions)))
        or tuple(item.operation_key for item in manifest.approved_operations)
        != tuple(sorted({item.operation_key for item in manifest.approved_operations}))
        or manifest.approval_id != _approval_id(manifest)
    ):
        raise ApprovalError("approval_manifest_integrity_error")


def verify_approval_against_proposal(
    manifest: HumanApprovalManifest, proposal: ProviderDesignProposal
) -> None:
    verify_approval_manifest(manifest)
    validate_proposal(proposal)
    bindings = (
        (manifest.proposal_id, proposal.proposal_id),
        (manifest.proposal_format_version, proposal.proposal_format_version),
        (manifest.candidate_id, proposal.candidate_id),
        (manifest.canonical_schema_sha256, proposal.canonical_schema_sha256),
        (manifest.proposal_snapshot_sha256, proposal_snapshot_sha256(proposal)),
    )
    if any(left != right for left, right in bindings):
        raise ApprovalError("approval_stale")
    try:
        blockers = validate_blockers(proposal, manifest.acknowledged_review_blockers)
        server = select_server(proposal, manifest.approved_server.hostname)
        operations, mutating, security = select_operations(
            proposal,
            tuple(item.operation_key for item in manifest.approved_operations),
            manifest.acknowledged_mutating_operations,
            manifest.acknowledged_security_exceptions,
        )
    except ApprovalError as exc:
        raise ApprovalError("approval_manifest_integrity_error") from exc
    if (
        blockers != manifest.acknowledged_review_blockers
        or tuple(proposal.issues) != manifest.proposal_issues
        or server != manifest.approved_server
        or operations != manifest.approved_operations
        or mutating != manifest.acknowledged_mutating_operations
        or security != manifest.acknowledged_security_exceptions
    ):
        raise ApprovalError("approval_manifest_integrity_error")
