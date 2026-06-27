from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .jsonl_audit_mirror import JSONLAuditMirror
from .memory_models import (
    MEMORY_BACKEND_JSONL,
    MEMORY_BACKEND_SQLITE,
    SAFE_DEFAULT_BACKEND,
    AutonomySessionStateRecord,
    ConversationRecord,
    EpisodeRecord,
    GovernanceEventRecord,
    LearningArtifactRecord,
    MessageRecord,
    ProviderAttemptRecord,
    RuntimeEventRecord,
    SemanticFactRecord,
    redact_payload,
)
from .sqlite_adapter import SQLiteAdapter


class MemoryFacade:
    def __init__(
        self,
        *,
        backend: str | None = None,
        sqlite_path: str | Path | None = None,
        jsonl_path: str | Path | None = None,
        enable_sqlite: bool | None = None,
    ) -> None:
        self._backend = (backend or os.environ.get("OMINI_MEMORY_BACKEND") or SAFE_DEFAULT_BACKEND).lower()
        self._sqlite_enabled = self._resolve_sqlite_enabled(enable_sqlite)
        self._sqlite_path = self._resolve_path(
            sqlite_path, "OMINI_SQLITE_MEMORY_PATH", ".omni/memory/omni-memory.sqlite"
        )
        self._jsonl_path = self._resolve_path(
            jsonl_path, "OMINI_JSONL_MEMORY_PATH", ".omni/memory/omni-audit.jsonl"
        )
        self._sqlite: SQLiteAdapter | None = None
        self._jsonl: JSONLAuditMirror | None = None
        self._initialized = False
        self._init_error: str | None = None

    def _resolve_sqlite_enabled(self, override: bool | None) -> bool:
        if override is not None:
            return override
        env = os.environ.get("OMINI_ENABLE_SQLITE_MEMORY", "false").strip().lower()
        return env in ("1", "true", "yes")

    @staticmethod
    def _resolve_path(override: str | Path | None, env_var: str, default: str) -> Path:
        if override is not None:
            return Path(override)
        env = os.environ.get(env_var, "").strip()
        if env:
            return Path(env)
        return Path(default)

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def sqlite_enabled(self) -> bool:
        return self._sqlite_enabled

    @property
    def sqlite_path(self) -> Path:
        return self._sqlite_path

    @property
    def jsonl_path(self) -> Path:
        return self._jsonl_path

    @property
    def init_error(self) -> str | None:
        return self._init_error

    @property
    def is_sqlite_connected(self) -> bool:
        return self._sqlite is not None and self._sqlite.is_connected

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        if self._backend == MEMORY_BACKEND_SQLITE and not self._sqlite_enabled:
            self._init_error = (
                "SQLite backend requested but SQLite is not enabled. "
                "Set OMINI_ENABLE_SQLITE_MEMORY=true or pass enable_sqlite=True."
            )
            return

        self._jsonl = JSONLAuditMirror(self._jsonl_path)

        if self._sqlite_enabled:
            try:
                self._sqlite = SQLiteAdapter(self._sqlite_path)
                self._sqlite.connect()
            except Exception as exc:
                self._sqlite = None
                sanitized = str(exc).replace(self._sqlite_path.as_posix(), "<db-path>")
                self._init_error = f"SQLite init failed: {sanitized}"

    def record_conversation(self, record: ConversationRecord) -> None:
        self._ensure_initialized()
        if self._sqlite is not None:
            try:
                self._sqlite.insert_conversation(record)
            except Exception:
                pass
        if self._jsonl is not None:
            self._jsonl.append("conversation", record.as_dict())

    def record_message(self, record: MessageRecord) -> None:
        self._ensure_initialized()
        safe = MessageRecord(
            message_id=record.message_id,
            conversation_id=record.conversation_id,
            role=record.role,
            content=record.content[:500] if record.content else "",
            created_at=record.created_at,
            token_count=record.token_count,
            metadata=record.metadata,
        )
        if self._sqlite is not None:
            try:
                self._sqlite.insert_message(safe)
            except Exception:
                pass
        if self._jsonl is not None:
            self._jsonl.append("message", safe.as_dict())

    def record_episode(self, record: EpisodeRecord) -> None:
        self._ensure_initialized()
        if self._sqlite is not None:
            try:
                self._sqlite.insert_episode(record)
            except Exception:
                pass
        if self._jsonl is not None:
            self._jsonl.append("episode", record.as_dict())

    def record_semantic_fact(self, record: SemanticFactRecord) -> None:
        self._ensure_initialized()
        if self._sqlite is not None:
            try:
                self._sqlite.insert_semantic_fact(record)
            except Exception:
                pass
        if self._jsonl is not None:
            self._jsonl.append("semantic_fact", record.as_dict())

    def record_runtime_event(self, record: RuntimeEventRecord) -> None:
        self._ensure_initialized()
        if self._sqlite is not None:
            try:
                self._sqlite.insert_runtime_event(record)
            except Exception:
                pass
        if self._jsonl is not None:
            self._jsonl.append("runtime_event", record.as_dict())

    def record_provider_attempt(self, record: ProviderAttemptRecord) -> None:
        self._ensure_initialized()
        safe = ProviderAttemptRecord(
            attempt_id=record.attempt_id,
            provider=record.provider,
            model=record.model,
            session_id=record.session_id,
            run_id=record.run_id,
            status=record.status,
            duration_ms=record.duration_ms,
            token_count=record.token_count,
            error_type=record.error_type,
            created_at=record.created_at,
            metadata={k: v for k, v in record.metadata.items()
                      if not _is_sensitive_key(k)},
        )
        if self._sqlite is not None:
            try:
                self._sqlite.insert_provider_attempt(safe)
            except Exception:
                pass
        if self._jsonl is not None:
            self._jsonl.append("provider_attempt", safe.as_dict())

    def record_governance_event(self, record: GovernanceEventRecord) -> None:
        self._ensure_initialized()
        if self._sqlite is not None:
            try:
                self._sqlite.insert_governance_event(record)
            except Exception:
                pass
        if self._jsonl is not None:
            self._jsonl.append("governance_event", record.as_dict())

    def record_learning_artifact(self, record: LearningArtifactRecord) -> None:
        self._ensure_initialized()
        if self._sqlite is not None:
            try:
                self._sqlite.insert_learning_artifact(record)
            except Exception:
                pass
        if self._jsonl is not None:
            self._jsonl.append("learning_artifact", record.as_dict())

    def record_autonomy_session_state(self, record: AutonomySessionStateRecord) -> None:
        self._ensure_initialized()
        safe = AutonomySessionStateRecord.from_dict(record.as_dict())
        if safe is None or self._sqlite is None:
            return
        try:
            self._sqlite.upsert_autonomy_session_state(safe)
        except Exception:
            pass

    def get_autonomy_session_state(self, session_id: str) -> AutonomySessionStateRecord | None:
        self._ensure_initialized()
        if self._sqlite is None:
            return None
        safe_session_id = AutonomySessionStateRecord.from_dict({"session_id": session_id})
        if safe_session_id is None:
            return None
        try:
            return self._sqlite.get_autonomy_session_state(safe_session_id.session_id)
        except Exception:
            return None

    def list_autonomy_session_states(self, limit: int = 50) -> list[AutonomySessionStateRecord]:
        self._ensure_initialized()
        if self._sqlite is None:
            return []
        try:
            return self._sqlite.list_autonomy_session_states(limit)
        except Exception:
            return []

    def cleanup_expired_autonomy_session_states(self, now: str | None = None) -> int:
        self._ensure_initialized()
        if self._sqlite is None:
            return 0
        try:
            return self._sqlite.cleanup_expired_autonomy_session_states(now or "")
        except Exception:
            return 0

    def query_runtime_events(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        self._ensure_initialized()
        if self._sqlite is not None:
            try:
                return self._sqlite.query_runtime_events(session_id, limit)
            except Exception:
                pass
        return []

    def query_provider_attempts(self, provider: str, limit: int = 50) -> list[dict[str, Any]]:
        self._ensure_initialized()
        if self._sqlite is not None:
            try:
                return self._sqlite.query_provider_attempts(provider, limit)
            except Exception:
                pass
        return []

    def audit_records(self, limit: int = 0) -> list[dict[str, Any]]:
        if self._jsonl is not None:
            return self._jsonl.read_all(limit)
        return []

    def close(self) -> None:
        if self._sqlite is not None:
            try:
                self._sqlite.close()
            except Exception:
                pass
            self._sqlite = None
        self._jsonl = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


_SENSITIVE_META_KEYS = frozenset({
    "api_key", "api_key_used", "credential", "token", "secret",
    "auth", "authorization", "raw_key",
})


def _is_sensitive_key(key: str) -> bool:
    return key.lower() in _SENSITIVE_META_KEYS
