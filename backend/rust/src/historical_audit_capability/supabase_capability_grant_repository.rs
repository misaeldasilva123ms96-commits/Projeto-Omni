use std::{
    error::Error,
    fmt,
    future::Future,
    io,
    net::{IpAddr, Ipv4Addr, SocketAddr},
    pin::Pin,
    sync::Arc,
    time::Duration,
};

use reqwest::{
    dns::{Addrs, Name, Resolve, Resolving},
    header::{
        HeaderMap, HeaderName, HeaderValue, ACCEPT, ACCEPT_ENCODING, AUTHORIZATION,
        CONTENT_ENCODING, CONTENT_LENGTH, CONTENT_RANGE, CONTENT_TYPE,
    },
    redirect::Policy,
    StatusCode, Url,
};
use serde::de::{self, MapAccess, Visitor};
use serde::{Deserialize, Deserializer};
use time::{format_description::well_known::Rfc3339, OffsetDateTime};
use uuid::Uuid;

use super::{
    CapabilityGrantLookup, CapabilityGrantRecord,
    HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_SUPABASE_GRANTS,
    HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_UNAVAILABLE,
};

const HISTORICAL_AUDIT_CAPABILITY: &str = "historical_audit:read";
const POSTGREST_RESOURCE_PATH: &str = "/rest/v1/omni_capability_grants";
const POSTGREST_PROJECTION: &str = "supabase_sub,capability,active,revoked_at,expires_at";
const MAX_RESPONSE_BODY_BYTES: usize = 16_384;
const DEFAULT_TIMEOUT_MS: u64 = 750;
const MIN_TIMEOUT_MS: u64 = 100;
const MAX_TIMEOUT_MS: u64 = 2_000;
const SUPABASE_PROJECT_REF_LENGTH: usize = 20;

const SOURCE_ENV: &str = "OMNI_HISTORICAL_AUDIT_CAPABILITY_SOURCE";
const URL_ENV: &str = "OMNI_HISTORICAL_AUDIT_SUPABASE_URL";
const SERVICE_ROLE_KEY_ENV: &str = "OMNI_HISTORICAL_AUDIT_SUPABASE_SERVICE_ROLE_KEY";
const TIMEOUT_ENV: &str = "OMNI_HISTORICAL_AUDIT_CAPABILITY_TIMEOUT_MS";
const ENABLED_ENV: &str = "OMNI_HISTORICAL_AUDIT_CAPABILITY_ADAPTER_ENABLED";

const APIKEY: HeaderName = HeaderName::from_static("apikey");

type TransportFuture<'a> = Pin<
    Box<
        dyn Future<Output = Result<CapabilityGrantTransportResponse, TransportFailure>> + Send + 'a,
    >,
>;

trait CapabilityGrantTransport: Send + Sync {
    fn execute<'a>(&'a self, request: CapabilityGrantRequest) -> TransportFuture<'a>;
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum TransportFailure {
    Unavailable,
    Timeout,
    Malformed,
}

struct CapabilityGrantRequest {
    url: Url,
    query: Vec<(&'static str, String)>,
    headers: HeaderMap,
}

struct CapabilityGrantTransportResponse {
    status: StatusCode,
    content_type: Option<String>,
    content_encoding: Option<String>,
    content_length: Option<u64>,
    content_range: Option<String>,
    headers_invalid: bool,
    body: Vec<u8>,
    oversized: bool,
}

struct ReqwestCapabilityGrantTransport {
    client: reqwest::Client,
}

impl CapabilityGrantTransport for ReqwestCapabilityGrantTransport {
    fn execute<'a>(&'a self, request: CapabilityGrantRequest) -> TransportFuture<'a> {
        Box::pin(async move {
            let CapabilityGrantRequest {
                url,
                query,
                headers,
            } = request;
            let mut response = self
                .client
                .get(url)
                .query(&query)
                .headers(headers)
                .send()
                .await
                .map_err(map_send_error)?;

            let status = response.status();
            let ResponseHeaderMetadata {
                content_type,
                content_encoding,
                content_length,
                content_range,
                invalid: headers_invalid,
            } = parse_response_headers(response.headers());

            if status != StatusCode::OK {
                return Ok(CapabilityGrantTransportResponse {
                    status,
                    content_type,
                    content_encoding,
                    content_length,
                    content_range,
                    headers_invalid,
                    body: Vec::new(),
                    oversized: false,
                });
            }

            if content_length
                .map(|length| length > MAX_RESPONSE_BODY_BYTES as u64)
                .unwrap_or(false)
            {
                return Ok(CapabilityGrantTransportResponse {
                    status,
                    content_type,
                    content_encoding,
                    content_length,
                    content_range,
                    headers_invalid,
                    body: Vec::new(),
                    oversized: true,
                });
            }

            let mut body = Vec::with_capacity(
                content_length
                    .and_then(|length| usize::try_from(length).ok())
                    .unwrap_or(0)
                    .min(MAX_RESPONSE_BODY_BYTES),
            );
            while let Some(chunk) = response.chunk().await.map_err(map_body_error)? {
                if body.len().saturating_add(chunk.len()) > MAX_RESPONSE_BODY_BYTES {
                    return Ok(CapabilityGrantTransportResponse {
                        status,
                        content_type,
                        content_encoding,
                        content_length,
                        content_range,
                        headers_invalid,
                        body: Vec::new(),
                        oversized: true,
                    });
                }
                body.extend_from_slice(&chunk);
            }

            Ok(CapabilityGrantTransportResponse {
                status,
                content_type,
                content_encoding,
                content_length,
                content_range,
                headers_invalid,
                body,
                oversized: false,
            })
        })
    }
}

fn map_send_error(error: reqwest::Error) -> TransportFailure {
    if error.is_timeout() {
        TransportFailure::Timeout
    } else {
        TransportFailure::Unavailable
    }
}

fn map_body_error(error: reqwest::Error) -> TransportFailure {
    if error.is_timeout() {
        TransportFailure::Timeout
    } else {
        TransportFailure::Malformed
    }
}

struct ResponseHeaderMetadata {
    content_type: Option<String>,
    content_encoding: Option<String>,
    content_length: Option<u64>,
    content_range: Option<String>,
    invalid: bool,
}

fn parse_response_headers(headers: &HeaderMap) -> ResponseHeaderMetadata {
    let content_type = single_header_value(headers, &CONTENT_TYPE);
    let content_encoding = single_header_value(headers, &CONTENT_ENCODING);
    let content_range = single_header_value(headers, &CONTENT_RANGE);
    let content_length = single_header_value(headers, &CONTENT_LENGTH).and_then(|value| {
        value
            .map(|raw| raw.parse::<u64>().map_err(|_| ()))
            .transpose()
    });
    let invalid = content_type.is_err()
        || content_encoding.is_err()
        || content_length.is_err()
        || content_range.is_err();

    ResponseHeaderMetadata {
        content_type: content_type.unwrap_or(None),
        content_encoding: content_encoding.unwrap_or(None),
        content_length: content_length.unwrap_or(None),
        content_range: content_range.unwrap_or(None),
        invalid,
    }
}

fn single_header_value(headers: &HeaderMap, name: &HeaderName) -> Result<Option<String>, ()> {
    let mut values = headers.get_all(name).iter();
    let Some(value) = values.next() else {
        return Ok(None);
    };
    if values.next().is_some() {
        return Err(());
    }
    value.to_str().map(str::to_owned).map(Some).map_err(|_| ())
}

#[derive(Clone)]
struct ValidatedSupabaseOrigin {
    origin: Url,
    host: String,
}

impl fmt::Debug for ValidatedSupabaseOrigin {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("ValidatedSupabaseOrigin([REDACTED])")
    }
}

impl ValidatedSupabaseOrigin {
    fn parse(raw: &str) -> Result<Self, ()> {
        if raw.trim() != raw || raw.is_empty() || raw.bytes().any(|byte| byte.is_ascii_uppercase())
        {
            return Err(());
        }
        let origin = Url::parse(raw).map_err(|_| ())?;
        if origin.scheme() != "https"
            || !origin.username().is_empty()
            || origin.password().is_some()
            || origin.query().is_some()
            || origin.fragment().is_some()
            || !matches!(origin.path(), "" | "/")
            || origin.port_or_known_default() != Some(443)
            || origin.port().is_some_and(|port| port != 443)
        {
            return Err(());
        }

        let host = origin.host_str().ok_or(())?.to_string();
        if !is_approved_supabase_project_host(&host) {
            return Err(());
        }

        Ok(Self { origin, host })
    }

    fn resource_url(&self) -> Result<Url, ()> {
        self.origin.join(POSTGREST_RESOURCE_PATH).map_err(|_| ())
    }
}

fn is_approved_supabase_project_host(host: &str) -> bool {
    let Some(project_ref) = host.strip_suffix(".supabase.co") else {
        return false;
    };
    project_ref.len() == SUPABASE_PROJECT_REF_LENGTH
        && project_ref
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit())
}

struct SecretServiceRoleKey {
    api_key: HeaderValue,
    authorization: HeaderValue,
}

impl fmt::Debug for SecretServiceRoleKey {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("SecretServiceRoleKey([REDACTED])")
    }
}

impl SecretServiceRoleKey {
    fn parse(raw: &str) -> Result<Self, ()> {
        let normalized = raw.trim();
        if normalized.is_empty() || normalized != raw || is_placeholder_secret(normalized) {
            return Err(());
        }
        let mut api_key = HeaderValue::from_str(normalized).map_err(|_| ())?;
        let mut authorization =
            HeaderValue::from_str(&format!("Bearer {normalized}")).map_err(|_| ())?;
        api_key.set_sensitive(true);
        authorization.set_sensitive(true);
        Ok(Self {
            api_key,
            authorization,
        })
    }

    fn headers(&self) -> HeaderMap {
        let mut headers = HeaderMap::with_capacity(4);
        headers.insert(APIKEY, self.api_key.clone());
        headers.insert(AUTHORIZATION, self.authorization.clone());
        headers.insert(ACCEPT, HeaderValue::from_static("application/json"));
        headers.insert(ACCEPT_ENCODING, HeaderValue::from_static("identity"));
        headers
    }
}

fn is_placeholder_secret(value: &str) -> bool {
    let normalized = value.to_ascii_lowercase();
    [
        "placeholder",
        "changeme",
        "replace-me",
        "your-key",
        "example",
    ]
    .iter()
    .any(|marker| normalized.contains(marker))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct CapabilityLookupTimeout(Duration);

impl CapabilityLookupTimeout {
    fn from_millis(value: u64) -> Result<Self, ()> {
        if !(MIN_TIMEOUT_MS..=MAX_TIMEOUT_MS).contains(&value) {
            return Err(());
        }
        Ok(Self(Duration::from_millis(value)))
    }
}

enum CapabilityAdapterConfiguration {
    Disabled,
    Live(Box<ValidatedLiveConfiguration>),
}

impl CapabilityAdapterConfiguration {
    fn from_lookup<F>(mut lookup: F) -> Result<Self, CapabilityGrantLookup>
    where
        F: FnMut(&str) -> Option<String>,
    {
        let source = lookup(SOURCE_ENV)
            .unwrap_or_else(|| HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_UNAVAILABLE.to_string());
        let enabled = parse_enabled(lookup(ENABLED_ENV).as_deref())?;

        match (source.as_str(), enabled) {
            (HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_UNAVAILABLE, false) => Ok(Self::Disabled),
            (HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_SUPABASE_GRANTS, true) => {
                let origin = lookup(URL_ENV)
                    .ok_or(CapabilityGrantLookup::Misconfigured)
                    .and_then(|value| {
                        ValidatedSupabaseOrigin::parse(&value)
                            .map_err(|_| CapabilityGrantLookup::Misconfigured)
                    })?;
                let secret = lookup(SERVICE_ROLE_KEY_ENV)
                    .ok_or(CapabilityGrantLookup::Misconfigured)
                    .and_then(|value| {
                        SecretServiceRoleKey::parse(&value)
                            .map_err(|_| CapabilityGrantLookup::Misconfigured)
                    })?;
                let timeout = match lookup(TIMEOUT_ENV) {
                    Some(value) => value
                        .parse::<u64>()
                        .map_err(|_| CapabilityGrantLookup::Misconfigured)
                        .and_then(|value| {
                            CapabilityLookupTimeout::from_millis(value)
                                .map_err(|_| CapabilityGrantLookup::Misconfigured)
                        })?,
                    None => CapabilityLookupTimeout(Duration::from_millis(DEFAULT_TIMEOUT_MS)),
                };
                Ok(Self::Live(Box::new(ValidatedLiveConfiguration {
                    origin,
                    secret,
                    timeout,
                })))
            }
            _ => Err(CapabilityGrantLookup::Misconfigured),
        }
    }

    fn source_mode(&self) -> &'static str {
        match self {
            Self::Disabled => HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_UNAVAILABLE,
            Self::Live(_) => HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_SUPABASE_GRANTS,
        }
    }
}

fn parse_enabled(raw: Option<&str>) -> Result<bool, CapabilityGrantLookup> {
    match raw.unwrap_or("false") {
        "true" => Ok(true),
        "false" => Ok(false),
        _ => Err(CapabilityGrantLookup::Misconfigured),
    }
}

struct ValidatedLiveConfiguration {
    origin: ValidatedSupabaseOrigin,
    secret: SecretServiceRoleKey,
    timeout: CapabilityLookupTimeout,
}

impl ValidatedLiveConfiguration {
    fn build(self) -> Result<SupabaseCapabilityGrantRepository, CapabilityGrantLookup> {
        let _ = rustls::crypto::ring::default_provider().install_default();
        let resolver = PublicSupabaseDnsResolver::new(self.origin.host.clone());
        let client = reqwest::Client::builder()
            .https_only(true)
            .min_tls_version(reqwest::tls::Version::TLS_1_2)
            .redirect(Policy::none())
            .no_proxy()
            .connect_timeout(self.timeout.0)
            .timeout(self.timeout.0)
            .pool_max_idle_per_host(2)
            .dns_resolver(resolver)
            .build()
            .map_err(|_| CapabilityGrantLookup::Misconfigured)?;
        Ok(SupabaseCapabilityGrantRepository::new(
            self.origin,
            self.secret,
            self.timeout,
            Arc::new(ReqwestCapabilityGrantTransport { client }),
        ))
    }
}

struct PublicSupabaseDnsResolver {
    expected_host: String,
}

impl PublicSupabaseDnsResolver {
    fn new(expected_host: String) -> Self {
        Self { expected_host }
    }
}

impl Resolve for PublicSupabaseDnsResolver {
    fn resolve(&self, name: Name) -> Resolving {
        let requested_host = name.as_str().to_string();
        let expected_host = self.expected_host.clone();
        Box::pin(async move {
            if requested_host != expected_host {
                return Err(dns_error("capability_dns_host_rejected"));
            }
            let resolved = tokio::net::lookup_host((expected_host.as_str(), 443))
                .await
                .map_err(|_| dns_error("capability_dns_unavailable"))?;
            let addresses: Vec<SocketAddr> = resolved
                .filter(|address| is_public_destination(address.ip()))
                .collect();
            if addresses.is_empty() {
                return Err(dns_error("capability_dns_destination_rejected"));
            }
            Ok(Box::new(addresses.into_iter()) as Addrs)
        })
    }
}

fn dns_error(message: &'static str) -> Box<dyn Error + Send + Sync> {
    Box::new(io::Error::other(message))
}

fn is_public_destination(address: IpAddr) -> bool {
    match address {
        IpAddr::V4(address) => is_public_ipv4(address),
        IpAddr::V6(_) => false,
    }
}

fn is_public_ipv4(address: Ipv4Addr) -> bool {
    let octets = address.octets();
    !(address.is_unspecified()
        || address.is_loopback()
        || address.is_private()
        || address.is_link_local()
        || address.is_multicast()
        || address.is_broadcast()
        || address.is_documentation()
        || octets[0] == 0
        || (octets[0] == 100 && (64..=127).contains(&octets[1]))
        || (octets[0] == 192 && octets[1] == 0 && octets[2] == 0)
        || (octets[0] == 192 && octets[1] == 88 && octets[2] == 99)
        || (octets[0] == 198 && (18..=19).contains(&octets[1]))
        || octets[0] >= 240)
}

struct SupabaseCapabilityGrantRepository {
    origin: ValidatedSupabaseOrigin,
    secret: SecretServiceRoleKey,
    timeout: CapabilityLookupTimeout,
    transport: Arc<dyn CapabilityGrantTransport>,
}

impl fmt::Debug for SupabaseCapabilityGrantRepository {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("SupabaseCapabilityGrantRepository")
            .field("origin", &"[REDACTED]")
            .field("secret", &"[REDACTED]")
            .field("timeout", &self.timeout)
            .finish_non_exhaustive()
    }
}

impl SupabaseCapabilityGrantRepository {
    fn new(
        origin: ValidatedSupabaseOrigin,
        secret: SecretServiceRoleKey,
        timeout: CapabilityLookupTimeout,
        transport: Arc<dyn CapabilityGrantTransport>,
    ) -> Self {
        Self {
            origin,
            secret,
            timeout,
            transport,
        }
    }

    fn source_mode(&self) -> &'static str {
        HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_SUPABASE_GRANTS
    }

    async fn lookup_grants(
        &self,
        caller_sub: &str,
        capability: &str,
        now_ms: u64,
    ) -> CapabilityGrantLookup {
        if capability != HISTORICAL_AUDIT_CAPABILITY {
            return CapabilityGrantLookup::Misconfigured;
        }
        let caller_uuid = match parse_canonical_uuid(caller_sub) {
            Some(uuid) => uuid,
            None => return CapabilityGrantLookup::Malformed,
        };
        let now_rfc3339 = match format_server_timestamp(now_ms) {
            Some(timestamp) => timestamp,
            None => return CapabilityGrantLookup::Misconfigured,
        };
        let request = match self.build_request(caller_uuid, now_rfc3339) {
            Ok(request) => request,
            Err(lookup) => return lookup,
        };

        let response = match tokio::time::timeout(self.timeout.0, self.transport.execute(request))
            .await
        {
            Err(_) => return CapabilityGrantLookup::Timeout,
            Ok(Err(TransportFailure::Timeout)) => return CapabilityGrantLookup::Timeout,
            Ok(Err(TransportFailure::Unavailable)) => return CapabilityGrantLookup::Unavailable,
            Ok(Err(TransportFailure::Malformed)) => return CapabilityGrantLookup::Malformed,
            Ok(Ok(response)) => response,
        };

        self.parse_response(response, caller_uuid, now_ms)
    }

    fn build_request(
        &self,
        caller_uuid: Uuid,
        now_rfc3339: String,
    ) -> Result<CapabilityGrantRequest, CapabilityGrantLookup> {
        let url = self
            .origin
            .resource_url()
            .map_err(|_| CapabilityGrantLookup::Misconfigured)?;
        Ok(CapabilityGrantRequest {
            url,
            query: vec![
                ("select", POSTGREST_PROJECTION.to_string()),
                ("supabase_sub", format!("eq.{caller_uuid}")),
                ("capability", format!("eq.{HISTORICAL_AUDIT_CAPABILITY}")),
                ("active", "eq.true".to_string()),
                ("revoked_at", "is.null".to_string()),
                (
                    "or",
                    format!("(expires_at.is.null,expires_at.gt.{now_rfc3339})"),
                ),
                ("limit", "2".to_string()),
            ],
            headers: self.secret.headers(),
        })
    }

    fn parse_response(
        &self,
        response: CapabilityGrantTransportResponse,
        caller_uuid: Uuid,
        now_ms: u64,
    ) -> CapabilityGrantLookup {
        if response.status != StatusCode::OK {
            return map_http_status(response.status);
        }
        if response.oversized
            || response.headers_invalid
            || response.body.len() > MAX_RESPONSE_BODY_BYTES
            || !valid_json_content_type(response.content_type.as_deref())
            || !valid_content_encoding(response.content_encoding.as_deref())
            || response
                .content_length
                .is_some_and(|length| length != response.body.len() as u64)
        {
            return CapabilityGrantLookup::Malformed;
        }

        let dtos: Vec<CapabilityGrantDto> = match serde_json::from_slice(&response.body) {
            Ok(rows) => rows,
            Err(_) => return CapabilityGrantLookup::Malformed,
        };
        if dtos.len() > 2 || !valid_content_range(response.content_range.as_deref(), dtos.len()) {
            return CapabilityGrantLookup::Malformed;
        }

        let mut records = Vec::with_capacity(dtos.len());
        for dto in dtos {
            match dto.into_record(caller_uuid, now_ms) {
                Some(record) => records.push(record),
                None => return CapabilityGrantLookup::Malformed,
            }
        }
        CapabilityGrantLookup::Records(records)
    }
}

fn map_http_status(status: StatusCode) -> CapabilityGrantLookup {
    match status {
        StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN => CapabilityGrantLookup::Forbidden,
        StatusCode::REQUEST_TIMEOUT => CapabilityGrantLookup::Timeout,
        StatusCode::TOO_MANY_REQUESTS => CapabilityGrantLookup::Unavailable,
        status if status.is_server_error() => CapabilityGrantLookup::Unavailable,
        status if status.is_redirection() || status == StatusCode::NO_CONTENT => {
            CapabilityGrantLookup::Malformed
        }
        status if status.is_client_error() => CapabilityGrantLookup::Misconfigured,
        _ => CapabilityGrantLookup::Malformed,
    }
}

fn valid_json_content_type(value: Option<&str>) -> bool {
    let Some(value) = value else {
        return false;
    };
    let mut parts = value.split(';').map(str::trim);
    if !parts
        .next()
        .is_some_and(|media_type| media_type.eq_ignore_ascii_case("application/json"))
    {
        return false;
    }
    match (parts.next(), parts.next()) {
        (None, None) => true,
        (Some(parameter), None) => parameter.split_once('=').is_some_and(|(name, value)| {
            name.trim().eq_ignore_ascii_case("charset")
                && value.trim().eq_ignore_ascii_case("utf-8")
        }),
        _ => false,
    }
}

fn valid_content_encoding(value: Option<&str>) -> bool {
    value.is_none_or(|encoding| encoding.eq_ignore_ascii_case("identity"))
}

fn valid_content_range(value: Option<&str>, row_count: usize) -> bool {
    matches!(
        (value, row_count),
        (None, _) | (Some("*/0"), 0) | (Some("0-0/*" | "0-0/1"), 1) | (Some("0-1/*" | "0-1/2"), 2)
    )
}

fn parse_canonical_uuid(value: &str) -> Option<Uuid> {
    let uuid = Uuid::parse_str(value).ok()?;
    (uuid.hyphenated().to_string() == value).then_some(uuid)
}

fn format_server_timestamp(now_ms: u64) -> Option<String> {
    let nanos = i128::from(now_ms).checked_mul(1_000_000)?;
    OffsetDateTime::from_unix_timestamp_nanos(nanos)
        .ok()?
        .format(&Rfc3339)
        .ok()
}

fn parse_timestamp_ms(value: &str) -> Option<u64> {
    let timestamp = OffsetDateTime::parse(value, &Rfc3339).ok()?;
    let nanos = timestamp.unix_timestamp_nanos();
    if nanos < 0 || nanos % 1_000_000 != 0 {
        return None;
    }
    u64::try_from(nanos / 1_000_000).ok()
}

struct CapabilityGrantDto {
    supabase_sub: String,
    capability: String,
    active: bool,
    revoked_at: Option<String>,
    expires_at: Option<String>,
}

impl CapabilityGrantDto {
    fn into_record(self, caller_uuid: Uuid, now_ms: u64) -> Option<CapabilityGrantRecord> {
        let returned_uuid = parse_canonical_uuid(&self.supabase_sub)?;
        if returned_uuid != caller_uuid
            || self.capability != HISTORICAL_AUDIT_CAPABILITY
            || !self.active
            || self.revoked_at.is_some()
        {
            return None;
        }
        let expires_at_ms = self
            .expires_at
            .as_deref()
            .map(parse_timestamp_ms)
            .transpose()?;
        if expires_at_ms.is_some_and(|expires_at| expires_at <= now_ms) {
            return None;
        }
        Some(CapabilityGrantRecord {
            supabase_sub: self.supabase_sub,
            capability: self.capability,
            active: self.active,
            revoked_at_ms: None,
            expires_at_ms,
        })
    }
}

trait OptionTranspose<T> {
    fn transpose(self) -> Option<Option<T>>;
}

impl<T> OptionTranspose<T> for Option<Option<T>> {
    fn transpose(self) -> Option<Option<T>> {
        match self {
            None => Some(None),
            Some(Some(value)) => Some(Some(value)),
            Some(None) => None,
        }
    }
}

impl<'de> Deserialize<'de> for CapabilityGrantDto {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_map(CapabilityGrantDtoVisitor)
    }
}

struct CapabilityGrantDtoVisitor;

impl<'de> Visitor<'de> for CapabilityGrantDtoVisitor {
    type Value = CapabilityGrantDto;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a strict capability grant row")
    }

    fn visit_map<M>(self, mut map: M) -> Result<Self::Value, M::Error>
    where
        M: MapAccess<'de>,
    {
        let mut supabase_sub = None;
        let mut capability = None;
        let mut active = None;
        let mut revoked_at = None;
        let mut expires_at = None;

        while let Some(key) = map.next_key::<String>()? {
            match key.as_str() {
                "supabase_sub" => {
                    if supabase_sub.is_some() {
                        return Err(de::Error::duplicate_field("supabase_sub"));
                    }
                    supabase_sub = Some(map.next_value()?);
                }
                "capability" => {
                    if capability.is_some() {
                        return Err(de::Error::duplicate_field("capability"));
                    }
                    capability = Some(map.next_value()?);
                }
                "active" => {
                    if active.is_some() {
                        return Err(de::Error::duplicate_field("active"));
                    }
                    active = Some(map.next_value()?);
                }
                "revoked_at" => {
                    if revoked_at.is_some() {
                        return Err(de::Error::duplicate_field("revoked_at"));
                    }
                    revoked_at = Some(map.next_value()?);
                }
                "expires_at" => {
                    if expires_at.is_some() {
                        return Err(de::Error::duplicate_field("expires_at"));
                    }
                    expires_at = Some(map.next_value()?);
                }
                _ => return Err(de::Error::unknown_field(&key, DTO_FIELDS)),
            }
        }

        Ok(CapabilityGrantDto {
            supabase_sub: supabase_sub.ok_or_else(|| de::Error::missing_field("supabase_sub"))?,
            capability: capability.ok_or_else(|| de::Error::missing_field("capability"))?,
            active: active.ok_or_else(|| de::Error::missing_field("active"))?,
            revoked_at: revoked_at.ok_or_else(|| de::Error::missing_field("revoked_at"))?,
            expires_at: expires_at.ok_or_else(|| de::Error::missing_field("expires_at"))?,
        })
    }
}

const DTO_FIELDS: &[&str] = &[
    "supabase_sub",
    "capability",
    "active",
    "revoked_at",
    "expires_at",
];

#[cfg(test)]
mod tests {
    use std::{
        collections::{HashMap, VecDeque},
        net::{Ipv6Addr, SocketAddr},
        sync::{
            atomic::{AtomicUsize, Ordering},
            Mutex,
        },
    };

    use serde_json::{json, Value};

    use super::*;

    const TEST_ORIGIN: &str = "https://aaaaaaaaaaaaaaaaaaaa.supabase.co";
    const TEST_SECRET: &str = "test";
    const CALLER: &str = "11111111-1111-4111-8111-111111111111";
    const OTHER_CALLER: &str = "22222222-2222-4222-8222-222222222222";
    const NOW_MS: u64 = 1_800_000_000_000;
    const FUTURE_TIMESTAMP: &str = "2027-01-15T09:00:00Z";

    struct CapturedRequest {
        path: String,
        query: Vec<(&'static str, String)>,
        header_sensitivity: Vec<(String, bool)>,
    }

    struct FakeTransport {
        responses: Mutex<VecDeque<Result<CapabilityGrantTransportResponse, TransportFailure>>>,
        requests: Mutex<Vec<CapturedRequest>>,
        attempts: AtomicUsize,
        completions: AtomicUsize,
        delay: Option<Duration>,
    }

    impl FakeTransport {
        fn new(
            responses: impl IntoIterator<
                Item = Result<CapabilityGrantTransportResponse, TransportFailure>,
            >,
        ) -> Self {
            Self {
                responses: Mutex::new(responses.into_iter().collect()),
                requests: Mutex::new(Vec::new()),
                attempts: AtomicUsize::new(0),
                completions: AtomicUsize::new(0),
                delay: None,
            }
        }

        fn delayed(response: CapabilityGrantTransportResponse, delay: Duration) -> Self {
            let mut transport = Self::new([Ok(response)]);
            transport.delay = Some(delay);
            transport
        }
    }

    impl CapabilityGrantTransport for FakeTransport {
        fn execute<'a>(&'a self, request: CapabilityGrantRequest) -> TransportFuture<'a> {
            self.attempts.fetch_add(1, Ordering::SeqCst);
            self.requests
                .lock()
                .expect("capture request")
                .push(CapturedRequest {
                    path: request.url.path().to_string(),
                    query: request.query,
                    header_sensitivity: request
                        .headers
                        .iter()
                        .map(|(name, value)| (name.as_str().to_string(), value.is_sensitive()))
                        .collect(),
                });
            let response = self
                .responses
                .lock()
                .expect("fake response queue")
                .pop_front()
                .unwrap_or(Err(TransportFailure::Unavailable));
            Box::pin(async move {
                if let Some(delay) = self.delay {
                    tokio::time::sleep(delay).await;
                }
                self.completions.fetch_add(1, Ordering::SeqCst);
                response
            })
        }
    }

    fn row(caller: &str) -> Value {
        json!({
            "supabase_sub": caller,
            "capability": HISTORICAL_AUDIT_CAPABILITY,
            "active": true,
            "revoked_at": null,
            "expires_at": FUTURE_TIMESTAMP
        })
    }

    fn response(status: StatusCode, body: Value) -> CapabilityGrantTransportResponse {
        let body = serde_json::to_vec(&body).expect("serialize synthetic response");
        CapabilityGrantTransportResponse {
            status,
            content_type: Some("application/json".to_string()),
            content_encoding: None,
            content_length: Some(body.len() as u64),
            content_range: None,
            headers_invalid: false,
            body,
            oversized: false,
        }
    }

    fn raw_response(body: &[u8]) -> CapabilityGrantTransportResponse {
        CapabilityGrantTransportResponse {
            status: StatusCode::OK,
            content_type: Some("application/json; charset=utf-8".to_string()),
            content_encoding: Some("identity".to_string()),
            content_length: Some(body.len() as u64),
            content_range: None,
            headers_invalid: false,
            body: body.to_vec(),
            oversized: false,
        }
    }

    fn response_with_headers(
        mut response: CapabilityGrantTransportResponse,
        headers: &HeaderMap,
    ) -> CapabilityGrantTransportResponse {
        let metadata = parse_response_headers(headers);
        response.content_type = metadata.content_type;
        response.content_encoding = metadata.content_encoding;
        response.content_length = metadata.content_length;
        response.content_range = metadata.content_range;
        response.headers_invalid = metadata.invalid;
        response
    }

    fn repository_with(
        transport: Arc<dyn CapabilityGrantTransport>,
        timeout_ms: u64,
    ) -> SupabaseCapabilityGrantRepository {
        SupabaseCapabilityGrantRepository::new(
            ValidatedSupabaseOrigin::parse(TEST_ORIGIN).expect("synthetic origin"),
            SecretServiceRoleKey::parse(TEST_SECRET).expect("synthetic secret"),
            CapabilityLookupTimeout::from_millis(timeout_ms).expect("test timeout"),
            transport,
        )
    }

    fn config(
        values: &[(&str, &str)],
    ) -> Result<CapabilityAdapterConfiguration, CapabilityGrantLookup> {
        let values: HashMap<&str, &str> = values.iter().copied().collect();
        CapabilityAdapterConfiguration::from_lookup(|key| {
            values.get(key).map(|value| value.to_string())
        })
    }

    #[test]
    fn production_source_mode_constant_is_available() {
        assert_eq!(
            HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_SUPABASE_GRANTS,
            "supabase_grants"
        );
    }

    #[test]
    fn configuration_defaults_to_unavailable_and_disabled() {
        let configured = config(&[]).expect("disabled defaults");
        assert!(matches!(
            configured,
            CapabilityAdapterConfiguration::Disabled
        ));
        assert_eq!(
            configured.source_mode(),
            HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_UNAVAILABLE
        );
    }

    #[test]
    fn valid_live_configuration_builds_dormant_adapter_without_network() {
        let configured = config(&[
            (SOURCE_ENV, "supabase_grants"),
            (ENABLED_ENV, "true"),
            (URL_ENV, TEST_ORIGIN),
            (SERVICE_ROLE_KEY_ENV, TEST_SECRET),
            (TIMEOUT_ENV, "750"),
        ])
        .expect("valid live configuration");
        assert_eq!(configured.source_mode(), "supabase_grants");
        let CapabilityAdapterConfiguration::Live(live) = configured else {
            panic!("expected live configuration")
        };
        let adapter = live.build().expect("build dormant client");
        assert_eq!(adapter.source_mode(), "supabase_grants");
    }

    #[test]
    fn invalid_configuration_variants_fail_closed() {
        let cases = [
            vec![(SOURCE_ENV, "unknown")],
            vec![(SOURCE_ENV, "unavailable"), (ENABLED_ENV, "true")],
            vec![(SOURCE_ENV, "supabase_grants"), (ENABLED_ENV, "false")],
            vec![(SOURCE_ENV, "supabase_grants"), (ENABLED_ENV, "maybe")],
            vec![(SOURCE_ENV, "supabase_grants"), (ENABLED_ENV, "true")],
            vec![
                (SOURCE_ENV, "supabase_grants"),
                (ENABLED_ENV, "true"),
                (URL_ENV, TEST_ORIGIN),
            ],
            vec![
                (SOURCE_ENV, "supabase_grants"),
                (ENABLED_ENV, "true"),
                (URL_ENV, TEST_ORIGIN),
                (SERVICE_ROLE_KEY_ENV, ""),
            ],
            vec![
                (SOURCE_ENV, "supabase_grants"),
                (ENABLED_ENV, "true"),
                (URL_ENV, TEST_ORIGIN),
                (SERVICE_ROLE_KEY_ENV, "placeholder"),
            ],
            vec![
                (SOURCE_ENV, "supabase_grants"),
                (ENABLED_ENV, "true"),
                (URL_ENV, TEST_ORIGIN),
                (SERVICE_ROLE_KEY_ENV, "line\nbreak"),
            ],
            vec![
                (SOURCE_ENV, "supabase_grants"),
                (ENABLED_ENV, "true"),
                (URL_ENV, TEST_ORIGIN),
                (SERVICE_ROLE_KEY_ENV, TEST_SECRET),
                (TIMEOUT_ENV, "invalid"),
            ],
            vec![
                (SOURCE_ENV, "supabase_grants"),
                (ENABLED_ENV, "true"),
                (URL_ENV, TEST_ORIGIN),
                (SERVICE_ROLE_KEY_ENV, TEST_SECRET),
                (TIMEOUT_ENV, "99"),
            ],
            vec![
                (SOURCE_ENV, "supabase_grants"),
                (ENABLED_ENV, "true"),
                (URL_ENV, TEST_ORIGIN),
                (SERVICE_ROLE_KEY_ENV, TEST_SECRET),
                (TIMEOUT_ENV, "2001"),
            ],
        ];
        for case in cases {
            assert!(matches!(
                config(&case),
                Err(CapabilityGrantLookup::Misconfigured)
            ));
        }
    }

    #[test]
    fn browser_url_fallback_is_not_consulted() {
        let mut consulted = Vec::new();
        let result = CapabilityAdapterConfiguration::from_lookup(|key| {
            consulted.push(key.to_string());
            None
        });
        assert!(matches!(
            result,
            Ok(CapabilityAdapterConfiguration::Disabled)
        ));
        assert!(!consulted.iter().any(|key| key.starts_with("VITE_")));
    }

    #[test]
    fn live_configuration_uses_bounded_default_timeout() {
        let configured = config(&[
            (SOURCE_ENV, "supabase_grants"),
            (ENABLED_ENV, "true"),
            (URL_ENV, TEST_ORIGIN),
            (SERVICE_ROLE_KEY_ENV, TEST_SECRET),
        ])
        .expect("live defaults");
        let CapabilityAdapterConfiguration::Live(live) = configured else {
            panic!("expected live configuration")
        };
        assert_eq!(live.timeout.0, Duration::from_millis(DEFAULT_TIMEOUT_MS));
    }

    #[test]
    fn url_validation_rejects_unsafe_origins_and_lookalikes() {
        let invalid = [
            "http://aaaaaaaaaaaaaaaaaaaa.supabase.co",
            "https://user@aaaaaaaaaaaaaaaaaaaa.supabase.co",
            "https://aaaaaaaaaaaaaaaaaaaa.supabase.co/path",
            "https://aaaaaaaaaaaaaaaaaaaa.supabase.co?query=value",
            "https://aaaaaaaaaaaaaaaaaaaa.supabase.co#fragment",
            "https://aaaaaaaaaaaaaaaaaaaa.supabase.co:444",
            "https://127.0.0.1",
            "https://localhost",
            "https://AAAAAAAAAAAAAAAAAAAA.supabase.co",
            "https://aaaaaaaaaaaaaaaaaaa.supabase.co",
            "https://aaaaaaaaaaaaaaaaaaaa.supabase.co.invalid",
            "https://aaaaaaaaaaaaaaaaaaaa.example.org",
        ];
        for origin in invalid {
            assert!(ValidatedSupabaseOrigin::parse(origin).is_err(), "{origin}");
        }
        assert!(ValidatedSupabaseOrigin::parse(TEST_ORIGIN).is_ok());
        assert!(ValidatedSupabaseOrigin::parse(&format!("{TEST_ORIGIN}:443")).is_ok());
    }

    #[test]
    fn dns_policy_rejects_private_reserved_and_mapped_destinations() {
        let rejected = [
            IpAddr::V4(Ipv4Addr::LOCALHOST),
            IpAddr::V4(Ipv4Addr::new(10, 0, 0, 1)),
            IpAddr::V4(Ipv4Addr::new(100, 64, 0, 1)),
            IpAddr::V4(Ipv4Addr::new(169, 254, 1, 1)),
            IpAddr::V4(Ipv4Addr::new(192, 0, 2, 1)),
            IpAddr::V4(Ipv4Addr::new(198, 18, 0, 1)),
            IpAddr::V6(Ipv6Addr::LOCALHOST),
            IpAddr::V6("3fff::1".parse().expect("reserved")),
            IpAddr::V6("3ffe::1".parse().expect("former 6bone")),
            IpAddr::V6("fc00::1".parse().expect("unique local")),
            IpAddr::V6("fe80::1".parse().expect("link local")),
            IpAddr::V6("::ffff:127.0.0.1".parse().expect("mapped loopback")),
            IpAddr::V6("2001:db8::1".parse().expect("documentation")),
        ];
        assert!(rejected
            .into_iter()
            .all(|address| !is_public_destination(address)));
        assert!(is_public_destination(IpAddr::V4(Ipv4Addr::new(8, 8, 8, 8))));
        assert!(!is_public_destination(IpAddr::V6(
            "2606:4700:4700::1111".parse().expect("public v6")
        )));
    }

    #[test]
    fn secret_debug_is_redacted_and_never_serialized() {
        let secret = SecretServiceRoleKey::parse(TEST_SECRET).expect("synthetic secret");
        let debug = format!("{secret:?}");
        assert_eq!(debug, "SecretServiceRoleKey([REDACTED])");
        assert!(!debug.contains(TEST_SECRET));
        let headers = secret.headers();
        assert!(headers.get(APIKEY).is_some_and(HeaderValue::is_sensitive));
        assert!(headers
            .get(AUTHORIZATION)
            .is_some_and(HeaderValue::is_sensitive));
        assert!(headers.get(ACCEPT).is_some_and(|value| {
            !value.is_sensitive() && value.as_bytes() == b"application/json"
        }));
        assert!(headers
            .get(ACCEPT_ENCODING)
            .is_some_and(|value| { !value.is_sensitive() && value.as_bytes() == b"identity" }));
    }

    #[tokio::test]
    async fn exact_request_contract_is_server_owned_and_single_attempt() {
        let transport = Arc::new(FakeTransport::new([Ok(response(
            StatusCode::OK,
            json!([row(CALLER)]),
        ))]));
        let repository = repository_with(transport.clone(), 750);
        let lookup = repository
            .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
            .await;
        assert!(matches!(lookup, CapabilityGrantLookup::Records(records) if records.len() == 1));
        assert_eq!(transport.attempts.load(Ordering::SeqCst), 1);

        let requests = transport.requests.lock().expect("captured requests");
        let request = &requests[0];
        assert_eq!(request.path, POSTGREST_RESOURCE_PATH);
        assert_eq!(
            request.query,
            vec![
                ("select", POSTGREST_PROJECTION.to_string()),
                ("supabase_sub", format!("eq.{CALLER}")),
                ("capability", "eq.historical_audit:read".to_string()),
                ("active", "eq.true".to_string()),
                ("revoked_at", "is.null".to_string()),
                (
                    "or",
                    "(expires_at.is.null,expires_at.gt.2027-01-15T08:00:00Z)".to_string(),
                ),
                ("limit", "2".to_string()),
            ]
        );
        assert_eq!(request.header_sensitivity.len(), 4);
        assert!(request
            .header_sensitivity
            .iter()
            .any(|(name, sensitive)| name == "apikey" && *sensitive));
        assert!(request
            .header_sensitivity
            .iter()
            .any(|(name, sensitive)| name == "authorization" && *sensitive));
        assert!(request
            .header_sensitivity
            .iter()
            .any(|(name, sensitive)| name == "accept" && !*sensitive));
        assert!(request
            .header_sensitivity
            .iter()
            .any(|(name, sensitive)| name == "accept-encoding" && !*sensitive));
        assert!(!request
            .header_sensitivity
            .iter()
            .any(|(name, _)| name == "range"));
        assert!(!request
            .header_sensitivity
            .iter()
            .any(|(name, _)| name == "cookie"));
    }

    #[tokio::test]
    async fn zero_one_and_two_rows_preserve_cardinality() {
        for count in 0..=2 {
            let rows: Vec<_> = (0..count).map(|_| row(CALLER)).collect();
            let transport = Arc::new(FakeTransport::new([Ok(response(
                StatusCode::OK,
                Value::Array(rows),
            ))]));
            let lookup = repository_with(transport, 750)
                .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
                .await;
            assert!(
                matches!(lookup, CapabilityGrantLookup::Records(records) if records.len() == count)
            );
        }
    }

    #[tokio::test]
    async fn repeated_lookups_have_no_positive_or_negative_cache() {
        let transport = Arc::new(FakeTransport::new([
            Ok(response(StatusCode::OK, json!([]))),
            Ok(response(StatusCode::OK, json!([row(CALLER)]))),
        ]));
        let repository = repository_with(transport.clone(), 750);
        assert!(matches!(
            repository
                .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
                .await,
            CapabilityGrantLookup::Records(records) if records.is_empty()
        ));
        assert!(matches!(
            repository
                .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
                .await,
            CapabilityGrantLookup::Records(records) if records.len() == 1
        ));
        assert_eq!(transport.attempts.load(Ordering::SeqCst), 2);
    }

    #[tokio::test]
    async fn invalid_caller_and_capability_never_reach_transport() {
        let transport = Arc::new(FakeTransport::new([]));
        let repository = repository_with(transport.clone(), 750);
        assert!(matches!(
            repository
                .lookup_grants("not-a-uuid", HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
                .await,
            CapabilityGrantLookup::Malformed
        ));
        assert!(matches!(
            repository.lookup_grants(CALLER, "admin", NOW_MS).await,
            CapabilityGrantLookup::Misconfigured
        ));
        assert_eq!(transport.attempts.load(Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn source_mode_is_stable_for_every_transport_failure() {
        for failure in [
            TransportFailure::Unavailable,
            TransportFailure::Timeout,
            TransportFailure::Malformed,
        ] {
            let transport = Arc::new(FakeTransport::new([Err(failure)]));
            let repository = repository_with(transport, 750);
            let _ = repository
                .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
                .await;
            assert_eq!(repository.source_mode(), "supabase_grants");
        }
    }

    #[tokio::test]
    async fn http_statuses_map_to_safe_categories_without_body_propagation() {
        let cases = [
            (
                StatusCode::BAD_REQUEST,
                CapabilityGrantLookup::Misconfigured,
            ),
            (StatusCode::UNAUTHORIZED, CapabilityGrantLookup::Forbidden),
            (StatusCode::FORBIDDEN, CapabilityGrantLookup::Forbidden),
            (StatusCode::NOT_FOUND, CapabilityGrantLookup::Misconfigured),
            (StatusCode::REQUEST_TIMEOUT, CapabilityGrantLookup::Timeout),
            (
                StatusCode::TOO_MANY_REQUESTS,
                CapabilityGrantLookup::Unavailable,
            ),
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                CapabilityGrantLookup::Unavailable,
            ),
            (StatusCode::BAD_GATEWAY, CapabilityGrantLookup::Unavailable),
            (
                StatusCode::SERVICE_UNAVAILABLE,
                CapabilityGrantLookup::Unavailable,
            ),
            (
                StatusCode::GATEWAY_TIMEOUT,
                CapabilityGrantLookup::Unavailable,
            ),
            (StatusCode::NO_CONTENT, CapabilityGrantLookup::Malformed),
            (StatusCode::FOUND, CapabilityGrantLookup::Malformed),
        ];
        for (status, expected) in cases {
            let transport = Arc::new(FakeTransport::new([Ok(response(
                status,
                json!({"private": "discarded"}),
            ))]));
            let actual = repository_with(transport, 750)
                .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
                .await;
            assert_eq!(actual, expected);
        }
    }

    #[tokio::test]
    async fn malformed_response_matrix_fails_closed() {
        let mut cases = vec![
            raw_response(b"not-json"),
            raw_response(b"[{"),
            raw_response(br#"{"not":"an-array"}"#),
            raw_response(b"null"),
            raw_response(br#"[null]"#),
            raw_response(format!("[{}, {}, {}]", row(CALLER), row(CALLER), row(CALLER)).as_bytes()),
            raw_response(
                format!(
                    "[{{\"supabase_sub\":\"{CALLER}\",\"capability\":\"historical_audit:read\",\"active\":true,\"revoked_at\":null}}]"
                )
                .as_bytes(),
            ),
            raw_response(
                format!(
                    "[{{\"supabase_sub\":\"{CALLER}\",\"capability\":\"historical_audit:read\",\"active\":true,\"revoked_at\":null,\"expires_at\":null,\"extra\":true}}]"
                )
                .as_bytes(),
            ),
            raw_response(
                format!(
                    "[{{\"supabase_sub\":\"{CALLER}\",\"supabase_sub\":\"{CALLER}\",\"capability\":\"historical_audit:read\",\"active\":true,\"revoked_at\":null,\"expires_at\":null}}]"
                )
                .as_bytes(),
            ),
            response(StatusCode::OK, json!([row(OTHER_CALLER)])),
            response(StatusCode::OK, json!([{ "supabase_sub": "invalid", "capability": HISTORICAL_AUDIT_CAPABILITY, "active": true, "revoked_at": null, "expires_at": null }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": "admin", "active": true, "revoked_at": null, "expires_at": null }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": false, "revoked_at": null, "expires_at": null }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": "true", "revoked_at": null, "expires_at": null }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": null, "revoked_at": null, "expires_at": null }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": true, "revoked_at": "2027-01-01T00:00:00Z", "expires_at": null }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": true, "revoked_at": false, "expires_at": null }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": true, "revoked_at": null, "expires_at": "invalid" }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": true, "revoked_at": null, "expires_at": "2027-01-15T09:00:00" }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": true, "revoked_at": null, "expires_at": "1969-01-01T00:00:00Z" }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": true, "revoked_at": null, "expires_at": "2027-01-15T08:00:00Z" }])),
            response(StatusCode::OK, json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": true, "revoked_at": null, "expires_at": "2027-01-15T08:00:00.000001Z" }])),
        ];

        let mut missing_content_type = response(StatusCode::OK, json!([]));
        missing_content_type.content_type = None;
        cases.push(missing_content_type);
        let mut invalid_content_type = response(StatusCode::OK, json!([]));
        invalid_content_type.content_type = Some("text/plain".to_string());
        cases.push(invalid_content_type);
        let mut unsupported_encoding = response(StatusCode::OK, json!([]));
        unsupported_encoding.content_encoding = Some("gzip".to_string());
        cases.push(unsupported_encoding);
        let mut invalid_headers = response(StatusCode::OK, json!([]));
        invalid_headers.headers_invalid = true;
        cases.push(invalid_headers);
        let mut wrong_length = response(StatusCode::OK, json!([]));
        wrong_length.content_length = Some(999);
        cases.push(wrong_length);
        let mut oversized = response(StatusCode::OK, json!([]));
        oversized.oversized = true;
        cases.push(oversized);
        cases.push(raw_response(&vec![b' '; MAX_RESPONSE_BODY_BYTES + 1]));
        let mut invalid_range = response(StatusCode::OK, json!([row(CALLER)]));
        invalid_range.content_range = Some("1-1/*".to_string());
        cases.push(invalid_range);

        for response in cases {
            let transport = Arc::new(FakeTransport::new([Ok(response)]));
            let actual = repository_with(transport, 750)
                .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
                .await;
            assert!(matches!(actual, CapabilityGrantLookup::Malformed));
        }
    }

    #[tokio::test]
    async fn nullable_and_offset_timestamps_parse_losslessly() {
        let null_expiry = response(
            StatusCode::OK,
            json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": true, "revoked_at": null, "expires_at": null }]),
        );
        let offset_expiry = response(
            StatusCode::OK,
            json!([{ "supabase_sub": CALLER, "capability": HISTORICAL_AUDIT_CAPABILITY, "active": true, "revoked_at": null, "expires_at": "2027-01-15T06:00:00-03:00" }]),
        );
        let transport = Arc::new(FakeTransport::new([Ok(null_expiry), Ok(offset_expiry)]));
        let repository = repository_with(transport, 750);
        let first = repository
            .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
            .await;
        let second = repository
            .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
            .await;
        assert!(
            matches!(first, CapabilityGrantLookup::Records(records) if records[0].expires_at_ms.is_none())
        );
        assert!(
            matches!(second, CapabilityGrantLookup::Records(records) if records[0].expires_at_ms == Some(1_800_003_600_000))
        );
    }

    #[tokio::test]
    async fn timeout_cancels_single_attempt_without_detached_completion() {
        let transport = Arc::new(FakeTransport::delayed(
            response(StatusCode::OK, json!([row(CALLER)])),
            Duration::from_millis(500),
        ));
        let repository = repository_with(transport.clone(), 100);
        let lookup = repository
            .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
            .await;
        assert!(matches!(lookup, CapabilityGrantLookup::Timeout));
        tokio::task::yield_now().await;
        assert_eq!(transport.attempts.load(Ordering::SeqCst), 1);
        assert_eq!(transport.completions.load(Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn transport_failures_are_categorical_and_redacted() {
        for (failure, expected) in [
            (
                TransportFailure::Unavailable,
                CapabilityGrantLookup::Unavailable,
            ),
            (TransportFailure::Timeout, CapabilityGrantLookup::Timeout),
            (
                TransportFailure::Malformed,
                CapabilityGrantLookup::Malformed,
            ),
        ] {
            let transport = Arc::new(FakeTransport::new([Err(failure)]));
            let repository = repository_with(transport.clone(), 750);
            let lookup = repository
                .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
                .await;
            assert_eq!(lookup, expected);
            assert_eq!(transport.attempts.load(Ordering::SeqCst), 1);
            let debug = format!("{repository:?}");
            assert!(!debug.contains(TEST_SECRET));
            assert!(!debug.contains("supabase.co"));
            assert!(!debug.contains(CALLER));
        }
    }

    #[test]
    fn content_type_and_range_contracts_are_strict() {
        assert!(valid_json_content_type(Some("application/json")));
        assert!(valid_json_content_type(Some(
            "Application/JSON; Charset=UTF-8"
        )));
        assert!(!valid_json_content_type(Some(
            "application/json; charset=utf-8; extra=x"
        )));
        assert!(!valid_json_content_type(Some(
            "application/vnd.pgrst.object+json"
        )));
        assert!(valid_content_range(Some("*/0"), 0));
        assert!(valid_content_range(Some("0-0/*"), 1));
        assert!(valid_content_range(Some("0-0/1"), 1));
        assert!(valid_content_range(Some("0-1/*"), 2));
        assert!(valid_content_range(Some("0-1/2"), 2));
        assert!(!valid_content_range(Some("0-0/2"), 1));
        assert!(!valid_content_range(Some("0-1/3"), 2));
        assert!(!valid_content_range(Some("0-2/*"), 2));
    }

    #[tokio::test]
    async fn content_range_rejects_partial_effective_grant_responses() {
        let cases = [
            (vec![row(CALLER)], "0-0/2", false),
            (vec![row(CALLER), row(CALLER)], "0-1/3", false),
            (vec![row(CALLER)], "0-0/1", true),
            (vec![row(CALLER), row(CALLER)], "0-1/2", true),
            (vec![row(CALLER)], "0-0/*", true),
            (vec![row(CALLER), row(CALLER)], "0-1/*", true),
        ];
        for (rows, content_range, valid) in cases {
            let mut transport_response = response(StatusCode::OK, Value::Array(rows));
            transport_response.content_range = Some(content_range.to_string());
            let transport = Arc::new(FakeTransport::new([Ok(transport_response)]));
            let lookup = repository_with(transport, 750)
                .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
                .await;
            if valid {
                assert!(matches!(lookup, CapabilityGrantLookup::Records(_)));
            } else {
                assert!(matches!(lookup, CapabilityGrantLookup::Malformed));
            }
        }
    }

    #[tokio::test]
    async fn duplicate_conflicting_and_invalid_response_headers_are_malformed() {
        let mut cases = Vec::new();

        let mut duplicate_content_type = HeaderMap::new();
        duplicate_content_type.append(CONTENT_TYPE, HeaderValue::from_static("application/json"));
        duplicate_content_type.append(CONTENT_TYPE, HeaderValue::from_static("application/json"));
        cases.push(duplicate_content_type);

        let mut duplicate_encoding = HeaderMap::new();
        duplicate_encoding.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
        duplicate_encoding.append(CONTENT_ENCODING, HeaderValue::from_static("identity"));
        duplicate_encoding.append(CONTENT_ENCODING, HeaderValue::from_static("identity"));
        cases.push(duplicate_encoding);

        let mut conflicting_length = HeaderMap::new();
        conflicting_length.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
        conflicting_length.append(CONTENT_LENGTH, HeaderValue::from_static("2"));
        conflicting_length.append(CONTENT_LENGTH, HeaderValue::from_static("3"));
        cases.push(conflicting_length);

        let mut conflicting_range = HeaderMap::new();
        conflicting_range.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
        conflicting_range.append(CONTENT_RANGE, HeaderValue::from_static("*/0"));
        conflicting_range.append(CONTENT_RANGE, HeaderValue::from_static("0-0/*"));
        cases.push(conflicting_range);

        let mut invalid_bytes = HeaderMap::new();
        invalid_bytes.insert(
            CONTENT_TYPE,
            HeaderValue::from_bytes(b"\xff").expect("opaque header"),
        );
        cases.push(invalid_bytes);

        for headers in cases {
            let transport_response =
                response_with_headers(response(StatusCode::OK, json!([])), &headers);
            assert!(transport_response.headers_invalid);
            let transport = Arc::new(FakeTransport::new([Ok(transport_response)]));
            let lookup = repository_with(transport, 750)
                .lookup_grants(CALLER, HISTORICAL_AUDIT_CAPABILITY, NOW_MS)
                .await;
            assert!(matches!(lookup, CapabilityGrantLookup::Malformed));
        }
    }

    #[test]
    fn resolver_defense_in_depth_records_remain_representable() {
        let records = [
            CapabilityGrantRecord {
                supabase_sub: CALLER.to_string(),
                capability: HISTORICAL_AUDIT_CAPABILITY.to_string(),
                active: false,
                revoked_at_ms: None,
                expires_at_ms: None,
            },
            CapabilityGrantRecord {
                supabase_sub: CALLER.to_string(),
                capability: HISTORICAL_AUDIT_CAPABILITY.to_string(),
                active: true,
                revoked_at_ms: Some(NOW_MS),
                expires_at_ms: None,
            },
            CapabilityGrantRecord {
                supabase_sub: CALLER.to_string(),
                capability: HISTORICAL_AUDIT_CAPABILITY.to_string(),
                active: true,
                revoked_at_ms: None,
                expires_at_ms: Some(NOW_MS),
            },
        ];
        assert_eq!(records.len(), 3);
    }

    #[test]
    fn no_caller_jwt_or_public_configuration_name_exists_in_request_contract() {
        let forbidden = ["VITE_SUPABASE_URL", "anon", "caller_jwt", "Range"];
        let contract = format!(
            "{SOURCE_ENV} {URL_ENV} {SERVICE_ROLE_KEY_ENV} {TIMEOUT_ENV} {ENABLED_ENV} {POSTGREST_RESOURCE_PATH} {POSTGREST_PROJECTION}"
        );
        assert!(forbidden.iter().all(|value| !contract.contains(value)));
    }

    #[test]
    fn ip_policy_accepts_only_public_socket_destinations() {
        let safe = SocketAddr::new(IpAddr::V4(Ipv4Addr::new(1, 1, 1, 1)), 443);
        let unsafe_address = SocketAddr::new(IpAddr::V4(Ipv4Addr::new(127, 0, 0, 1)), 443);
        assert!(is_public_destination(safe.ip()));
        assert!(!is_public_destination(unsafe_address.ip()));
    }
}
