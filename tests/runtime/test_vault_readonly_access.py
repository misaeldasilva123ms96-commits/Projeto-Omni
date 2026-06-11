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
from brain.runtime.vault import (
    list_vault_notes as exported_list_vault_notes,
    read_vault_note as exported_read_vault_note,
    search_vault_notes as exported_search_vault_notes,
)


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


def _write_raw_note(vault_root: Path, relative_path: str, text: str) -> Path:
    path = vault_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
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
    assert result.to_dict()["path"] == "02_Architecture/approved.md"


def test_package_exports_read_only_helpers() -> None:
    assert exported_read_vault_note is read_vault_note
    assert exported_list_vault_notes is list_vault_notes
    assert exported_search_vault_notes is search_vault_notes


def test_reads_reviewed_markdown_note(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "04_Governance/reviewed.md", status="reviewed")

    result = read_vault_note("04_Governance/reviewed.md", vault_root=vault_root)

    assert result.allowed_for_context is True
    assert result.status == "reviewed"


def test_reads_created_fallback_updated_at_and_scalar_tags(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_raw_note(
        vault_root,
        "03_Runtime_Truth/created-fallback.md",
        """---
title: Created Fallback
type: runtime-truth
status: approved
owner: codex
created: 2026-06-09
updated_at: 2026-06-11
tags: runtime-truth
---

Evidence summary.
""",
    )

    result = read_vault_note("03_Runtime_Truth/created-fallback.md", vault_root=vault_root)

    assert result.allowed_for_context is True
    assert result.created_at == "2026-06-09"
    assert result.updated_at == "2026-06-11"
    assert result.tags == ["runtime-truth"]
    assert result.title == "Created Fallback"
    assert result.type == "runtime-truth"
    assert result.owner == "codex"


def test_status_casing_is_allowed_conservatively(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "status-case.md", status="APPROVED")

    result = read_vault_note("status-case.md", vault_root=vault_root)

    assert result.allowed_for_context is True
    assert result.status == "APPROVED"


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


def test_blocked_status_does_not_return_body_context(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "draft-context.md", status="draft", body="Draft context must stay hidden.")

    result = read_vault_note("draft-context.md", vault_root=vault_root)

    assert result.allowed_for_context is False
    assert result.body == ""
    assert result.blocked_reason == vault_reader.BLOCKED_STATUS_REASON


def test_blocks_missing_frontmatter(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    vault_root.mkdir()
    note = vault_root / "missing.md"
    note.write_text("# Missing frontmatter\n", encoding="utf-8")

    result = read_vault_note("missing.md", vault_root=vault_root)

    assert result.allowed_for_context is False
    assert result.blocked_reason == vault_reader.MISSING_FRONTMATTER_REASON


def test_blocks_missing_required_owner_and_type_fields(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_raw_note(
        vault_root,
        "missing-owner.md",
        """---
title: Missing Owner
type: architecture
status: approved
created_at: 2026-06-10
tags:
  - vault
---

Missing owner.
""",
    )
    _write_raw_note(
        vault_root,
        "missing-type.md",
        """---
title: Missing Type
status: approved
owner: omni
created_at: 2026-06-10
tags:
  - vault
---

Missing type.
""",
    )

    missing_owner = read_vault_note("missing-owner.md", vault_root=vault_root)
    missing_type = read_vault_note("missing-type.md", vault_root=vault_root)

    assert missing_owner.allowed_for_context is False
    assert missing_owner.body == ""
    assert "owner" in str(missing_owner.blocked_reason)
    assert missing_type.allowed_for_context is False
    assert missing_type.body == ""
    assert "type" in str(missing_type.blocked_reason)


def test_empty_body_note_returns_safely(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "empty.md", body="")

    result = read_vault_note("empty.md", vault_root=vault_root)

    assert result.allowed_for_context is True
    assert result.body == ""
    assert result.truncated is False


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


def test_absolute_path_inside_vault_is_readable(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    note = _write_note(vault_root, "02_Architecture/absolute.md", body="Absolute safe path.")

    result = read_vault_note(note.resolve(), vault_root=vault_root)

    assert result.allowed_for_context is True
    assert result.path == "02_Architecture/absolute.md"
    assert result.body == "Absolute safe path."


def test_missing_markdown_file_is_blocked(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    vault_root.mkdir()

    result = read_vault_note("missing.md", vault_root=vault_root)

    assert result.allowed_for_context is False
    assert result.blocked_reason == "Vault note does not exist."


def test_blocks_non_markdown_files(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    vault_root.mkdir()
    data_file = vault_root / "note.json"
    data_file.write_text("{}", encoding="utf-8")

    result = read_vault_note("note.json", vault_root=vault_root)

    assert result.allowed_for_context is False
    assert result.blocked_reason == vault_reader.EXTENSION_BLOCKED_REASON


def test_blocks_invalid_utf8_markdown(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    vault_root.mkdir()
    note = vault_root / "invalid.md"
    note.write_bytes(b"\xff\xfe\x00")

    result = read_vault_note("invalid.md", vault_root=vault_root)

    assert result.allowed_for_context is False
    assert result.blocked_reason == "Vault note is not valid UTF-8 Markdown."


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


def test_secret_like_frontmatter_is_blocked(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "frontmatter-secret.md", extra_frontmatter="source: TOKEN\n")

    result = read_vault_note("frontmatter-secret.md", vault_root=vault_root)

    assert result.allowed_for_context is False
    assert result.redacted is True
    assert result.body == ""
    assert result.frontmatter["source"] == "[REDACTED]"


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
    assert searched[1].blocked_reason == vault_reader.BLOCKED_STATUS_REASON


def test_search_query_not_found_or_empty_returns_empty_list(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "approved.md", title="Runtime Truth", body="sandbox evidence")

    assert search_vault_notes("not-present", vault_root=vault_root) == []
    assert search_vault_notes("", vault_root=vault_root) == []


def test_list_and_search_missing_vault_root_return_empty_lists(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "missing-vault"

    assert list_vault_notes(vault_root=vault_root) == []
    assert search_vault_notes("anything", vault_root=vault_root) == []


def test_nested_markdown_file_is_readable(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "02_Architecture/nested/deep.md", body="Deep vault note.")

    result = read_vault_note("02_Architecture/nested/deep.md", vault_root=vault_root)

    assert result.allowed_for_context is True
    assert result.path == "02_Architecture/nested/deep.md"
    assert result.body == "Deep vault note."


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


def test_negative_body_limit_returns_empty_truncated_body(vault_workspace: Path) -> None:
    vault_root = vault_workspace / "vault"
    _write_note(vault_root, "negative-limit.md", body="limit me")

    result = read_vault_note("negative-limit.md", vault_root=vault_root, max_body_chars=-1)

    assert result.body == ""
    assert result.truncated is True
