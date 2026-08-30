"""Single governed HTTP authority for outbound external API traffic."""

from __future__ import annotations

import http.client
import hashlib
import ipaddress
import json
import socket
import ssl
import threading
import time
import uuid
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Mapping, Protocol
from urllib.parse import urlencode, urlsplit, urlunsplit

from brain.runtime.external.config import external_api_enabled
from brain.runtime.external.credentials import CredentialResolver, EnvironmentCredentialResolver
from brain.runtime.external.models import ExternalAPIRequest, ExternalAPIResponse, RedirectPolicy
from brain.runtime.external.policy import ExternalAPIPolicy
from brain.runtime.external.provenance import ExternalResponseProvenance

EventSink = Callable[[str, dict[str, object]], None]
Clock = Callable[[], float]


class ExternalGatewayError(RuntimeError):
    def __init__(
        self, code: str, *, retryable: bool = False, status_code: int | None = None
    ) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class TransportResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes
    connected_ip: str


class Resolver(Protocol):
    def resolve(self, host: str, port: int) -> tuple[str, ...]: ...


class Transport(Protocol):
    def request(
        self,
        *,
        logical_host: str,
        pinned_ip: str,
        port: int,
        method: str,
        target: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
        max_response_bytes: int,
        body: bytes = b"",
    ) -> TransportResponse: ...


class SystemResolver:
    def resolve(self, host: str, port: int) -> tuple[str, ...]:
        try:
            records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ExternalGatewayError("dns_resolution_failed") from exc
        addresses = tuple(dict.fromkeys(str(record[4][0]) for record in records if record[4]))
        if not addresses:
            raise ExternalGatewayError("dns_no_usable_address")
        return addresses


def validate_resolved_addresses(addresses: tuple[str, ...]) -> tuple[str, ...]:
    if not addresses:
        raise ExternalGatewayError("dns_no_usable_address")
    validated: list[str] = []
    for raw in addresses:
        try:
            address = ipaddress.ip_address(raw)
        except ValueError as exc:
            raise ExternalGatewayError("dns_invalid_address") from exc
        if not address.is_global:
            raise ExternalGatewayError("dns_non_public_address")
        validated.append(str(address))
    return tuple(validated)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        *,
        logical_host: str,
        pinned_ip: str,
        port: int,
        timeout: float,
        context: ssl.SSLContext,
    ) -> None:
        super().__init__(logical_host, port=port, timeout=timeout, context=context)
        self._logical_host = logical_host
        self._pinned_ip = pinned_ip

    def connect(self) -> None:
        raw_socket = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw_socket, server_hostname=self._logical_host)
        except BaseException:
            raw_socket.close()
            raise


def _read_limited(response: http.client.HTTPResponse, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(65_536, limit - total + 1))
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > limit:
            raise ExternalGatewayError("response_too_large")
        chunks.append(chunk)


class PinnedHTTPSTransport:
    """Connects to a validated IP while authenticating the original DNS host."""

    def __init__(
        self, *, context_factory: Callable[[], ssl.SSLContext] = ssl.create_default_context
    ) -> None:
        self._context_factory = context_factory

    def request(
        self,
        *,
        logical_host: str,
        pinned_ip: str,
        port: int,
        method: str,
        target: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
        max_response_bytes: int,
        body: bytes = b"",
    ) -> TransportResponse:
        context = self._context_factory()
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            raise ExternalGatewayError("tls_verification_required")
        connection = _PinnedHTTPSConnection(
            logical_host=logical_host,
            pinned_ip=pinned_ip,
            port=port,
            timeout=timeout_seconds,
            context=context,
        )
        try:
            connection.putrequest(method, target, skip_host=True, skip_accept_encoding=True)
            connection.putheader("Host", logical_host if port == 443 else f"{logical_host}:{port}")
            for name, value in headers.items():
                connection.putheader(name, value)
            connection.endheaders(body or None)
            response = connection.getresponse()
            body = _read_limited(response, max_response_bytes)
            return TransportResponse(
                status_code=response.status,
                headers={name.lower(): value for name, value in response.getheaders()},
                body=body,
                connected_ip=pinned_ip,
            )
        except ExternalGatewayError:
            raise
        except (TimeoutError, socket.timeout) as exc:
            raise ExternalGatewayError("request_timeout", retryable=True) from exc
        except (OSError, http.client.HTTPException, ssl.SSLError) as exc:
            raise ExternalGatewayError("connection_failed", retryable=True) from exc
        finally:
            connection.close()


class TTLResponseCache:
    def __init__(self, *, max_entries: int = 256, clock: Clock = time.monotonic) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> object | None:
        now = self._clock()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= now:
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return value

    def put(self, key: str, value: object, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        with self._lock:
            self._entries[key] = (self._clock() + ttl_seconds, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


class LocalRateLimiter:
    """Thread-safe transport-attempt throttle scoped to this Python instance."""

    def __init__(self, *, clock: Clock = time.monotonic) -> None:
        self._clock = clock
        self._requests: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, api_id: str, *, limit: int, window_seconds: float) -> bool:
        now = self._clock()
        with self._lock:
            bucket = self._requests.setdefault(api_id, deque())
            cutoff = now - window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


def _canonical_query(query: Mapping[str, object]) -> str:
    """Return the deterministic doseq wire representation used by transport."""
    return urlencode(sorted(query.items(), key=lambda item: str(item[0])), doseq=True)


def _canonical_form(form_fields: Mapping[str, str]) -> str:
    """Return the deterministic form wire representation used by transport."""
    return urlencode(sorted(form_fields.items(), key=lambda item: item[0]))


class ExternalAPIGateway:
    _TRANSIENT_STATUSES = {429, 502, 503, 504}

    def __init__(
        self,
        *,
        registry: object,
        resolver: Resolver | None = None,
        transport: Transport | None = None,
        cache: TTLResponseCache | None = None,
        rate_limiter: LocalRateLimiter | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        event_sink: EventSink | None = None,
        credential_resolver: CredentialResolver | None = None,
    ) -> None:
        self.registry = registry
        self.policy = ExternalAPIPolicy(registry)
        self.resolver = resolver or SystemResolver()
        self.transport = transport or PinnedHTTPSTransport()
        self.cache = cache if cache is not None else TTLResponseCache()
        self.rate_limiter = rate_limiter if rate_limiter is not None else LocalRateLimiter()
        self.sleeper = sleeper
        self.event_sink = event_sink
        self.credential_resolver = credential_resolver or EnvironmentCredentialResolver()

    def _emit(self, event: str, payload: dict[str, object], sink: EventSink | None) -> None:
        try:
            if sink or self.event_sink:
                (sink or self.event_sink)(event, payload)  # type: ignore[misc]
        except Exception:
            return

    @staticmethod
    def _cache_key(request: ExternalAPIRequest) -> str:
        payload = json.dumps(
            {
                "api_id": request.api_id,
                "method": request.method.upper(),
                "path": request.path,
                "query": _canonical_query(request.query),
                "form": _canonical_form(request.form_fields),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return f"external-api-cache:v2:{hashlib.sha256(payload).hexdigest()}"

    def execute(
        self,
        request: ExternalAPIRequest,
        *,
        global_enabled: bool | None = None,
        provider_enabled: bool = False,
        event_sink: EventSink | None = None,
    ) -> ExternalAPIResponse:
        definition = self.registry.get(request.api_id)
        if definition is None:
            self._emit(
                "external_api.policy_denied",
                {"api_id": request.api_id, "reason": "unknown_api"},
                event_sink,
            )
            raise ExternalGatewayError("unknown_api")
        base = urlsplit(definition.base_url)
        canonical_query = _canonical_query(request.query)
        endpoint = urlunsplit((base.scheme, base.netloc, request.path, canonical_query, ""))
        decision = self.policy.evaluate(
            api_id=request.api_id,
            endpoint=endpoint,
            method=request.method,
            feature_enabled=global_enabled,
        )
        if not decision.allowed or not provider_enabled:
            reason = decision.reason if not decision.allowed else "provider_disabled"
            self._emit(
                "external_api.policy_denied",
                {"api_id": request.api_id, "reason": reason},
                event_sink,
            )
            raise ExternalGatewayError(reason)
        if set(request.form_fields) - set(definition.allowed_form_fields):
            raise ExternalGatewayError("form_field_not_allowed")
        canonical_form = _canonical_form(request.form_fields)
        body = canonical_form.encode("utf-8") if canonical_form else b""
        if len(body) > definition.max_request_body_bytes:
            raise ExternalGatewayError("request_body_too_large")
        credential = None
        if definition.auth_type.value != "none":
            try:
                credential = self.credential_resolver.resolve(definition.credential_id or "")
            except ValueError as exc:
                code = str(exc)
                self._emit(
                    "external_api.request_failed",
                    {"api_id": request.api_id, "reason": code, "auth_required": True},
                    event_sink,
                )
                raise ExternalGatewayError(code) from None
            if credential.header_name.lower() != str(definition.auth_header_name).lower():
                raise ExternalGatewayError("credential_invalid")
        key = self._cache_key(request)
        cached = self.cache.get(key) if definition.cache_ttl_seconds else None
        if cached is not None:
            self._emit(
                "external_api.cache_hit", {"api_id": request.api_id, "cached": True}, event_sink
            )
            return self._response(definition, endpoint, cached, cached=True)
        host = str(base.hostname or "")
        port = base.port or 443
        headers = {"Accept": "application/json", "User-Agent": "Omni-External-API/1"}
        headers.update(request.headers)
        if body:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            headers["Content-Length"] = str(len(body))
        if credential is not None:
            headers[credential.header_name] = credential.secret
        self._emit(
            "external_api.request_started",
            {"api_id": request.api_id, "method": request.method.upper()},
            event_sink,
        )
        last_error: ExternalGatewayError | None = None
        for attempt in range(1, definition.max_attempts + 1):
            try:
                if not self.rate_limiter.allow(
                    request.api_id,
                    limit=definition.rate_limit_requests,
                    window_seconds=definition.rate_limit_window_seconds,
                ):
                    self._emit("external_api.rate_limited", {"api_id": request.api_id}, event_sink)
                    raise ExternalGatewayError("rate_limit_exceeded")
                validated = validate_resolved_addresses(self.resolver.resolve(host, port))
                pinned_ip = validated[0]
                target = request.path + (f"?{canonical_query}" if canonical_query else "")
                transport_response = self.transport.request(
                    logical_host=host,
                    pinned_ip=pinned_ip,
                    port=port,
                    method=request.method.upper(),
                    target=target,
                    headers=headers,
                    body=body,
                    timeout_seconds=definition.timeout_seconds,
                    max_response_bytes=definition.max_response_bytes,
                )
                if transport_response.connected_ip != pinned_ip:
                    raise ExternalGatewayError("pinned_ip_mismatch")
                if 300 <= transport_response.status_code < 400:
                    if definition.redirect_policy is RedirectPolicy.DENY:
                        raise ExternalGatewayError("redirect_denied")
                    raise ExternalGatewayError("redirect_policy_not_implemented")
                if transport_response.status_code in self._TRANSIENT_STATUSES:
                    raise ExternalGatewayError("transient_http_status", retryable=True)
                if credential is not None and transport_response.status_code in {401, 403}:
                    raise ExternalGatewayError(
                        "provider_auth_failed", status_code=transport_response.status_code
                    )
                if transport_response.status_code >= 400:
                    raise ExternalGatewayError(
                        "provider_http_error", status_code=transport_response.status_code
                    )
                if len(transport_response.body) > definition.max_response_bytes:
                    raise ExternalGatewayError("response_too_large")
                try:
                    data = json.loads(transport_response.body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ExternalGatewayError("malformed_json") from exc
                if definition.cache_ttl_seconds:
                    self.cache.put(key, data, definition.cache_ttl_seconds)
                self._emit(
                    "external_api.request_succeeded",
                    {"api_id": request.api_id, "cached": False},
                    event_sink,
                )
                return self._response(definition, endpoint, data, cached=False)
            except ExternalGatewayError as exc:
                last_error = exc
                if (
                    not exc.retryable
                    or request.method.upper() != "GET"
                    or attempt >= definition.max_attempts
                ):
                    break
                self.sleeper(0.05 * attempt)
        assert last_error is not None
        self._emit(
            "external_api.request_failed",
            {"api_id": request.api_id, "reason": last_error.code},
            event_sink,
        )
        raise last_error

    @staticmethod
    def _response(
        definition: object, endpoint: str, data: object, *, cached: bool
    ) -> ExternalAPIResponse:
        provenance = ExternalResponseProvenance(
            source_type="external_api",
            provider=definition.name,
            api_id=definition.api_id,
            retrieved_at=datetime.now(UTC),
            endpoint=endpoint,
            cached=cached,
            freshness="cache" if cached else "live",
            request_id=f"external-{uuid.uuid4().hex}",
            attribution=definition.provenance,
        ).as_dict()
        return ExternalAPIResponse(status_code=200, data=data, provenance=provenance)

    def require_feature_gates(
        self,
        *,
        api_id: str,
        global_enabled: bool | None,
        provider_enabled: bool,
        event_sink: EventSink | None = None,
    ) -> None:
        """Apply canonical tool gates before a local shortcut can bypass transport."""
        effective_global = external_api_enabled() if global_enabled is None else global_enabled
        reason = "external_api_disabled" if not effective_global else "provider_disabled"
        if effective_global and provider_enabled:
            return
        self._emit(
            "external_api.policy_denied",
            {"api_id": api_id, "reason": reason},
            event_sink,
        )
        raise ExternalGatewayError(reason)
