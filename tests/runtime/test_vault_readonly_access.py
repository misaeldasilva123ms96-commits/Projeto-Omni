from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.vault.vault_reader import (
    list_vault_notes,
    read_vault_note,
    search_vault_notes,
)
from brain.runtime.vault import vault_reader


@pytest.fixture()
def vault_workspace() -> Path:
    base = PROJECT_ROOT / ".pytest-local"
    base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vault-readonly-", dir=base) as temp_dir:
        yield Path(temp_dir)


def _write_note(
    vault_root: Path,
    relative_path: str,
    *,
    title: str = "Readable Note",
    status: str = "approved",
    body: str = "Reviewed architecture note.",
    extra_frontmatter: str = "",
) -> Path:
    path = vault_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = f"""---
title: {title}
type: architecture
status: {status}
owner: omni
created_at: 2026-06-10
tags:
  - vault
  - sandbox
{extra_frontmatter}---
"""
    path.write_text(f"{frontmatter}\n{body}\n", encoding="utf-8")
    return path


def test_reads_approved_markdown_note(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "02_Architecture/approved.md", body="Safe approved content.")

    result = read_vault_note("02_Architecture/approved.md", vault_root=vault_root)

    assert result.allowed_for_context is True
    assert result.blocked_reason is None
    assert result.path == "02_Architecture/approved.md"
    assert result.status == "approved"
    assert result.type == "architecture"
    assert result.owner == "omni"
    assert result.created_at == "2026-06-10"
    assert result.tags == ["vault", "sandbox"]
    assert result.body == "Safe approved content."
    assert result.evidence_version == "1.0"


def test_reads_reviewed_markdown_note(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "04_Governance/reviewed.md", status="reviewed")

    result = read_vault_note("04_Governance/reviewed.md", vault_root=vault_root)

    assert result.allowed_for_context is True
    assert result.status == "reviewed"


def test_blocks_draft_and_deprecated_notes_by_default(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "draft.md", status="draft")
    _write_note(vault_root, "deprecated.md", status="deprecated")

    draft = read_vault_note("draft.md", vault_root=vault_root)
    deprecated = read_vault_note("deprecated.md", vault_root=vault_root)

    assert draft.allowed_for_context is False
    assert deprecated.allowed_for_context is False
    assert draft.blocked_reason == vault_reader.BLOCKED_STATUS_REASON
    assert deprecated.blocked_reason == vault_reader.BLOCKED_STATUS_REASON


def test_blocks_missing_frontmatter(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    vault_root.mkdir()
    note = vault_root / "missing.md"
    note.write_text("# Missing frontmatter\n", encoding="utf-8")

    result = read_vault_note("missing.md", vault_root=vault_root)

    assert result.allowed_for_context is False
    assert result.blocked_reason == vault_reader.MISSING_FRONTMATTER_REASON


def test_blocks_path_traversal_and_outside_absolute_paths(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    vault_root.mkdir()
    outside = vault_workspace / "outside.md"
    outside.write_text("outside", encoding="utf-8")

    traversal = read_vault_note("../outside.md", vault_root=vault_root)
    absolute = read_vault_note(outside, vault_root=vault_root)

    assert traversal.allowed_for_context is False
    assert absolute.allowed_for_context is False
    assert traversal.blocked_reason == vault_reader.PATH_BLOCKED_REASON
    assert absolute.blocked_reason == vault_reader.PATH_BLOCKED_REASON


def test_blocks_non_markdown_files(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    vault_root.mkdir()
    data_file = vault_root / "note.json"
    data_file.write_text("{}", encoding="utf-8")

    result = read_vault_note("note.json", vault_root=vault_root)

    assert result.allowed_for_context is False
    assert result.blocked_reason == vault_reader.EXTENSION_BLOCKED_REASON


def test_blocks_and_redacts_secret_like_content(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(
        vault_root,
        "secret.md",
        body="This note references OPENAI_API_KEY and must not enter context.",
    )

    result = read_vault_note("secret.md", vault_root=vault_root)

    assert result.allowed_for_context is False
    assert result.redacted is True
    assert result.blocked_reason == vault_reader.SECRET_BLOCKED_REASON
    assert "OPENAI_API_KEY" not in result.body
    assert result.body == ""


def test_list_and_search_return_allowed_notes_only_by_default(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "approved.md", title="Runtime Truth", body="sandbox evidence")
    _write_note(vault_root, "draft.md", title="Runtime Truth Draft", status="draft", body="sandbox evidence")

    listed = list_vault_notes(vault_root=vault_root)
    searched = search_vault_notes("runtime", vault_root=vault_root)

    assert [result.path for result in listed] == ["approved.md"]
    assert [result.path for result in searched] == ["approved.md"]


def test_list_and_search_can_include_blocked_notes_for_review(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "approved.md", title="Runtime Truth")
    _write_note(vault_root, "draft.md", title="Runtime Truth Draft", status="draft")

    listed = list_vault_notes(vault_root=vault_root, include_blocked=True)
    searched = search_vault_notes("runtime", vault_root=vault_root, include_blocked=True)

    assert [result.path for result in listed] == ["approved.md", "draft.md"]
    assert [result.path for result in searched] == ["approved.md", "draft.md"]


def test_truncates_large_body_without_writing_files(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "large.md", body="x" * 50)
    before = sorted(path.relative_to(vault_root).as_posix() for path in vault_root.rglob("*"))

    result = read_vault_note("large.md", vault_root=vault_root, max_body_chars=12)
    list_vault_notes(vault_root=vault_root)
    search_vault_notes("x", vault_root=vault_root)
    after = sorted(path.relative_to(vault_root).as_posix() for path in vault_root.rglob("*"))

    assert result.body == "x" * 12
    assert result.truncated is True
    assert after == before
