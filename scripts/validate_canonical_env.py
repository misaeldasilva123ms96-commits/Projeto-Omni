"""Enforce canonical-only Omni environment configuration."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OBSOLETE_PREFIX = "OMIN" + "I_"
OBSOLETE_NAME = re.compile(rf"\b{OBSOLETE_PREFIX}[A-Z0-9_]+\b")
DYNAMIC_PREFIX = re.compile(r"OMIN.{0,40}I_", re.DOTALL)
HISTORICAL_NOTICE = "Historical configuration note:"
HISTORICAL_PREFIXES = ("docs/audit/", "docs/reports/repository-archive/")
HISTORICAL_FILES = {"docs/security/audit-reconciliation-2026-07-02.md"}
NEGATIVE_TEST_FILES = {
    "backend/python/tests/runtime/test_canonical_env.py",
    "tests/config/test_encrypted_credential_store.py",
    "tests/runtime/js_runtime_launcher.test.mjs",
    "tests/runtime/omniCanonicalNaming.test.mjs",
    "tests/runtime/test_secrets_config_hardening.py",
}
TEXT_SUFFIXES = {
    ".example", ".js", ".json", ".md", ".mjs", ".py", ".rs", ".toml",
    ".ts", ".tsx", ".txt", ".yaml", ".yml",
}


def tracked_text_files() -> Iterable[tuple[str, Path]]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        path = ROOT / relative
        if path.is_file() and (path.name == ".env.example" or path.suffix.lower() in TEXT_SUFFIXES):
            yield relative, path


def is_historical(relative: str) -> bool:
    return relative in HISTORICAL_FILES or relative.startswith(HISTORICAL_PREFIXES)


def validate() -> tuple[dict[str, object], list[str]]:
    errors: list[str] = []
    historical_references: dict[str, int] = {}
    negative_test_references: dict[str, int] = {}
    canonical_names: set[str] = set()

    for relative, path in tracked_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        canonical_names.update(re.findall(r"\bOMNI_[A-Z0-9_]+\b", text))
        obsolete_names = OBSOLETE_NAME.findall(text)
        if obsolete_names:
            if is_historical(relative):
                historical_references[relative] = len(obsolete_names)
                if HISTORICAL_NOTICE not in text:
                    errors.append(f"{relative}: historical references lack the obsolete-runtime notice")
            elif relative in NEGATIVE_TEST_FILES:
                negative_test_references[relative] = len(obsolete_names)
            else:
                errors.append(f"{relative}: contains obsolete environment names")

        if relative == "scripts/validate_canonical_env.py" or is_historical(relative):
            continue
        if DYNAMIC_PREFIX.search(text):
            approved_rust_negative = (
                relative == "backend/rust/src/main.rs"
                and '["OMIN", "I_ALLOWED_ORIGINS"]' in text
            )
            if not approved_rust_negative and relative not in NEGATIVE_TEST_FILES:
                errors.append(f"{relative}: constructs the obsolete prefix dynamically")

    report: dict[str, object] = {
        "schema_version": 2,
        "policy": "runtime configuration accepts OMNI_* names exclusively",
        "canonical_name_count": len(canonical_names),
        "active_obsolete_references": 0 if not errors else sum(
            1 for error in errors if "obsolete environment" in error
        ),
        "negative_test_references": negative_test_references,
        "historical_reference_files": historical_references,
    }
    return report, sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail when canonical-only policy is violated")
    args = parser.parse_args()
    report, errors = validate()
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.check and errors:
        for error in errors:
            print(f"canonical environment policy error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
