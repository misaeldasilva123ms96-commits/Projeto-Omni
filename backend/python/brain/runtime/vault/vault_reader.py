"""Safe read-only access for governed vault Markdown notes.

This module reads approved or reviewed Markdown notes from the local vault. It
does not write files, execute commands, call providers, use MCP, or build an
external index.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Optional

from .vault_types import VaultReadResult

TRUSTED_STATUSES = {"approved", "reviewed"}
BLOCKED_STATUS_REASON = "Vault note status is not approved or reviewed."
MISSING_FRONTMATTER_REASON = "Vault note is missing required frontmatter."
PATH_BLOCKED_REASON = "Requested path is outside the configured vault root."
EXTENSION_BLOCKED_REASON = "Only Markdown .md vault notes are readable."
SECRET_BLOCKED_REASON = "Vault note contains secret-like content and is blocked from context."
VAULT_EVIDENCE_VERSION = "1.0"

SECRET_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"OPENAI[_A-Z0-9]*", re.IGNORECASE),
    re.compile(r"SUPABASE[_A-Z0-9]*", re.IGNORECASE),
    re.compile(r"PRIVATE_KEY", re.IGNORECASE),
    re.compile(r"API_KEY", re.IGNORECASE),
    re.compile(r"SECRET", re.IGNORECASE),
    re.compile(r"TOKEN", re.IGNORECASE),
    re.compile(r"PASSWORD", re.IGNORECASE),
    re.compile(r"JWT", re.IGNORECASE),
    re.compile(r"\.env", re.IGNORECASE),
)


def read_vault_note(
    note_path: str | Path,
    *,
    vault_root: str | Path = "vault",
    max_body_chars: int = 12000,
) -> VaultReadResult:
    root = _resolve_vault_root(vault_root)
    resolved = _resolve_note_path(root, note_path)
    display_path = _display_path(root, resolved)

    if resolved is None:
        return _blocked_result(
            path=str(note_path),
            blocked_reason=PATH_BLOCKED_REASON,
        )
    if resolved.suffix.lower() != ".md":
        return _blocked_result(
            path=display_path,
            blocked_reason=EXTENSION_BLOCKED_REASON,
        )
    if not resolved.is_file():
        return _blocked_result(
            path=display_path,
            blocked_reason="Vault note does not exist.",
        )

    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return _blocked_result(
            path=display_path,
            blocked_reason="Vault note is not valid UTF-8 Markdown.",
        )

    parsed = _parse_markdown_note(text)
    if parsed is None:
        return _blocked_result(
            path=display_path,
            blocked_reason=MISSING_FRONTMATTER_REASON,
        )

    frontmatter, body = parsed
    status = str(frontmatter.get("status", "unknown")).strip().lower()
    missing = _missing_required_frontmatter(frontmatter)
    if missing:
        return _result_from_parts(
            path=display_path,
            frontmatter=frontmatter,
            body="",
            allowed_for_context=False,
            blocked_reason=f"{MISSING_FRONTMATTER_REASON} Missing: {', '.join(missing)}.",
            redacted=False,
            max_body_chars=max_body_chars,
        )

    redacted_body, body_redacted = _redact_text(body)
    redacted_frontmatter, frontmatter_redacted = _redact_frontmatter(frontmatter)
    redacted = body_redacted or frontmatter_redacted
    blocked_reason: Optional[str] = None
    allowed = status in TRUSTED_STATUSES

    if not allowed:
        blocked_reason = BLOCKED_STATUS_REASON
    if redacted:
        allowed = False
        blocked_reason = SECRET_BLOCKED_REASON

    return _result_from_parts(
        path=display_path,
        frontmatter=redacted_frontmatter,
        body=redacted_body if allowed else "",
        allowed_for_context=allowed,
        blocked_reason=blocked_reason,
        redacted=redacted,
        max_body_chars=max_body_chars,
    )


def list_vault_notes(
    *,
    vault_root: str | Path = "vault",
    include_blocked: bool = False,
    max_body_chars: int = 12000,
) -> list[VaultReadResult]:
    root = _resolve_vault_root(vault_root)
    results = [
        read_vault_note(path, vault_root=root, max_body_chars=max_body_chars)
        for path in sorted(root.rglob("*.md"))
        if _is_inside(root, path)
    ]
    if include_blocked:
        return results
    return [result for result in results if result.allowed_for_context]


def search_vault_notes(
    query: str,
    *,
    vault_root: str | Path = "vault",
    include_blocked: bool = False,
    max_body_chars: int = 12000,
) -> list[VaultReadResult]:
    normalized_query = str(query or "").casefold()
    if not normalized_query:
        return []
    candidates = list_vault_notes(
        vault_root=vault_root,
        include_blocked=include_blocked,
        max_body_chars=max_body_chars,
    )
    return [
        result
        for result in candidates
        if normalized_query in result.title.casefold()
        or normalized_query in result.body.casefold()
        or any(normalized_query in tag.casefold() for tag in result.tags)
    ]


def _resolve_vault_root(vault_root: str | Path) -> Path:
    return Path(vault_root).resolve()


def _resolve_note_path(root: Path, note_path: str | Path) -> Optional[Path]:
    candidate = Path(note_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not _is_inside(root, resolved):
        return None
    return resolved


def _is_inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _display_path(root: Path, resolved: Optional[Path]) -> str:
    if resolved is None:
        return ""
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _parse_markdown_note(text: str) -> Optional[tuple[dict[str, Any], str]]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return None
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return None
    frontmatter = _parse_frontmatter_lines(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :]).strip()
    return frontmatter, body


def _parse_frontmatter_lines(lines: Iterable[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: Optional[str] = None
    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") and current_key:
            current_value = data.setdefault(current_key, [])
            if isinstance(current_value, list):
                current_value.append(stripped[2:].strip())
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            parsed_value: Any = value.strip()
            if parsed_value == "":
                parsed_value = []
            data[current_key] = parsed_value
    return data


def _missing_required_frontmatter(frontmatter: dict[str, Any]) -> list[str]:
    missing = []
    for field in ("type", "status", "owner"):
        if not str(frontmatter.get(field, "")).strip():
            missing.append(field)
    if not str(frontmatter.get("created_at") or frontmatter.get("created") or "").strip():
        missing.append("created_at or created")
    return missing


def _result_from_parts(
    *,
    path: str,
    frontmatter: dict[str, Any],
    body: str,
    allowed_for_context: bool,
    blocked_reason: Optional[str],
    redacted: bool,
    max_body_chars: int,
) -> VaultReadResult:
    truncated_body, truncated = _truncate_body(body, max_body_chars)
    return VaultReadResult(
        path=path,
        title=str(frontmatter.get("title") or Path(path).stem),
        type=str(frontmatter.get("type", "unknown")),
        status=str(frontmatter.get("status", "unknown")),
        owner=str(frontmatter.get("owner", "unknown")),
        created_at=str(frontmatter.get("created_at") or frontmatter.get("created") or ""),
        updated_at=_optional_string(frontmatter.get("updated_at") or frontmatter.get("updated")),
        tags=_tags(frontmatter.get("tags")),
        body=truncated_body,
        frontmatter=frontmatter,
        allowed_for_context=allowed_for_context,
        blocked_reason=blocked_reason,
        redacted=redacted,
        evidence_version=VAULT_EVIDENCE_VERSION,
        truncated=truncated,
    )


def _blocked_result(path: str, blocked_reason: str) -> VaultReadResult:
    return VaultReadResult(
        path=path,
        title="",
        type="unknown",
        status="unknown",
        owner="unknown",
        created_at="",
        updated_at=None,
        tags=[],
        body="",
        frontmatter={},
        allowed_for_context=False,
        blocked_reason=blocked_reason,
        redacted=False,
        evidence_version=VAULT_EVIDENCE_VERSION,
        truncated=False,
    )


def _redact_frontmatter(frontmatter: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    redacted = False
    safe: dict[str, Any] = {}
    for key, value in frontmatter.items():
        if isinstance(value, list):
            redacted_items = []
            for item in value:
                redacted_item, item_changed = _redact_text(str(item))
                redacted_items.append(redacted_item)
                redacted = redacted or item_changed
            safe[key] = redacted_items
        else:
            redacted_value, value_changed = _redact_text(str(value))
            safe[key] = redacted_value
            redacted = redacted or value_changed
    return safe, redacted


def _redact_text(text: str) -> tuple[str, bool]:
    redacted = text
    changed = False
    for pattern in SECRET_PATTERNS:
        redacted, count = pattern.subn("[REDACTED]", redacted)
        changed = changed or count > 0
    return redacted, changed


def _truncate_body(body: str, max_body_chars: int) -> tuple[str, bool]:
    limit = max(0, int(max_body_chars))
    if len(body) <= limit:
        return body, False
    return body[:limit], True


def _optional_string(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _tags(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None or value == "":
        return []
    return [str(value)]
