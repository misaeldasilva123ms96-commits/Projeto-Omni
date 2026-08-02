use std::net::IpAddr;

use axum::http::HeaderMap;
use ipnet::IpNet;

pub(crate) const MAX_FORWARDED_HEADER_BYTES: usize = 8_192;
pub(crate) const DEFAULT_TRUST_PROXY_MAX_HOPS: usize = 8;
pub(crate) const MAX_TRUST_PROXY_HOPS: usize = 64;

#[derive(Debug, Clone)]
pub(crate) struct TrustedProxyConfig {
    trust_forwarded_headers: bool,
    trusted_networks: Vec<IpNet>,
    max_hops: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum ClientIdentitySource {
    DirectPeer,
    TrustedForwardedChain,
    ForwardedHeaderRejected,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct ClientIdentity {
    pub(crate) effective_ip: IpAddr,
    pub(crate) source: ClientIdentitySource,
}

impl TrustedProxyConfig {
    pub(crate) fn parse(
        trust_forwarded_headers: bool,
        raw_trusted_networks: &str,
        max_hops: usize,
    ) -> Result<Self, &'static str> {
        if !(1..=MAX_TRUST_PROXY_HOPS).contains(&max_hops) {
            return Err("OMNI_TRUST_PROXY_MAX_HOPS is outside the accepted range");
        }

        let mut trusted_networks = Vec::new();
        if !raw_trusted_networks.trim().is_empty() {
            for entry in raw_trusted_networks.split(',').map(str::trim) {
                if entry.is_empty() {
                    return Err("OMNI_TRUSTED_PROXY_CIDRS contains an empty entry");
                }
                let network = parse_network(entry)?;
                if network.prefix_len() == 0 {
                    return Err("OMNI_TRUSTED_PROXY_CIDRS contains a blanket network");
                }
                trusted_networks.push(network);
            }
        }

        if trust_forwarded_headers && trusted_networks.is_empty() {
            return Err("OMNI_TRUSTED_PROXY_CIDRS is required when proxy trust is enabled");
        }

        Ok(Self {
            trust_forwarded_headers,
            trusted_networks,
            max_hops,
        })
    }

    #[cfg(test)]
    pub(crate) fn direct_only() -> Self {
        Self {
            trust_forwarded_headers: false,
            trusted_networks: Vec::new(),
            max_hops: DEFAULT_TRUST_PROXY_MAX_HOPS,
        }
    }

    pub(crate) fn resolve(&self, peer_ip: IpAddr, headers: &HeaderMap) -> ClientIdentity {
        let peer_ip = normalize_ip(peer_ip);
        if !self.trust_forwarded_headers || !self.is_trusted(peer_ip) {
            return ClientIdentity {
                effective_ip: peer_ip,
                source: ClientIdentitySource::DirectPeer,
            };
        }

        match self.parse_forwarded_chain(headers) {
            Some(chain) => chain
                .into_iter()
                .rev()
                .find(|candidate| !self.is_trusted(*candidate))
                .map(|effective_ip| ClientIdentity {
                    effective_ip,
                    source: ClientIdentitySource::TrustedForwardedChain,
                })
                .unwrap_or(ClientIdentity {
                    effective_ip: peer_ip,
                    source: ClientIdentitySource::ForwardedHeaderRejected,
                }),
            None => ClientIdentity {
                effective_ip: peer_ip,
                source: ClientIdentitySource::ForwardedHeaderRejected,
            },
        }
    }

    fn is_trusted(&self, ip: IpAddr) -> bool {
        self.trusted_networks
            .iter()
            .any(|network| network.contains(&ip))
    }

    fn parse_forwarded_chain(&self, headers: &HeaderMap) -> Option<Vec<IpAddr>> {
        let mut total_bytes = 0usize;
        let mut chain = Vec::new();
        let mut saw_header = false;

        for value in headers.get_all("x-forwarded-for") {
            saw_header = true;
            total_bytes = total_bytes.checked_add(value.as_bytes().len())?;
            if total_bytes > MAX_FORWARDED_HEADER_BYTES {
                return None;
            }
            let raw = value.to_str().ok()?;
            for element in raw.split(',') {
                let element = element.trim();
                if element.is_empty() {
                    return None;
                }
                chain.push(normalize_ip(element.parse::<IpAddr>().ok()?));
                if chain.len() > self.max_hops {
                    return None;
                }
            }
        }

        if !saw_header || chain.is_empty() {
            None
        } else {
            Some(chain)
        }
    }
}

fn parse_network(raw: &str) -> Result<IpNet, &'static str> {
    if raw.contains('/') {
        raw.parse::<IpNet>()
            .map_err(|_| "OMNI_TRUSTED_PROXY_CIDRS contains an invalid network")
    } else {
        raw.parse::<IpAddr>()
            .map(normalize_ip)
            .map(IpNet::from)
            .map_err(|_| "OMNI_TRUSTED_PROXY_CIDRS contains an invalid address")
    }
}

pub(crate) fn normalize_ip(ip: IpAddr) -> IpAddr {
    match ip {
        IpAddr::V6(value) => value
            .to_ipv4_mapped()
            .map(IpAddr::V4)
            .unwrap_or(IpAddr::V6(value)),
        IpAddr::V4(value) => IpAddr::V4(value),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::HeaderValue;
    use std::net::Ipv4Addr;

    fn trusted_config(raw: &str, max_hops: usize) -> TrustedProxyConfig {
        TrustedProxyConfig::parse(true, raw, max_hops).expect("valid trusted proxy config")
    }

    fn headers(values: &[&str]) -> HeaderMap {
        let mut headers = HeaderMap::new();
        for value in values {
            headers.append(
                "x-forwarded-for",
                HeaderValue::from_str(value).expect("header"),
            );
        }
        headers
    }

    fn ip(raw: &str) -> IpAddr {
        raw.parse().expect("IP address")
    }

    #[test]
    fn direct_mode_ignores_forwarding_headers() {
        let identity = TrustedProxyConfig::direct_only().resolve(
            IpAddr::V4(Ipv4Addr::new(198, 51, 100, 10)),
            &headers(&["203.0.113.1"]),
        );
        assert_eq!(identity.effective_ip, ip("198.51.100.10"));
        assert_eq!(identity.source, ClientIdentitySource::DirectPeer);
    }

    #[test]
    fn trusted_peer_uses_single_forwarded_client() {
        let identity = trusted_config("10.0.0.0/8", 8)
            .resolve("10.0.0.2".parse().unwrap(), &headers(&["203.0.113.7"]));
        assert_eq!(identity.effective_ip, ip("203.0.113.7"));
        assert_eq!(identity.source, ClientIdentitySource::TrustedForwardedChain);
    }

    #[test]
    fn right_to_left_walk_skips_trusted_proxies_and_leftmost_spoof() {
        let config = trusted_config("10.0.0.0/8,192.0.2.0/24", 8);
        let identity = config.resolve(
            "10.0.0.2".parse().unwrap(),
            &headers(&["198.51.100.99, 203.0.113.8, 192.0.2.10"]),
        );
        assert_eq!(identity.effective_ip, ip("203.0.113.8"));
        assert_ne!(identity.effective_ip, ip("198.51.100.99"));
    }

    #[test]
    fn untrusted_peer_ignores_valid_forwarding_chain() {
        let identity = trusted_config("10.0.0.0/8", 8)
            .resolve("198.51.100.12".parse().unwrap(), &headers(&["203.0.113.7"]));
        assert_eq!(identity.effective_ip, ip("198.51.100.12"));
        assert_eq!(identity.source, ClientIdentitySource::DirectPeer);
    }

    #[test]
    fn forwarded_and_x_real_ip_are_intentionally_ignored() {
        let mut candidate = HeaderMap::new();
        candidate.insert("forwarded", HeaderValue::from_static("for=203.0.113.7"));
        candidate.insert("x-real-ip", HeaderValue::from_static("203.0.113.8"));
        let identity =
            trusted_config("10.0.0.0/8", 8).resolve("10.0.0.2".parse().unwrap(), &candidate);
        assert_eq!(identity.effective_ip, ip("10.0.0.2"));
        assert_eq!(
            identity.source,
            ClientIdentitySource::ForwardedHeaderRejected
        );
    }

    #[test]
    fn all_trusted_chain_falls_back_to_peer() {
        let identity = trusted_config("10.0.0.0/8", 8).resolve(
            "10.0.0.2".parse().unwrap(),
            &headers(&["10.1.1.1, 10.2.2.2"]),
        );
        assert_eq!(identity.effective_ip, ip("10.0.0.2"));
        assert_eq!(
            identity.source,
            ClientIdentitySource::ForwardedHeaderRejected
        );
    }

    #[test]
    fn multiple_header_fields_preserve_wire_order() {
        let identity = trusted_config("10.0.0.0/8", 8).resolve(
            "10.0.0.2".parse().unwrap(),
            &headers(&["198.51.100.9", "203.0.113.8, 10.0.0.3"]),
        );
        assert_eq!(identity.effective_ip, ip("203.0.113.8"));
        assert_ne!(identity.effective_ip, ip("198.51.100.9"));
    }

    #[test]
    fn malformed_headers_fall_back_to_peer() {
        let config = trusted_config("10.0.0.0/8", 8);
        for raw in [
            "not-an-ip",
            "203.0.113.1,,10.0.0.3",
            "203.0.113.1:80",
            "\"203.0.113.1\"",
        ] {
            let identity = config.resolve("10.0.0.2".parse().unwrap(), &headers(&[raw]));
            assert_eq!(identity.effective_ip, ip("10.0.0.2"));
            assert_eq!(
                identity.source,
                ClientIdentitySource::ForwardedHeaderRejected
            );
        }
    }

    #[test]
    fn empty_and_missing_headers_fall_back_to_peer() {
        let config = trusted_config("10.0.0.0/8", 8);
        for candidate in [HeaderMap::new(), headers(&[" "])] {
            let identity = config.resolve("10.0.0.2".parse().unwrap(), &candidate);
            assert_eq!(identity.effective_ip, ip("10.0.0.2"));
            assert_eq!(
                identity.source,
                ClientIdentitySource::ForwardedHeaderRejected
            );
        }
    }

    #[test]
    fn non_utf8_header_falls_back_to_peer() {
        let mut candidate = HeaderMap::new();
        candidate.insert(
            "x-forwarded-for",
            HeaderValue::from_bytes(&[0xff, 0xfe]).expect("opaque header"),
        );
        let identity =
            trusted_config("10.0.0.0/8", 8).resolve("10.0.0.2".parse().unwrap(), &candidate);
        assert_eq!(identity.effective_ip, ip("10.0.0.2"));
        assert_eq!(
            identity.source,
            ClientIdentitySource::ForwardedHeaderRejected
        );
    }

    #[test]
    fn byte_and_hop_limits_fall_back_to_peer() {
        let config = trusted_config("10.0.0.0/8", 2);
        let oversized = "1".repeat(MAX_FORWARDED_HEADER_BYTES + 1);
        for candidate in [
            headers(&[&oversized]),
            headers(&["1.1.1.1,2.2.2.2,3.3.3.3"]),
        ] {
            let identity = config.resolve("10.0.0.2".parse().unwrap(), &candidate);
            assert_eq!(identity.effective_ip, ip("10.0.0.2"));
            assert_eq!(
                identity.source,
                ClientIdentitySource::ForwardedHeaderRejected
            );
        }
    }

    #[test]
    fn normalizes_ipv4_ipv6_and_ipv4_mapped_ipv6() {
        let config = trusted_config("10.0.0.1,2001:db8::/32", 8);
        let ipv4 = config.resolve("10.0.0.1".parse().unwrap(), &headers(&["203.0.113.9"]));
        let ipv6 = config.resolve("2001:db8::1".parse().unwrap(), &headers(&["2001:db9::1"]));
        let mapped = config.resolve(
            IpAddr::V6(Ipv4Addr::new(10, 0, 0, 1).to_ipv6_mapped()),
            &headers(&["::ffff:203.0.113.9"]),
        );
        assert_eq!(ipv4.effective_ip, ip("203.0.113.9"));
        assert_eq!(ipv6.effective_ip, ip("2001:db9::1"));
        assert_eq!(mapped.effective_ip, ip("203.0.113.9"));
    }

    #[test]
    fn configuration_rejects_empty_invalid_blanket_and_hop_bounds() {
        assert!(TrustedProxyConfig::parse(true, "", 8).is_err());
        assert!(TrustedProxyConfig::parse(true, "invalid", 8).is_err());
        assert!(TrustedProxyConfig::parse(true, "127.0.0.1,", 8).is_err());
        assert!(TrustedProxyConfig::parse(true, "0.0.0.0/0", 8).is_err());
        assert!(TrustedProxyConfig::parse(true, "::/0", 8).is_err());
        assert!(TrustedProxyConfig::parse(false, "", 0).is_err());
        assert!(TrustedProxyConfig::parse(false, "", MAX_TRUST_PROXY_HOPS + 1).is_err());
    }

    #[test]
    fn configuration_accepts_exact_addresses_and_scoped_networks() {
        let exact = TrustedProxyConfig::parse(true, "127.0.0.1,::1", 8).unwrap();
        let networks = TrustedProxyConfig::parse(true, "10.0.0.0/8,2001:db8::/32", 8).unwrap();
        assert!(exact.is_trusted("127.0.0.1".parse().unwrap()));
        assert!(exact.is_trusted("::1".parse().unwrap()));
        assert!(networks.is_trusted("10.2.3.4".parse().unwrap()));
        assert!(networks.is_trusted("2001:db8::5".parse().unwrap()));
    }
}
