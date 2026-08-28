"""Explicit, in-memory registry for maintainer-approved external APIs."""

from __future__ import annotations

from brain.runtime.external.models import ExternalAPIDefinition
from brain.runtime.external.policy import validate_api_definition


class ExternalAPIRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ExternalAPIDefinition] = {}

    def register(self, definition: ExternalAPIDefinition) -> None:
        if definition.api_id in self._definitions:
            raise ValueError(f"external API already registered: {definition.api_id}")
        validate_api_definition(definition)
        self._definitions[definition.api_id] = definition

    def get(self, api_id: str) -> ExternalAPIDefinition | None:
        return self._definitions.get(str(api_id or "").strip())

    def list(self) -> tuple[ExternalAPIDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def is_registered(self, api_id: str) -> bool:
        return self.get(api_id) is not None
