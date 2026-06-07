from __future__ import annotations

from typing import Any

from brain.runtime.session_helpers import (
    extract_session_byok_bridge,
    session_id,
    SESSION_BYOK_PUBLIC_RESPONSE,
)
from brain.runtime.session_store import SessionStore
from brain.runtime.control.run_registry import RunRegistry
from brain.runtime.control.governance_controller import GovernanceResolutionController
from brain.runtime.orchestrator_services.session_service import SessionService
from brain.runtime.orchestrator_services.run_lifecycle_service import RunLifecycleService
from brain.runtime.orchestrator_services.governance_integration_service import GovernanceIntegrationService
from brain.runtime.checkpoint_store import CheckpointStore


class SessionManager:
    def __init__(self, paths: Any) -> None:
        self.paths = paths
        self._session_provider_preference: str | None = None
        self._session_provider_env_overlay: dict[str, str] = {}
        self._session_byok_active: bool = False
        self._session_byok_error_reason: str | None = None
        self._runtime_bridge: dict[str, Any] = {}
        self.session_store = SessionStore(paths.sessions_dir)
        self.checkpoint_store = CheckpointStore(paths.root)
        self._session_service = SessionService(self.checkpoint_store)

    def initialize_from_bridge(self, bridge: dict[str, Any] | None) -> None:
        self._runtime_bridge = dict(bridge) if isinstance(bridge, dict) else {}
        byok_state = extract_session_byok_bridge(self._runtime_bridge)
        self._session_byok_active = bool(byok_state.get("active"))
        self._session_provider_preference = (
            byok_state.get("provider") if isinstance(byok_state.get("provider"), str) else None
        )
        self._session_provider_env_overlay = (
            dict(byok_state.get("env_overlay")) if isinstance(byok_state.get("env_overlay"), dict) else {}
        )
        self._session_byok_error_reason = (
            str(byok_state.get("error_reason")) if byok_state.get("error_reason") else None
        )

    def has_byok_error(self) -> bool:
        return bool(self._session_byok_error_reason)

    def build_byok_error_response(self) -> dict[str, Any]:
        return {
            "response": SESSION_BYOK_PUBLIC_RESPONSE,
            "stop_reason": self._session_byok_error_reason,
            "error": {
                "failure_class": "BYOK_SESSION_INVALID",
                "message": "Session BYOK credentials are invalid or incomplete.",
                "reason": self._session_byok_error_reason,
            },
            "provider_failed": True,
            "failure_class": "BYOK_SESSION_INVALID",
        }

    def generate_session_id(self) -> str:
        return session_id()

    def save_session(self, session_id_val: str, payload: dict[str, object]) -> None:
        self.session_store.save(session_id_val, payload)

    def load_session(self, session_id_val: str) -> dict[str, object]:
        return self.session_store.load(session_id_val)

    def get_bridge(self) -> dict[str, Any]:
        return dict(self._runtime_bridge)

    def get_provider_preference(self) -> str | None:
        return self._session_provider_preference

    def get_provider_env_overlay(self) -> dict[str, str]:
        return dict(self._session_provider_env_overlay)

    def get_byok_active(self) -> bool:
        return self._session_byok_active

    def get_byok_error_reason(self) -> str | None:
        return self._session_byok_error_reason
