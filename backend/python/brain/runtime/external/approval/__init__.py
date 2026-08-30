"""Offline human approval and inert scaffold boundary."""

from brain.runtime.external.approval.manifest import (
    APPROVAL_MANIFEST_FORMAT_VERSION,
    create_human_approval_manifest,
    proposal_snapshot_sha256,
    verify_approval_against_proposal,
    verify_approval_manifest,
)
from brain.runtime.external.approval.models import (
    HumanApprovalManifest,
    HumanReviewChecklist,
    NonExecutableProviderScaffold,
)
from brain.runtime.external.approval.scaffold import (
    NON_EXECUTABLE_SCAFFOLD_FORMAT_VERSION,
    create_non_executable_scaffold,
    verify_scaffold,
    write_scaffold_artifacts,
)
from brain.runtime.external.approval.serialization import (
    load_json_file,
    load_manifest,
    load_proposal,
    load_scaffold,
    write_json,
)
from brain.runtime.external.approval.validation import ApprovalError, operation_key

__all__ = [
    "APPROVAL_MANIFEST_FORMAT_VERSION",
    "NON_EXECUTABLE_SCAFFOLD_FORMAT_VERSION",
    "ApprovalError",
    "HumanApprovalManifest",
    "HumanReviewChecklist",
    "NonExecutableProviderScaffold",
    "create_human_approval_manifest",
    "create_non_executable_scaffold",
    "load_json_file",
    "load_manifest",
    "load_proposal",
    "load_scaffold",
    "operation_key",
    "proposal_snapshot_sha256",
    "verify_approval_against_proposal",
    "verify_approval_manifest",
    "verify_scaffold",
    "write_json",
    "write_scaffold_artifacts",
]
