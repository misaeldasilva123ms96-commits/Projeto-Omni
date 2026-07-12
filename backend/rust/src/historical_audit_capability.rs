#[cfg(test)]
use std::collections::HashSet;
use std::{
    sync::Arc,
    time::{SystemTime, UNIX_EPOCH},
};

#[cfg(test)]
pub(crate) const HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_SUPABASE_GRANTS: &str = "supabase_grants";
#[cfg(test)]
pub(crate) const HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_STATIC_TEST: &str = "static_test";
pub(crate) const HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_UNAVAILABLE: &str = "unavailable";

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct CapabilityDecision {
    pub(crate) allowed: bool,
    pub(crate) reason: &'static str,
    pub(crate) source_mode: &'static str,
}

impl CapabilityDecision {
    fn allow(source_mode: &'static str) -> Self {
        Self {
            allowed: true,
            reason: "historical_audit_readonly_authorized",
            source_mode,
        }
    }

    fn deny(reason: &'static str, source_mode: &'static str) -> Self {
        Self {
            allowed: false,
            reason,
            source_mode,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct CapabilityGrantRecord {
    pub(crate) supabase_sub: String,
    pub(crate) capability: String,
    pub(crate) active: bool,
    pub(crate) revoked_at_ms: Option<u64>,
    pub(crate) expires_at_ms: Option<u64>,
}

impl CapabilityGrantRecord {
    #[cfg(test)]
    pub(crate) fn active_grant(supabase_sub: &str, capability: &str) -> Self {
        Self {
            supabase_sub: supabase_sub.to_string(),
            capability: capability.to_string(),
            active: true,
            revoked_at_ms: None,
            expires_at_ms: None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
#[allow(dead_code)]
pub(crate) enum CapabilityGrantLookup {
    Records(Vec<CapabilityGrantRecord>),
    Unavailable,
    Timeout,
    Misconfigured,
    Forbidden,
}

pub(crate) trait CapabilityGrantRepository: Send + Sync {
    fn source_mode(&self) -> &'static str;

    fn lookup_grants(
        &self,
        caller_sub: &str,
        capability: &str,
        now_ms: u64,
    ) -> CapabilityGrantLookup;
}

pub(crate) struct UnavailableCapabilityGrantRepository {
    reason: CapabilityGrantLookup,
}

impl UnavailableCapabilityGrantRepository {
    pub(crate) fn misconfigured() -> Self {
        Self {
            reason: CapabilityGrantLookup::Misconfigured,
        }
    }
}

impl CapabilityGrantRepository for UnavailableCapabilityGrantRepository {
    fn source_mode(&self) -> &'static str {
        HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_UNAVAILABLE
    }

    fn lookup_grants(
        &self,
        _caller_sub: &str,
        _capability: &str,
        _now_ms: u64,
    ) -> CapabilityGrantLookup {
        self.reason.clone()
    }
}

#[derive(Clone)]
pub(crate) struct HistoricalAuditCapabilityResolver {
    repository: Arc<dyn CapabilityGrantRepository>,
    required_capability: &'static str,
}

impl HistoricalAuditCapabilityResolver {
    pub(crate) fn new(
        repository: Arc<dyn CapabilityGrantRepository>,
        required_capability: &'static str,
    ) -> Self {
        Self {
            repository,
            required_capability,
        }
    }

    pub(crate) fn unavailable(required_capability: &'static str) -> Self {
        Self::new(
            Arc::new(UnavailableCapabilityGrantRepository::misconfigured()),
            required_capability,
        )
    }

    pub(crate) fn authorize(&self, caller_sub: &str) -> CapabilityDecision {
        self.authorize_at(caller_sub, now_ms())
    }

    pub(crate) fn authorize_at(&self, caller_sub: &str, now_ms: u64) -> CapabilityDecision {
        let source_mode = self.repository.source_mode();
        if !is_safe_supabase_sub(caller_sub) {
            return CapabilityDecision::deny("invalid_caller_identity", source_mode);
        }
        if self.required_capability != "historical_audit:read" {
            return CapabilityDecision::deny("capability_source_misconfigured", source_mode);
        }

        match self
            .repository
            .lookup_grants(caller_sub, self.required_capability, now_ms)
        {
            CapabilityGrantLookup::Records(records) => {
                self.evaluate_records(caller_sub, records, now_ms, source_mode)
            }
            CapabilityGrantLookup::Unavailable => {
                CapabilityDecision::deny("capability_source_unavailable", source_mode)
            }
            CapabilityGrantLookup::Timeout => {
                CapabilityDecision::deny("capability_source_timeout", source_mode)
            }
            CapabilityGrantLookup::Misconfigured => {
                CapabilityDecision::deny("capability_source_misconfigured", source_mode)
            }
            CapabilityGrantLookup::Forbidden => {
                CapabilityDecision::deny("capability_source_forbidden", source_mode)
            }
        }
    }

    fn evaluate_records(
        &self,
        caller_sub: &str,
        records: Vec<CapabilityGrantRecord>,
        now_ms: u64,
        source_mode: &'static str,
    ) -> CapabilityDecision {
        if records.is_empty() {
            return CapabilityDecision::deny(
                "missing_historical_audit_readonly_capability",
                source_mode,
            );
        }

        let mut effective_grants = 0usize;
        let mut saw_revoked = false;
        let mut saw_expired = false;

        for record in records {
            if !is_safe_supabase_sub(&record.supabase_sub)
                || record.supabase_sub != caller_sub
                || record.capability != self.required_capability
            {
                return CapabilityDecision::deny("malformed_capability_grant", source_mode);
            }
            if record.revoked_at_ms.is_some() {
                saw_revoked = true;
                continue;
            }
            if record
                .expires_at_ms
                .map(|expires_at| expires_at <= now_ms)
                .unwrap_or(false)
            {
                saw_expired = true;
                continue;
            }
            if !record.active {
                continue;
            }
            effective_grants += 1;
        }

        match effective_grants {
            1 => CapabilityDecision::allow(source_mode),
            count if count > 1 => {
                CapabilityDecision::deny("duplicate_capability_grant", source_mode)
            }
            _ if saw_revoked => CapabilityDecision::deny(
                "revoked_historical_audit_readonly_capability",
                source_mode,
            ),
            _ if saw_expired => CapabilityDecision::deny(
                "expired_historical_audit_readonly_capability",
                source_mode,
            ),
            _ => CapabilityDecision::deny(
                "missing_historical_audit_readonly_capability",
                source_mode,
            ),
        }
    }
}

#[cfg(test)]
pub(crate) struct StaticTestCapabilityGrantRepository {
    authorized_callers: HashSet<String>,
}

#[cfg(test)]
impl StaticTestCapabilityGrantRepository {
    pub(crate) fn new(callers: &[&str]) -> Self {
        Self {
            authorized_callers: callers.iter().map(|caller| (*caller).to_string()).collect(),
        }
    }
}

#[cfg(test)]
impl CapabilityGrantRepository for StaticTestCapabilityGrantRepository {
    fn source_mode(&self) -> &'static str {
        HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_STATIC_TEST
    }

    fn lookup_grants(
        &self,
        caller_sub: &str,
        capability: &str,
        _now_ms: u64,
    ) -> CapabilityGrantLookup {
        if self.authorized_callers.contains(caller_sub) {
            CapabilityGrantLookup::Records(vec![CapabilityGrantRecord::active_grant(
                caller_sub, capability,
            )])
        } else {
            CapabilityGrantLookup::Records(vec![])
        }
    }
}

fn is_safe_supabase_sub(value: &str) -> bool {
    if value.is_empty() || value.len() > 128 {
        return false;
    }
    value
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '_' | '-' | '.' | ':' | '+'))
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis() as u64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    struct TestGrantRepository {
        source_mode: &'static str,
        lookup: CapabilityGrantLookup,
    }

    impl CapabilityGrantRepository for TestGrantRepository {
        fn source_mode(&self) -> &'static str {
            self.source_mode
        }

        fn lookup_grants(
            &self,
            _caller_sub: &str,
            _capability: &str,
            _now_ms: u64,
        ) -> CapabilityGrantLookup {
            self.lookup.clone()
        }
    }

    fn resolver(lookup: CapabilityGrantLookup) -> HistoricalAuditCapabilityResolver {
        HistoricalAuditCapabilityResolver::new(
            Arc::new(TestGrantRepository {
                source_mode: HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_SUPABASE_GRANTS,
                lookup,
            }),
            "historical_audit:read",
        )
    }

    fn revoked_grant() -> CapabilityGrantRecord {
        let mut grant =
            CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read");
        grant.active = false;
        grant.revoked_at_ms = Some(900);
        grant
    }

    fn expired_grant() -> CapabilityGrantRecord {
        let mut grant =
            CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read");
        grant.expires_at_ms = Some(999);
        grant
    }

    fn inactive_grant() -> CapabilityGrantRecord {
        let mut grant =
            CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read");
        grant.active = false;
        grant
    }

    #[test]
    fn capability_resolver_allows_only_exact_active_server_side_grant() {
        let decision = resolver(CapabilityGrantLookup::Records(vec![
            CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read"),
        ]))
        .authorize_at("operator-123", 1_000);

        assert!(decision.allowed);
        assert_eq!(decision.reason, "historical_audit_readonly_authorized");
        assert_eq!(
            decision.source_mode,
            HISTORICAL_AUDIT_CAPABILITY_SOURCE_MODE_SUPABASE_GRANTS
        );
    }

    #[test]
    fn capability_resolver_denies_missing_or_invalid_caller() {
        let decision = resolver(CapabilityGrantLookup::Records(vec![])).authorize_at("", 1_000);

        assert!(!decision.allowed);
        assert_eq!(decision.reason, "invalid_caller_identity");
    }

    #[test]
    fn capability_resolver_denies_missing_grant() {
        let decision =
            resolver(CapabilityGrantLookup::Records(vec![])).authorize_at("operator-123", 1_000);

        assert!(!decision.allowed);
        assert_eq!(
            decision.reason,
            "missing_historical_audit_readonly_capability"
        );
    }

    #[test]
    fn capability_resolver_denies_revoked_expired_inactive_and_duplicate_grants() {
        assert_eq!(
            resolver(CapabilityGrantLookup::Records(vec![revoked_grant()]))
                .authorize_at("operator-123", 1_000)
                .reason,
            "revoked_historical_audit_readonly_capability"
        );

        assert_eq!(
            resolver(CapabilityGrantLookup::Records(vec![expired_grant()]))
                .authorize_at("operator-123", 1_000)
                .reason,
            "expired_historical_audit_readonly_capability"
        );

        assert_eq!(
            resolver(CapabilityGrantLookup::Records(vec![inactive_grant()]))
                .authorize_at("operator-123", 1_000)
                .reason,
            "missing_historical_audit_readonly_capability"
        );

        assert_eq!(
            resolver(CapabilityGrantLookup::Records(vec![
                CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read"),
                CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read"),
            ]))
            .authorize_at("operator-123", 1_000)
            .reason,
            "duplicate_capability_grant"
        );
    }

    #[test]
    fn capability_resolver_allows_active_grant_with_expired_historical_grant() {
        let decision = resolver(CapabilityGrantLookup::Records(vec![
            CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read"),
            expired_grant(),
        ]))
        .authorize_at("operator-123", 1_000);

        assert!(decision.allowed);
        assert_eq!(decision.reason, "historical_audit_readonly_authorized");
    }

    #[test]
    fn capability_resolver_allows_active_grant_with_revoked_historical_grant() {
        let decision = resolver(CapabilityGrantLookup::Records(vec![
            CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read"),
            revoked_grant(),
        ]))
        .authorize_at("operator-123", 1_000);

        assert!(decision.allowed);
        assert_eq!(decision.reason, "historical_audit_readonly_authorized");
    }

    #[test]
    fn capability_resolver_allows_active_grant_with_inactive_historical_grant() {
        let decision = resolver(CapabilityGrantLookup::Records(vec![
            CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read"),
            inactive_grant(),
        ]))
        .authorize_at("operator-123", 1_000);

        assert!(decision.allowed);
        assert_eq!(decision.reason, "historical_audit_readonly_authorized");
    }

    #[test]
    fn capability_resolver_denies_two_effective_active_grants() {
        let decision = resolver(CapabilityGrantLookup::Records(vec![
            CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read"),
            CapabilityGrantRecord::active_grant("operator-123", "historical_audit:read"),
        ]))
        .authorize_at("operator-123", 1_000);

        assert!(!decision.allowed);
        assert_eq!(decision.reason, "duplicate_capability_grant");
    }

    #[test]
    fn capability_resolver_denies_only_expired_grants() {
        let decision = resolver(CapabilityGrantLookup::Records(vec![expired_grant()]))
            .authorize_at("operator-123", 1_000);

        assert!(!decision.allowed);
        assert_eq!(
            decision.reason,
            "expired_historical_audit_readonly_capability"
        );
    }

    #[test]
    fn capability_resolver_denies_only_revoked_grants() {
        let decision = resolver(CapabilityGrantLookup::Records(vec![revoked_grant()]))
            .authorize_at("operator-123", 1_000);

        assert!(!decision.allowed);
        assert_eq!(
            decision.reason,
            "revoked_historical_audit_readonly_capability"
        );
    }

    #[test]
    fn capability_resolver_denies_malformed_wrong_capability_and_source_failures() {
        assert_eq!(
            resolver(CapabilityGrantLookup::Records(vec![
                CapabilityGrantRecord::active_grant("operator-123", "admin")
            ]))
            .authorize_at("operator-123", 1_000)
            .reason,
            "malformed_capability_grant"
        );
        assert_eq!(
            resolver(CapabilityGrantLookup::Unavailable)
                .authorize_at("operator-123", 1_000)
                .reason,
            "capability_source_unavailable"
        );
        assert_eq!(
            resolver(CapabilityGrantLookup::Timeout)
                .authorize_at("operator-123", 1_000)
                .reason,
            "capability_source_timeout"
        );
        assert_eq!(
            resolver(CapabilityGrantLookup::Misconfigured)
                .authorize_at("operator-123", 1_000)
                .reason,
            "capability_source_misconfigured"
        );
        assert_eq!(
            resolver(CapabilityGrantLookup::Forbidden)
                .authorize_at("operator-123", 1_000)
                .reason,
            "capability_source_forbidden"
        );
    }

    #[test]
    fn static_grants_exist_only_for_isolated_tests() {
        let resolver = HistoricalAuditCapabilityResolver::new(
            Arc::new(StaticTestCapabilityGrantRepository::new(&["operator-123"])),
            "historical_audit:read",
        );

        assert!(resolver.authorize_at("operator-123", 1_000).allowed);
        assert_eq!(
            resolver.authorize_at("operator-456", 1_000).reason,
            "missing_historical_audit_readonly_capability"
        );
    }
}
