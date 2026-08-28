"""Secret-free provenance envelope for future external responses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True, slots=True)
class ExternalResponseProvenance:
    source_type: str
    provider: str
    api_id: str
    retrieved_at: datetime
    endpoint: str
    cached: bool
    freshness: str
    request_id: str
    attribution: str = ""

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["retrieved_at"] = self.retrieved_at.isoformat()
        parsed = urlsplit(self.endpoint)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("provenance endpoint must not contain credentials")
        payload["endpoint"] = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        return payload
