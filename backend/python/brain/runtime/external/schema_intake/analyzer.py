"""Bounded, deterministic structural inspection of OpenAPI JSON documents."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from urllib.parse import urlsplit

from brain.runtime.external.discovery.models import DiscoveryCandidate
from brain.runtime.external.discovery.parsers import sanitize_text
from brain.runtime.external.schema_intake.models import (
    DeclaredServer,
    OperationSummary,
    ProviderDesignProposal,
    ReferenceAudit,
    SecuritySchemeSummary,
)
from brain.runtime.external.schema_intake.registry import SchemaIntakeError

MAX_TREE_NODES = 150_000
MAX_DEPTH = 128
MAX_PATHS = 10_000
MAX_OPERATIONS = 50_000
MAX_OPERATION_DETAILS = 500
MAX_REFERENCES = 25_000
MAX_SECURITY_SCHEMES = 200
MAX_SERVERS = 200
MAX_BINARY_AUDIT_NODES = 10_000
MAX_TAGS = 500
PROPOSAL_FORMAT_VERSION = "provider-design-proposal-v2"
_OAS3 = re.compile(r"^3\.(?:0|1|2)\.\d+$")
_METHODS_V2 = frozenset({"get", "put", "post", "delete", "options", "head", "patch"})
_METHODS_V3 = _METHODS_V2 | {"trace"}
_MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def build_proposal_id(
    candidate_id: str, canonical_schema_sha256: str, proposal_format_version: str
) -> str:
    material = f"{candidate_id}\x00{canonical_schema_sha256}\x00{proposal_format_version}".encode()
    return hashlib.sha256(material).hexdigest()


def _detected_version(document: dict[str, object]) -> str:
    if document.get("swagger") == "2.0":
        return "2.0"
    value = document.get("openapi")
    if isinstance(value, str) and _OAS3.fullmatch(value):
        return value
    raise SchemaIntakeError("openapi_version_unsupported")


def _bounded_walk(document: object) -> tuple[ReferenceAudit, Counter[str], set[str]]:
    stack: list[tuple[object, int]] = [(document, 0)]
    nodes = internal = external = relative = absolute = unusual = 0
    resources: Counter[str] = Counter()
    signals: set[str] = set()
    resource_keys = {
        "externalValue": "example_external_value",
        "operationRef": "link_operation_ref",
        "authorizationUrl": "oauth_authorization_url",
        "tokenUrl": "oauth_token_url",
        "refreshUrl": "oauth_refresh_url",
        "deviceAuthorizationUrl": "oauth_device_authorization_url",
        "openIdConnectUrl": "openid_connect_url",
        "oauth2MetadataUrl": "oauth2_metadata_url",
    }
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > MAX_TREE_NODES or depth > MAX_DEPTH:
            raise SchemaIntakeError("schema_complexity_limit_exceeded")
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "$ref" and isinstance(child, str):
                    if child.startswith("#"):
                        internal += 1
                    else:
                        external += 1
                        parsed = urlsplit(child)
                        if parsed.scheme or parsed.netloc:
                            absolute += 1
                            if parsed.scheme and parsed.scheme not in {"http", "https"}:
                                unusual += 1
                        else:
                            relative += 1
                    if internal + external > MAX_REFERENCES:
                        raise SchemaIntakeError("schema_complexity_limit_exceeded")
                if key in resource_keys and isinstance(child, str):
                    resources[resource_keys[key]] += 1
                    if key == "oauth2MetadataUrl":
                        signals.add("oauth2_metadata_resource_present")
                if key == "externalDocs" and isinstance(child, dict) and child.get("url"):
                    resources["external_docs"] += 1
                if key == "callbacks" and isinstance(child, dict):
                    resources["callbacks"] += len(child)
                    signals.add("callback_surface_present")
                stack.append((child, depth + 1))
        elif isinstance(value, list):
            stack.extend((child, depth + 1) for child in value)
    return (
        ReferenceAudit(internal, external, relative, absolute, unusual),
        resources,
        signals,
    )


def _server(value: object) -> DeclaredServer | None:
    if not isinstance(value, str):
        return None
    url = sanitize_text(value, 2_048)
    templated = "{" in url or "}" in url
    if templated:
        scheme = url.split(":", 1)[0].lower() if ":" in url else None
        return DeclaredServer(scheme, None, None, "", True)
    try:
        parsed = urlsplit(url)
        return DeclaredServer(
            parsed.scheme.lower() or None,
            parsed.hostname,
            parsed.port,
            parsed.path or "/",
            False,
        )
    except ValueError:
        return DeclaredServer(None, None, None, "", False)


def _servers(document: dict[str, object], version: str) -> tuple[DeclaredServer, ...]:
    values: list[object] = []
    declared_count = 0

    def add_entries(entries: list[object]) -> None:
        nonlocal declared_count
        declared_count += len(entries)
        if declared_count > MAX_SERVERS:
            raise SchemaIntakeError("schema_complexity_limit_exceeded")
        values.extend(item.get("url") for item in entries if isinstance(item, dict))

    if version == "2.0":
        schemes = document.get("schemes") if isinstance(document.get("schemes"), list) else []
        host = document.get("host")
        base_path = document.get("basePath") or ""
        declared_count += len(schemes)
        if declared_count > MAX_SERVERS:
            raise SchemaIntakeError("schema_complexity_limit_exceeded")
        values.extend(f"{scheme}://{host}{base_path}" for scheme in schemes if host)
    else:
        root = document.get("servers") if isinstance(document.get("servers"), list) else []
        add_entries(root)
        paths = document.get("paths") if isinstance(document.get("paths"), dict) else {}
        for path_item in paths.values():
            if not isinstance(path_item, dict):
                continue
            nested = path_item.get("servers") if isinstance(path_item.get("servers"), list) else []
            add_entries(nested)
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                nested = (
                    operation.get("servers") if isinstance(operation.get("servers"), list) else []
                )
                add_entries(nested)
    return tuple(item for item in (_server(value) for value in values) if item)


def _parameter_locations(
    path_item: dict[str, object], operation: dict[str, object]
) -> tuple[str, ...]:
    locations: set[str] = set()
    for owner in (path_item, operation):
        parameters = owner.get("parameters") if isinstance(owner.get("parameters"), list) else []
        for parameter in parameters:
            if isinstance(parameter, dict) and isinstance(parameter.get("in"), str):
                locations.add(sanitize_text(parameter["in"], 50))
    return tuple(sorted(locations))


def _content_types(mapping: object) -> tuple[str, ...]:
    return (
        tuple(sorted(sanitize_text(key, 200) for key in mapping))
        if isinstance(mapping, dict)
        else ()
    )


def _analyze_operation_security(
    operation: dict[str, object], version: str
) -> tuple[bool, str, int, bool, set[str]]:
    if "security" not in operation:
        return False, "inherits_global", 0, False, set()
    declaration = operation["security"]
    if not isinstance(declaration, list) or any(
        not isinstance(requirement, dict) for requirement in declaration
    ):
        return True, "invalid", 0, False, {"invalid_operation_security_declaration"}
    if not declaration:
        return True, "explicit_empty", 0, False, {"operation_explicitly_disables_security"}
    anonymous = any(not requirement for requirement in declaration)
    if anonymous and version != "2.0":
        return (
            True,
            "explicit_optional_anonymous",
            len(declaration),
            True,
            {"operation_anonymous_access_option_declared"},
        )
    signals = {"ambiguous_empty_security_requirement"} if anonymous else set()
    return True, "explicit_requirements", len(declaration), anonymous, signals


def _operations(
    document: dict[str, object], version: str
) -> tuple[int, Counter[str], tuple[OperationSummary, ...], bool, set[str]]:
    paths = document.get("paths")
    if not isinstance(paths, dict):
        paths = {}
    if len(paths) > MAX_PATHS:
        raise SchemaIntakeError("schema_complexity_limit_exceeded")
    methods = _METHODS_V2 if version == "2.0" else _METHODS_V3
    if version.startswith("3.2."):
        methods = methods | {"query"}
    count = 0
    details: list[OperationSummary] = []
    method_counts: Counter[str] = Counter()
    signals: set[str] = set()
    for path, raw_item in sorted(paths.items(), key=lambda item: str(item[0])):
        if not isinstance(raw_item, dict):
            continue
        entries: list[tuple[str, object]] = [
            (key, value) for key, value in raw_item.items() if key in methods
        ]
        if version.startswith("3.2.") and isinstance(raw_item.get("additionalOperations"), dict):
            entries.extend(
                (str(key), value) for key, value in raw_item["additionalOperations"].items()
            )
        for raw_method, raw_operation in entries:
            if not isinstance(raw_operation, dict):
                continue
            count += 1
            if count > MAX_OPERATIONS:
                raise SchemaIntakeError("schema_complexity_limit_exceeded")
            method = raw_method.upper()
            method_counts[method] += 1
            mutating = method in _MUTATING or method not in {item.upper() for item in methods}
            if mutating:
                signals.add("mutation_review_required")
            if method == "GET":
                signals.add("read_method_present")
            locations = _parameter_locations(raw_item, raw_operation)
            if "cookie" in locations:
                signals.add("cookie_parameter_present")
            if "header" in locations:
                signals.add("header_parameters_present")
            if "body" in locations:
                signals.add("body_parameters_present")
            if "formData" in locations:
                signals.add("form_upload_possible")
            request_body = raw_operation.get("requestBody")
            if version == "2.0":
                consumes = raw_operation.get("consumes", document.get("consumes", []))
                request_types = (
                    tuple(sorted(sanitize_text(item, 200) for item in consumes))
                    if isinstance(consumes, list)
                    else ()
                )
            else:
                request_types = (
                    _content_types(request_body.get("content"))
                    if isinstance(request_body, dict)
                    else ()
                )
            if any(_contains_binary(item) for item in (raw_operation, request_body)):
                signals.add("file_upload_surface_present")
            responses = (
                raw_operation.get("responses")
                if isinstance(raw_operation.get("responses"), dict)
                else {}
            )
            response_types: set[str] = set()
            for response in responses.values():
                if isinstance(response, dict):
                    response_types.update(_content_types(response.get("content")))
            if version == "2.0":
                produces = raw_operation.get("produces", document.get("produces", []))
                if isinstance(produces, list):
                    response_types.update(sanitize_text(item, 200) for item in produces)
            security_override, security_mode, security_count, anonymous, security_signals = (
                _analyze_operation_security(raw_operation, version)
            )
            signals.update(security_signals)
            if len(details) < MAX_OPERATION_DETAILS:
                details.append(
                    OperationSummary(
                        method,
                        sanitize_text(path, 1_000),
                        sanitize_text(raw_operation.get("operationId"), 255) or None,
                        sanitize_text(raw_operation.get("summary"), 500),
                        raw_operation.get("deprecated") is True,
                        locations,
                        request_types,
                        tuple(sorted(response_types)),
                        security_override,
                        security_mode,
                        security_count,
                        anonymous,
                        mutating,
                    )
                )
    return count, method_counts, tuple(details), count > len(details), signals


def _contains_binary(value: object) -> bool:
    stack = [value]
    examined = 0
    while stack and examined < MAX_BINARY_AUDIT_NODES:
        item = stack.pop()
        examined += 1
        if isinstance(item, dict):
            if item.get("format") == "binary" or item.get("type") == "file":
                return True
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    if stack:
        raise SchemaIntakeError("schema_complexity_limit_exceeded")
    return False


def _security(
    document: dict[str, object], version: str
) -> tuple[tuple[SecuritySchemeSummary, ...], set[str]]:
    if version == "2.0":
        schemes = document.get("securityDefinitions")
    else:
        components = (
            document.get("components") if isinstance(document.get("components"), dict) else {}
        )
        schemes = components.get("securitySchemes")
    schemes = schemes if isinstance(schemes, dict) else {}
    if len(schemes) > MAX_SECURITY_SCHEMES:
        raise SchemaIntakeError("schema_complexity_limit_exceeded")
    known = (
        {"basic", "apiKey", "oauth2"}
        if version == "2.0"
        else {"apiKey", "http", "oauth2", "openIdConnect", "mutualTLS"}
    )
    result: list[SecuritySchemeSummary] = []
    signals: set[str] = set()
    for name, raw in sorted(schemes.items(), key=lambda item: str(item[0])):
        raw = raw if isinstance(raw, dict) else {}
        kind = sanitize_text(raw.get("type"), 100) or "unknown"
        if kind not in known:
            signals.add("unknown_security_scheme")
        location = sanitize_text(raw.get("in"), 50) or None
        if kind == "apiKey" and location == "query":
            signals.add("api_key_in_query_declared")
        if kind == "openIdConnect":
            signals.add("openid_connect_declared")
        flows = raw.get("flows") if isinstance(raw.get("flows"), dict) else {}
        if version == "2.0" and kind == "oauth2":
            flow_names = (sanitize_text(raw.get("flow"), 100),)
            scope_map = raw.get("scopes") if isinstance(raw.get("scopes"), dict) else {}
        else:
            flow_names = tuple(sorted(sanitize_text(key, 100) for key in flows))
            scope_map = {}
            for flow in flows.values():
                if isinstance(flow, dict) and isinstance(flow.get("scopes"), dict):
                    scope_map.update(flow["scopes"])
        result.append(
            SecuritySchemeSummary(
                sanitize_text(name, 255),
                kind,
                location,
                sanitize_text(raw.get("scheme"), 100) or None,
                tuple(item for item in flow_names if item),
                len(scope_map),
            )
        )
    return tuple(result), signals


def analyze_openapi_schema(
    candidate: DiscoveryCandidate, document: object
) -> ProviderDesignProposal:
    if not isinstance(document, dict):
        raise SchemaIntakeError("openapi_schema_invalid")
    try:
        version = _detected_version(document)
        tags = document.get("tags") if isinstance(document.get("tags"), list) else []
        if len(tags) > MAX_TAGS:
            raise SchemaIntakeError("schema_complexity_limit_exceeded")
        references, resources, walk_signals = _bounded_walk(document)
        servers = _servers(document, version)
        operation_count, method_counts, operations, truncated, operation_signals = _operations(
            document, version
        )
        security, security_signals = _security(document, version)
        webhooks = document.get("webhooks") if isinstance(document.get("webhooks"), dict) else {}
        if len(webhooks) > MAX_PATHS:
            raise SchemaIntakeError("schema_complexity_limit_exceeded")
        canonical = json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    except (RecursionError, MemoryError) as exc:
        raise SchemaIntakeError("schema_complexity_limit_exceeded") from exc
    digest = hashlib.sha256(canonical).hexdigest()
    issues: set[str] = set()
    blockers: set[str] = set()
    signals = walk_signals | operation_signals | security_signals
    if "invalid_operation_security_declaration" in signals:
        issues.add("invalid_operation_security_declaration")
    if candidate.openapi_version and candidate.openapi_version != version:
        issues.add("catalog_schema_version_mismatch")
        blockers.add("catalog_schema_version_mismatch")
    if references.external_refs:
        blockers.add("external_refs_present")
    if any(server.scheme == "http" for server in servers):
        signals.add("insecure_http_server_declared")
    authorities = {(server.hostname, server.port) for server in servers if server.hostname}
    if len(authorities) > 1:
        signals.add("multiple_server_authorities")
    if webhooks:
        signals.add("webhook_surface_present")
        blockers.add("webhooks_present")
    callbacks = resources["callbacks"]
    if callbacks:
        blockers.add("callbacks_present")
    if security:
        blockers.add("credential_design_review_required")
    blockers.update(
        signals
        & {
            "insecure_http_server_declared",
            "api_key_in_query_declared",
            "unknown_security_scheme",
            "multiple_server_authorities",
            "file_upload_surface_present",
            "operation_explicitly_disables_security",
            "operation_anonymous_access_option_declared",
            "ambiguous_empty_security_requirement",
            "invalid_operation_security_declaration",
        }
    )
    info = document.get("info") if isinstance(document.get("info"), dict) else {}
    if not info.get("title") or not info.get("version"):
        issues.add("schema_metadata_incomplete")
        blockers.add("schema_metadata_incomplete")
    license_info = info.get("license") if isinstance(info.get("license"), dict) else {}
    proposal_format_version = PROPOSAL_FORMAT_VERSION
    return ProviderDesignProposal(
        build_proposal_id(candidate.candidate_id, digest, proposal_format_version),
        proposal_format_version,
        candidate.candidate_id,
        candidate.source_record_id,
        digest,
        len(canonical),
        candidate.openapi_version,
        version,
        sanitize_text(info.get("title"), 300),
        sanitize_text(info.get("version"), 255) or None,
        sanitize_text(license_info.get("name"), 255) or None,
        sanitize_text(license_info.get("identifier"), 255) or None,
        bool(license_info.get("url")),
        bool(info.get("termsOfService")),
        servers,
        operation_count,
        tuple(sorted(method_counts.items())),
        operations,
        truncated,
        security,
        "security" in document,
        len(document.get("security", [])) if isinstance(document.get("security"), list) else 0,
        references,
        tuple(sorted(resources.items())),
        callbacks,
        len(webhooks),
        tuple(sorted(signals)),
        tuple(sorted(issues)),
        tuple(sorted(blockers)),
    )
