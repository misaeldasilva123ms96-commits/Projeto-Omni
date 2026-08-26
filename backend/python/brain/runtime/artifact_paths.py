"""Central resolver for runtime artifact storage roots.

Artifact stores write under ``<root>/.logs/...`` by default so production
behavior stays unchanged. When ``OMNI_LOG_ROOT`` is set (the test harnesses
set it to an isolated temp directory), artifacts are redirected there while
keeping per-root scoping: each distinct ``root`` maps to its own tagged
subdirectory, so tests that pass explicit workspace roots remain isolated
from each other exactly as they were with the default layout.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path


def artifact_logs_root(root: Path) -> Path:
    """Return the artifact root that replaces ``<root>/.logs``.

    Honors the canonical ``OMNI_LOG_ROOT`` override documented in
    ``.env.example`` and enforced by both test harnesses (root conftest and
    scripts/run_python_tests.mjs).
    """
    override = os.environ.get("OMNI_LOG_ROOT")
    if not override:
        return root / ".logs"
    resolved = str(Path(root).resolve())
    tag = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:12]
    return Path(override) / f"root-{tag}"
