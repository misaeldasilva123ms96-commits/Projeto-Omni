"""Strict offline validation for human approval inputs."""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from dataclasses import fields
from datetime import datetime, timezone
from urllib.parse import unquote

from brain.runtime.external.approval.models import (
    ApprovedOperation,
    ApprovedServer,
    HumanReviewChecklist,
)
from brain.runtime.external.schema_intake.analyzer import build_proposal_id
from brain.runtime.external.schema_intake.models import (
    DeclaredServer,
    OperationSummary,
    ProviderDesignProposal,
)

SUPPORTED_PROPOSAL_FORMAT = "provider-design-proposal-v2"
MAX_APPROVED_OPERATIONS = 20
SUPPORTED_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"})
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


class ApprovalError(ValueError):
    """Stable failure code for maintenance approval boundaries."""


def validate_proposal(proposal: ProviderDesignProposal) -> None:
    if proposal.proposal_format_version != SUPPORTED_PROPOSAL_FORMAT:
        raise ApprovalError("unsupported_proposal_format")
    if proposal.proposal_id != build_proposal_id(
        proposal.candidate_id,
        proposal.canonical_schema_sha256,
        proposal.proposal_format_version,
    ):
        raise ApprovalError("proposal_identity_invalid")
    required_true = (
        "maintainer_review_required",
        "terms_review_required",
        "security_review_required",
        "privacy_review_required",
        "cost_review_required",
        "rate_limit_review_required",
        "provider_docs_review_required",
    )
    required_false = (
        "execution_authorized",
        "registration_authorized",
        "code_generation_authorized",
        "credential_generation_authorized",
        "network_authority",
    )
    if (
        proposal.proposal_state != "manual_review_required"
        or any(getattr(proposal, name) is not True for name in required_true)
        or any(getattr(proposal, name) is not False for name in required_false)
    ):
        raise ApprovalError("proposal_authority_invalid")
    if proposal.operation_details_truncated:
        raise ApprovalError("proposal_operation_details_incomplete")


def normalize_reviewer(value: object) -> str:
    if not isinstance(value, str):
        raise ApprovalError("reviewer_identity_invalid")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not 2 <= len(normalized) <= 200 or any(
        unicodedata.category(character).startswith("C") for character in normalized
    ):
        raise ApprovalError("reviewer_identity_invalid")
    return normalized


def format_approved_at(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ApprovalError("approved_at_invalid")
    utc = value.astimezone(timezone.utc).replace(microsecond=0)
    return utc.isoformat().replace("+00:00", "Z")


def validate_checklist(checklist: HumanReviewChecklist) -> None:
    if not isinstance(checklist, HumanReviewChecklist) or not all(
        getattr(checklist, item.name) is True for item in fields(checklist)
    ):
        raise ApprovalError("human_review_incomplete")


def validate_blockers(
    proposal: ProviderDesignProposal, acknowledgements: tuple[str, ...]
) -> tuple[str, ...]:
    supplied = set(acknowledgements)
    expected = set(proposal.review_blockers)
    if supplied - expected:
        raise ApprovalError("unknown_review_blocker_acknowledgement")
    if supplied != expected:
        raise ApprovalError("human_review_incomplete")
    return tuple(sorted(supplied))


def operation_key(operation: OperationSummary) -> str:
    return f"{operation.method} {operation.path}"


def _validate_path(path: str) -> None:
    decoded = unquote(path)
    if (
        not isinstance(path, str)
        or not path.startswith("/")
        or len(path) > 1_000
        or any(character in decoded for character in ("?", "#", "\r", "\n", "\x00", "\\"))
        or any(segment in {".", ".."} for segment in decoded.split("/"))
    ):
        raise ApprovalError("operation_path_invalid")


def select_operations(
    proposal: ProviderDesignProposal,
    selected_keys: tuple[str, ...],
    mutating_acknowledgements: tuple[str, ...],
    security_acknowledgements: tuple[str, ...],
) -> tuple[tuple[ApprovedOperation, ...], tuple[str, ...], tuple[str, ...]]:
    if not selected_keys:
        raise ApprovalError("no_operations_selected")
    if len(selected_keys) > MAX_APPROVED_OPERATIONS:
        raise ApprovalError("too_many_operations_selected")
    if len(set(selected_keys)) != len(selected_keys):
        raise ApprovalError("duplicate_selected_operation")
    available = {operation_key(item): item for item in proposal.operations}
    selected: list[ApprovedOperation] = []
    required_mutating: set[str] = set()
    required_security: set[str] = set()
    for key in selected_keys:
        operation = available.get(key)
        if operation is None:
            raise ApprovalError("selected_operation_not_found")
        if operation.method not in SUPPORTED_METHODS:
            raise ApprovalError("operation_method_not_supported_for_scaffold")
        _validate_path(operation.path)
        if operation.security_mode == "invalid":
            raise ApprovalError("selected_operation_security_invalid")
        if operation.mutating_signal:
            required_mutating.add(key)
        if (
            operation.security_mode == "explicit_empty"
            or operation.anonymous_security_option_present
        ):
            required_security.add(key)
        selected.append(
            ApprovedOperation(
                key,
                operation.method,
                operation.path,
                operation.operation_id,
                operation.security_mode,
                operation.security_requirement_count,
                operation.anonymous_security_option_present,
                operation.mutating_signal,
            )
        )
    mutating = set(mutating_acknowledgements)
    security = set(security_acknowledgements)
    if mutating != required_mutating:
        raise ApprovalError("mutating_operation_not_acknowledged")
    if security != required_security:
        raise ApprovalError("operation_security_exception_not_acknowledged")
    return (
        tuple(sorted(selected, key=lambda item: item.operation_key)),
        tuple(sorted(mutating)),
        tuple(sorted(security)),
    )


def _validate_base_path(path: str) -> None:
    _validate_path(path)


def _validate_hostname(hostname: str) -> None:
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ApprovalError("ip_literal_server_not_supported")
    lowered = hostname.lower().rstrip(".")
    labels = lowered.split(".")
    if lowered == "localhost" or len(labels) < 2 or lowered.endswith(".local"):
        raise ApprovalError("provider_scaffold_server_unavailable")
    if len(lowered) > 253 or any(not _HOST_LABEL.fullmatch(label) for label in labels):
        raise ApprovalError("provider_scaffold_server_unavailable")


def _eligible_server(server: DeclaredServer) -> ApprovedServer:
    if server.templated:
        raise ApprovalError("templated_server_not_supported_for_scaffold")
    if server.scheme != "https":
        raise ApprovalError("insecure_server_not_supported_for_scaffold")
    if server.port not in (None, 443):
        raise ApprovalError("non_standard_server_port_not_supported")
    if not server.hostname:
        raise ApprovalError("provider_scaffold_server_unavailable")
    _validate_hostname(server.hostname)
    _validate_base_path(server.base_path)
    return ApprovedServer("https", server.hostname, server.port, server.base_path)


def select_server(proposal: ProviderDesignProposal, confirmed_host: str) -> ApprovedServer:
    if not proposal.declared_servers:
        raise ApprovalError("provider_scaffold_server_unavailable")
    eligible: list[ApprovedServer] = []
    first_error: ApprovalError | None = None
    for server in proposal.declared_servers:
        try:
            eligible.append(_eligible_server(server))
        except ApprovalError as exc:
            if first_error is None:
                first_error = exc
    if not eligible:
        raise first_error or ApprovalError("provider_scaffold_server_unavailable")
    if len(eligible) > 1:
        raise ApprovalError("provider_scaffold_server_ambiguous")
    if confirmed_host != eligible[0].hostname:
        raise ApprovalError("confirmed_server_mismatch")
    return eligible[0]
