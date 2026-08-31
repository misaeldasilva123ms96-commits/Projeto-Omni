"""Bounded deterministic parsers for untrusted discovery catalogs."""

from __future__ import annotations

import base64
import binascii
import re
import unicodedata
from datetime import UTC, datetime
from urllib.parse import unquote, urlsplit

from brain.runtime.external.gateway import ExternalGatewayError
from brain.runtime.external.discovery.models import (
    DiscoveryCandidate,
    SourceProvenance,
    candidate_id,
)

MAX_CATALOG_ENTRIES = 5_000
MAX_VERSIONS = 100
MAX_PUBLIC_APIS_BYTES = 2 * 1024 * 1024
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_AMBIGUOUS_PATH_ENCODINGS = ("%2e", "%2f", "%5c", "%252e", "%252f", "%255c")


def sanitize_text(value: object, limit: int) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = _CONTROL.sub("", text).replace("\r", " ").replace("\n", " ")
    return " ".join(text.split())[:limit]


def _display_url(value: object) -> str | None:
    url = sanitize_text(value, 2_048)
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    return url


def _schema_locator(value: object) -> str | None:
    if not isinstance(value, str) or any(char in value for char in ("\\", "\x00", "\r", "\n")):
        return None
    url = sanitize_text(value, 2_048)
    if any(char in url for char in ("\\", "\x00", "\r", "\n")):
        return None
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return None
    raw_path = parsed.path
    if any(token in raw_path.casefold() for token in _AMBIGUOUS_PATH_ENCODINGS):
        return None
    path = unquote(raw_path)
    segments = path.split("/")
    if (
        parsed.scheme == "https"
        and parsed.hostname == "api.apis.guru"
        and parsed.username is None
        and parsed.password is None
        and port in {None, 443}
        and not parsed.query
        and not parsed.fragment
        and path.startswith("/v2/specs/")
        and "//" not in raw_path
        and "//" not in path
        and not any(segment in {".", ".."} for segment in segments)
        and segments[-1] in {"swagger.json", "openapi.json"}
    ):
        return url
    return None


def parse_apis_guru(
    data: object, provenance: SourceProvenance, *, discovered_at: str | None = None
) -> tuple[DiscoveryCandidate, ...]:
    if not isinstance(data, dict) or len(data) > MAX_CATALOG_ENTRIES:
        raise ExternalGatewayError("catalog_schema_error")
    now = discovered_at or datetime.now(UTC).isoformat()
    candidates: list[DiscoveryCandidate] = []
    for raw_id, raw_entry in sorted(data.items(), key=lambda item: str(item[0])):
        if not isinstance(raw_entry, dict):
            continue
        versions = raw_entry.get("versions")
        preferred = sanitize_text(raw_entry.get("preferred"), 255)
        if (
            not isinstance(versions, dict)
            or len(versions) > MAX_VERSIONS
            or preferred not in versions
        ):
            continue
        version = versions[preferred]
        if not isinstance(version, dict):
            continue
        info = version.get("info") if isinstance(version.get("info"), dict) else {}
        catalog_id = sanitize_text(raw_id, 512)
        provider, _, service = catalog_id.partition(":")
        raw_locator = version.get("swaggerUrl")
        locator = _schema_locator(raw_locator)
        issues: list[str] = []
        if raw_locator and not locator:
            issues.append("invalid_schema_locator")
        openapi_version = sanitize_text(version.get("openapiVer"), 255) or None
        if openapi_version is None:
            issues.append("missing_openapi_version")
        external_docs = version.get("externalDocs")
        if "externalDocs" not in version:
            external_docs = info.get("externalDocs")
        categories = info.get("x-apisguru-categories", ())
        if not isinstance(categories, list):
            categories = ()
        category = ", ".join(sanitize_text(item, 100) for item in categories[:20]) or None
        candidates.append(
            DiscoveryCandidate(
                candidate_id=candidate_id("apis_guru", catalog_id),
                source="apis_guru",
                source_record_id=catalog_id,
                name=sanitize_text(info.get("title") or catalog_id, 300),
                description=sanitize_text(info.get("description"), 2_000),
                category=category,
                provider=sanitize_text(provider, 255) or None,
                service=sanitize_text(service, 255) or None,
                documentation_url=(
                    _display_url(external_docs.get("url"))
                    if isinstance(external_docs, dict)
                    else None
                ),
                schema_available=locator is not None,
                schema_locator=locator,
                preferred_version=preferred,
                openapi_version=openapi_version,
                source_added_at=sanitize_text(version.get("added"), 255) or None,
                source_updated_at=sanitize_text(version.get("updated"), 255) or None,
                discovered_at=now,
                issues=tuple(issues),
                source_provenance=provenance,
            )
        )
    return tuple(candidates)


def decode_public_apis_content(data: object) -> tuple[str, str]:
    if not isinstance(data, dict):
        raise ExternalGatewayError("catalog_schema_error")
    if (
        data.get("type") != "file"
        or data.get("name") != "README.md"
        or data.get("path") != "README.md"
    ):
        raise ExternalGatewayError("catalog_schema_error")
    if data.get("encoding") != "base64" or not isinstance(data.get("content"), str):
        raise ExternalGatewayError("catalog_encoding_error")
    try:
        encoded = re.sub(r"[ \t\r\n]", "", data["content"])
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ExternalGatewayError("catalog_encoding_error") from exc
    if len(decoded) > MAX_PUBLIC_APIS_BYTES:
        raise ExternalGatewayError("catalog_too_large")
    try:
        return decoded.decode("utf-8"), sanitize_text(data.get("sha"), 255)
    except UnicodeDecodeError as exc:
        raise ExternalGatewayError("catalog_encoding_error") from exc


def parse_public_apis(
    markdown: str, provenance: SourceProvenance, *, discovered_at: str | None = None
) -> tuple[DiscoveryCandidate, ...]:
    now = discovered_at or datetime.now(UTC).isoformat()
    lines = markdown.splitlines()
    category: str | None = None
    output: list[DiscoveryCandidate] = []
    index = 0
    while index < len(lines) and len(output) < MAX_CATALOG_ENTRIES:
        line = lines[index].strip()
        if line.startswith("### "):
            category = sanitize_text(line[4:], 100)
        if category and [part.strip() for part in line.strip("|").split("|")] == [
            "API",
            "Description",
            "Auth",
            "HTTPS",
            "CORS",
        ]:
            index += 2
            while index < len(lines) and "|" in lines[index]:
                cells = [part.strip() for part in lines[index].strip().strip("|").split("|")]
                if len(cells) == 5:
                    match = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", cells[0])
                    if match:
                        name, raw_url = match.groups()
                        url = _display_url(raw_url)
                        issues = () if url else ("invalid_documentation_url",)
                        safe_name = sanitize_text(name, 300)
                        safe_url = sanitize_text(raw_url, 2_048)
                        record = f"{category}\x00{safe_name}\x00{safe_url}"
                        output.append(
                            DiscoveryCandidate(
                                candidate_id=candidate_id("public_apis", record),
                                source="public_apis",
                                source_record_id=record,
                                name=sanitize_text(name, 300),
                                description=sanitize_text(cells[1], 2_000),
                                category=category,
                                documentation_url=url,
                                auth_hint=sanitize_text(cells[2], 255) or None,
                                https_hint=sanitize_text(cells[3], 255) or None,
                                cors_hint=sanitize_text(cells[4], 255) or None,
                                discovered_at=now,
                                issues=issues,
                                source_provenance=provenance,
                            )
                        )
                index += 1
            continue
        index += 1
    return tuple(output)
