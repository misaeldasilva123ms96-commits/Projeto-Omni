"""Inventory legacy OMINI environment aliases without reading environment values."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
ALIAS_PATTERN = re.compile(r"\bOMINI_[A-Z0-9_]+\b")
ACTIVE_ALIAS_ASSIGNMENT = re.compile(r"^\s*OMINI_[A-Z0-9_]+\s*=", re.MULTILINE)
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
}
TEXT_SUFFIXES = {
    ".example",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".rs",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
SOURCE_ROOTS = {"backend", "core", "features", "js-runner", "platform", "runtime", "scripts"}


def _tracked_text_files() -> Iterable[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative = Path(raw_path.decode("utf-8", errors="surrogateescape"))
        path = ROOT / relative
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.name == ".env.example" or path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def _category(relative: Path) -> str:
    parts = relative.parts
    if parts and parts[0] == "docs":
        return "documentation"
    if "tests" in parts or (parts and parts[0] == "tests"):
        return "tests"
    if parts and parts[0] in SOURCE_ROOTS:
        return "runtime_source"
    return "configuration"


def build_inventory() -> tuple[dict[str, object], list[str]]:
    references: dict[str, list[str]] = defaultdict(list)
    category_counts: Counter[str] = Counter()
    source_pairing_errors: list[str] = []
    env_example = ROOT / ".env.example"

    for path in _tracked_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(ROOT)
        aliases = sorted(set(ALIAS_PATTERN.findall(text)))
        if not aliases:
            continue
        category = _category(relative)
        category_counts[category] += len(aliases)
        for alias in aliases:
            references[alias].append(relative.as_posix())
            canonical = f"OMNI_{alias.removeprefix('OMINI_')}"
            if category == "runtime_source" and canonical not in text:
                source_pairing_errors.append(
                    f"{relative.as_posix()}: {alias} has no same-file {canonical} pair"
                )

    errors = sorted(set(source_pairing_errors))
    try:
        env_text = env_example.read_text(encoding="utf-8")
    except OSError:
        errors.append(".env.example is missing")
    else:
        if ACTIVE_ALIAS_ASSIGNMENT.search(env_text):
            errors.append(".env.example contains active OMINI_* assignments")

    aliases = [
        {
            "legacy": alias,
            "canonical": f"OMNI_{alias.removeprefix('OMINI_')}",
            "files": sorted(paths),
        }
        for alias, paths in sorted(references.items())
    ]
    inventory: dict[str, object] = {
        "schema_version": 1,
        "policy": "OMNI canonical; OMINI compatibility only",
        "unique_aliases": len(aliases),
        "file_references": sum(len(row["files"]) for row in aliases),
        "category_alias_references": dict(sorted(category_counts.items())),
        "aliases": aliases,
    }
    return inventory, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail on unsafe alias drift")
    args = parser.parse_args()
    inventory, errors = build_inventory()
    print(json.dumps(inventory, indent=2, sort_keys=True))
    if args.check and errors:
        for error in errors:
            print(f"env-alias policy error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
