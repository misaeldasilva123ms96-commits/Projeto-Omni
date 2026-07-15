from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from brain.env import read_env, read_env_bool, read_env_float, read_env_int


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
    node_subprocess_timeout_seconds: int = 60
    node_circuit_breaker_enabled: bool = True
    node_circuit_failure_threshold: int = 3
    node_circuit_reset_seconds: int = 30
    jsonl_archive_retention_count: int = 5
    jsonl_archive_retention_days: int = 7
    supabase_url: str = ""
    supabase_service_role_key: str = ""


def python_service_mode() -> bool:
    mode = read_env("OMNI_PYTHON_MODE", "subprocess").lower()
    return mode == "service"


def load_config() -> OmniConfig:
    return OmniConfig(
        public_demo_mode=read_env_bool("OMNI_PUBLIC_DEMO_MODE"),
        runtime_mode=read_env("OMNI_RUNTIME_MODE", "live").lower(),
        allow_high_risk=read_env_bool("OMNI_ALLOW_HIGH_RISK", True),
        allow_critical=read_env_bool("OMNI_ALLOW_CRITICAL"),
        max_parallel_read_steps=read_env_int("OMNI_MAX_PARALLEL_READ_STEPS", 2),
        stale_checkpoint_minutes=read_env_int("OMNI_STALE_CHECKPOINT_MINUTES", 120),
        enable_critic=read_env_bool("OMNI_ENABLE_CRITIC", True),
        max_correction_depth=read_env_int("OMNI_MAX_CORRECTION_DEPTH", 1),
        evolution_interval_seconds=read_env_int("OMNI_EVOLUTION_INTERVAL_SECONDS", 300),
        evolution_min_sessions=read_env_int("OMNI_EVOLUTION_MIN_SESSIONS", 1),
        base_dir=read_env("OMNI_BASE_DIR"),
        python_base_dir=read_env("OMNI_PYTHON_BASE_DIR"),
        memory_json_path=read_env("OMNI_MEMORY_JSON_PATH"),
        memory_dir=read_env("OMNI_MEMORY_DIR"),
        transcripts_dir=read_env("OMNI_TRANSCRIPTS_DIR"),
        node_bin=read_env("OMNI_NODE_BIN", "node"),
        node_subprocess_timeout_seconds=max(
            1,
            min(read_env_int("OMNI_NODE_SUBPROCESS_TIMEOUT_SECONDS", 60), 300),
        ),
        node_circuit_breaker_enabled=read_env_bool("OMNI_NODE_CIRCUIT_BREAKER_ENABLED", True),
        node_circuit_failure_threshold=max(
            1,
            min(read_env_int("OMNI_NODE_CIRCUIT_FAILURE_THRESHOLD", 3), 20),
        ),
        node_circuit_reset_seconds=max(
            1,
            min(read_env_int("OMNI_NODE_CIRCUIT_RESET_SECONDS", 30), 3600),
        ),
        jsonl_archive_retention_count=min(
            read_env_int("OMNI_JSONL_ARCHIVE_RETENTION_COUNT", 5),
            100,
        ),
        jsonl_archive_retention_days=min(
            read_env_int("OMNI_JSONL_ARCHIVE_RETENTION_DAYS", 7),
            365,
        ),
        supabase_url=read_env("SUPABASE_URL"),
        supabase_service_role_key=read_env("SUPABASE_SERVICE_ROLE_KEY"),
    )
