from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from brain.providers.models import ProviderHealth, ProviderRequest, ProviderResponse


class BaseProviderAdapter(ABC):
    name: str
    provider_type: str

    @abstractmethod
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError

    def stream_generate(self, request: ProviderRequest) -> Iterator[str]:
        response = self.generate(request)
        yield response.content

    def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name=str(getattr(self, "name", "unknown")),
            healthy=True,
            detail="healthcheck not implemented",
        )
