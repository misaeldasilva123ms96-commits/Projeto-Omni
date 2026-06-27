from __future__ import annotations

import logging
from typing import Any

from .memory_facade import MemoryFacade
from .memory_models import (
    GovernanceEventRecord,
    ProviderAttemptRecord,
    RuntimeEventRecord,
    redact_payload,
)

logger = logging.getLogger(__name__)

_facade: MemoryFacade | None = None
_initialized = False


def _lazy_facade() -> MemoryFacade | None:
    global _facade, _initialized
    if not _initialized:
        _initialized = True
        try:
            _facade = MemoryFacade()
            _facade.initialize()
            if _facade.init_error:
                logger.warning("MemoryFacade init warning: %s", _facade.init_error)
        except Exception as exc:
            logger.warning("MemoryFacade init failed: %s", exc)
            _facade = None
    return _facade


def get_memory_facade() -> MemoryFacade | None:
    return _lazy_facade()


def record_runtime_event(
    *,
    event_type: str,
    source: str,
    session_id: str,
    run_id: str,
    summary: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    facade = _lazy_facade()
    if facade is None:
        return
    try:
        record = RuntimeEventRecord(
            event_type=event_type,
            source=source,
            session_id=session_id,
            run_id=run_id,
            summary=summary,
            metadata=redact_payload(metadata or {}),
        )
        facade.record_runtime_event(record)
    except Exception as exc:
        logger.debug("Runtime event record failed: %s", exc)


def record_provider_attempt(
    *,
    provider: str,
    model: str,
    session_id: str,
    run_id: str,
    status: str,
    duration_ms: int = 0,
    token_count: int = 0,
    error_type: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    facade = _lazy_facade()
    if facade is None:
        return
    try:
        record = ProviderAttemptRecord(
            provider=provider,
            model=model,
            session_id=session_id,
            run_id=run_id,
            status=status,
            duration_ms=duration_ms,
            token_count=token_count,
            error_type=error_type,
            metadata=redact_payload(metadata or {}),
        )
        facade.record_provider_attempt(record)
    except Exception as exc:
        logger.debug("Provider attempt record failed: %s", exc)


def record_governance_event(
    *,
    event_type: str,
    source: str,
    session_id: str,
    run_id: str,
    status: str,
    reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    facade = _lazy_facade()
    if facade is None:
        return
    try:
        record = GovernanceEventRecord(
            event_type=event_type,
            source=source,
            session_id=session_id,
            run_id=run_id,
            status=status,
            reason=reason,
            metadata=redact_payload(metadata or {}),
        )
        facade.record_governance_event(record)
    except Exception as exc:
        logger.debug("Governance event record failed: %s", exc)


def close() -> None:
    global _facade, _initialized
    if _facade is not None:
        try:
            _facade.close()
        except Exception as exc:
            logger.debug("MemoryFacade close error: %s", exc)
    _facade = None
    _initialized = False


def reset_for_testing() -> None:
    global _facade, _initialized
    close()
    _initialized = False
