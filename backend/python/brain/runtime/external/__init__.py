"""Governed foundation for future outbound external API access.

Phase 1 intentionally provides no transport and registers no providers.
"""

from brain.runtime.external.config import external_api_enabled
from brain.runtime.external.models import ExternalAPIDefinition
from brain.runtime.external.policy import ExternalAPIPolicy
from brain.runtime.external.registry import ExternalAPIRegistry

__all__ = ["ExternalAPIDefinition", "ExternalAPIPolicy", "ExternalAPIRegistry", "external_api_enabled"]
