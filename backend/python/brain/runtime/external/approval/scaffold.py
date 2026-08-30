"""Generate inert JSON/Markdown review scaffolds from verified approvals."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, replace
from pathlib import Path

from brain.runtime.external.approval.manifest import (
    canonical_json_bytes,
    verify_approval_against_proposal,
)
from brain.runtime.external.approval.models import (
    HumanApprovalManifest,
    NonExecutableProviderScaffold,
)
from brain.runtime.external.approval.serialization import atomic_write, write_json
from brain.runtime.external.approval.validation import ApprovalError
from brain.runtime.external.schema_intake.models import ProviderDesignProposal

NON_EXECUTABLE_SCAFFOLD_FORMAT_VERSION = "non-executable-provider-scaffold-v2"
_BASE_TODOS = (
    "review provider terms",
    "confirm official provider documentation",
    "confirm rate limits",
    "design credentials",
    "design safe input schema",
    "design response normalization",
    "design fallback",
    "define exact host allowlist",
    "define exact paths/methods",
    "define observability/redaction",
    "implement tests",
    "perform security review",
)


def build_scaffold_id(scaffold: NonExecutableProviderScaffold) -> str:
    payload = asdict(scaffold)
    payload.pop("scaffold_id")
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _todos(manifest: HumanApprovalManifest, proposal: ProviderDesignProposal) -> tuple[str, ...]:
    values = list(_BASE_TODOS)
    if proposal.security_schemes:
        values.append("credential implementation required")
    if any(item.mutating_signal for item in manifest.approved_operations):
        values.append("mutation policy review required before executable implementation")
    if any(
        item.security_mode in {"explicit_empty", "explicit_optional_anonymous"}
        or item.anonymous_security_option_present
        for item in manifest.approved_operations
    ):
        values.append("authentication semantics require implementation-time revalidation")
    if "external_refs_present" in proposal.review_blockers:
        values.append("external references remain unresolved and MUST NOT be fetched automatically")
    if proposal.callback_count or proposal.webhook_count:
        values.append("callbacks/webhooks excluded from scaffold execution scope")
    return tuple(values)


def _build_scaffold(
    manifest: HumanApprovalManifest, proposal: ProviderDesignProposal
) -> NonExecutableProviderScaffold:
    version = NON_EXECUTABLE_SCAFFOLD_FORMAT_VERSION
    scaffold = NonExecutableProviderScaffold(
        "",
        version,
        manifest.approval_id,
        manifest.proposal_id,
        manifest.proposal_format_version,
        manifest.candidate_id,
        manifest.canonical_schema_sha256,
        manifest.proposal_snapshot_sha256,
        manifest.approved_server,
        manifest.approved_operations,
        tuple(sorted({item.scheme_type for item in proposal.security_schemes})),
        tuple(proposal.risk_signals),
        tuple(proposal.review_blockers),
        _todos(manifest, proposal),
    )
    return replace(scaffold, scaffold_id=build_scaffold_id(scaffold))


def create_non_executable_scaffold(
    manifest: HumanApprovalManifest, proposal: ProviderDesignProposal
) -> NonExecutableProviderScaffold:
    verify_approval_against_proposal(manifest, proposal)
    return _build_scaffold(manifest, proposal)


def verify_scaffold(scaffold: NonExecutableProviderScaffold) -> None:
    invariants = {
        "scaffold_format_version": NON_EXECUTABLE_SCAFFOLD_FORMAT_VERSION,
        "scaffold_state": "inactive_review_artifact",
        "execution_authorized": False,
        "registration_authorized": False,
        "network_authority": False,
        "tool_registration_authorized": False,
        "runtime_activation_authorized": False,
        "credential_creation_authorized": False,
        "executable_code_generation_authorized": False,
    }
    if any(getattr(scaffold, name, None) != value for name, value in invariants.items()) or (
        scaffold.scaffold_id != build_scaffold_id(scaffold)
    ):
        raise ApprovalError("scaffold_integrity_error")


def verify_scaffold_against_approval_and_proposal(
    scaffold: NonExecutableProviderScaffold,
    manifest: HumanApprovalManifest,
    proposal: ProviderDesignProposal,
) -> None:
    verify_scaffold(scaffold)
    verify_approval_against_proposal(manifest, proposal)
    if scaffold != _build_scaffold(manifest, proposal):
        raise ApprovalError("scaffold_stale")


def write_scaffold_artifacts(
    output_dir: str | Path, scaffold: NonExecutableProviderScaffold
) -> tuple[Path, Path]:
    verify_scaffold(scaffold)
    destination = Path(output_dir)
    json_path = destination / "provider-scaffold.json"
    readme_path = destination / "README.md"
    write_json(json_path, scaffold.as_dict())
    readme = (
        "# NON-EXECUTABLE REVIEW SCAFFOLD\n\n"
        "This artifact does not authorize or implement network execution, provider registration, "
        "credentials, tools, or runtime activation.\n\n"
        f"Scaffold format: `{scaffold.scaffold_format_version}`\n\n"
        f"Scaffold ID: `{scaffold.scaffold_id}`\n"
    ).encode("utf-8")
    try:
        atomic_write(readme_path, readme)
    except BaseException:
        json_path.unlink(missing_ok=True)
        raise
    return json_path, readme_path
