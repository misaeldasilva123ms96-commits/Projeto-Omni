from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from typing import Any


LEGACY_ALIASES: dict[str, str] = {
    "OMNI_PUBLIC_DEMO_MODE": "OMINI_PUBLIC_DEMO_MODE",
    "OMNI_JS_RUNTIME_BIN": "OMINI_JS_RUNTIME_BIN",
    "OMNI_BRIDGE_CLIENT_SESSION_ID": "OMINI_BRIDGE_CLIENT_SESSION_ID",
    "OMNI_ALLOW_HIGH_RISK": "OMINI_ALLOW_HIGH_RISK",
    "OMNI_ALLOW_CRITICAL": "OMINI_ALLOW_CRITICAL",
    "OMNI_RUNTIME_MODE": "OMINI_RUNTIME_MODE",
    "OMNI_BASE_DIR": "BASE_DIR",
    "OMNI_PYTHON_BASE_DIR": "PYTHON_BASE_DIR",
    "OMNI_PYTHON_MODE": "OMINI_PYTHON_MODE",
}


def read_env(name: str, default: str = "") -> str:
    canonical = LEGACY_ALIASES.get(name, name)
    value = os.getenv(name) or os.getenv(canonical) or default
    if os.getenv(name) and name != canonical:
        warnings.warn(f"Use {canonical} instead of {name}", DeprecationWarning, stacklevel=2)
    return str(value).strip()


def read_env_bool(name: str, default: bool = False) -> bool:
    val = read_env(name, "true" if default else "false").lower()
    return val in ("1", "true", "yes", "on")


def read_env_int(name: str, default: int = 0) -> int:
    val = read_env(name, str(default))
    try:
        return max(0, int(val))
    except (ValueError, TypeError):
        return default


def read_env_float(name: str, default: float = 0.0) -> float:
    val = read_env(name, str(default))
    try:
        return max(0.0, float(val))
    except (ValueError, TypeError):
        return default


@dataclass
class OmniConfig:
    public_demo_mode: bool = False
    runtime_mode: str = "live"
    allow_high_risk: bool = True
    allow_critical: bool = False
    max_parallel_read_steps: int = 2
    stale_checkpoint_minutes: int = 120
    enable_critic: bool = True
    max_correction_depth: int = 1
    evolution_interval_seconds: int = 300
    evolution_min_sessions: int = 1
    base_dir: str = ""
    python_base_dir: str = ""
    memory_json_path: str = ""
    memory_dir: str = ""
    transcripts_dir: str = ""
    node_bin: str = "node"
    supabase_url: str = ""
    supabase_service_role_key: str = ""


def python_service_mode() -> bool:
    mode = str(os.getenv("OMINI_PYTHON_MODE") or os.getenv("OMNI_PYTHON_MODE", "subprocess")).strip().lower()
    return mode == "service"


def load_config() -> OmniConfig:
    return OmniConfig(
        public_demo_mode=(
            read_env_bool("OMNI_PUBLIC_DEMO_MODE")
            or read_env_bool("OMINI_PUBLIC_DEMO_MODE")
        ),
        runtime_mode=read_env("OMNI_RUNTIME_MODE", "live").lower(),
        allow_high_risk=read_env_bool("OMINI_ALLOW_HIGH_RISK", True),
        allow_critical=read_env_bool("OMINI_ALLOW_CRITICAL"),
        max_parallel_read_steps=read_env_int("OMINI_MAX_PARALLEL_READ_STEPS", 2),
        stale_checkpoint_minutes=read_env_int("OMINI_STALE_CHECKPOINT_MINUTES", 120),
        enable_critic=read_env_bool("OMINI_ENABLE_CRITIC", True),
        max_correction_depth=read_env_int("OMINI_MAX_CORRECTION_DEPTH", 1),
        evolution_interval_seconds=read_env_int("OMINI_EVOLUTION_INTERVAL_SECONDS", 300),
        evolution_min_sessions=read_env_int("OMINI_EVOLUTION_MIN_SESSIONS", 1),
        base_dir=read_env("BASE_DIR"),
        python_base_dir=read_env("PYTHON_BASE_DIR"),
        memory_json_path=read_env("MEMORY_JSON_PATH"),
        memory_dir=read_env("MEMORY_DIR"),
        transcripts_dir=read_env("TRANSCRIPTS_DIR"),
        node_bin=read_env("NODE_BIN", "node"),
        supabase_url=read_env("SUPABASE_URL"),
        supabase_service_role_key=read_env("SUPABASE_SERVICE_ROLE_KEY"),
    )
