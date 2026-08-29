# URLhaus reputation pilot

Documentation reviewed 2026-08-29 against the official URLhaus Community API.
The community service requires an abuse.ch `Auth-Key`, operates under fair-use
principles, and commercial/for-profit usage requires separate review. The
automated exact-URL lookup uses `POST https://urlhaus-api.abuse.ch/v1/url/`, an
`application/x-www-form-urlencoded` `url` field, and the `Auth-Key` header. Parts
of the current automated-query documentation require an authenticated account.

This read-only pilot sends the supplied public URL indicator to URLhaus. Paths and
queries can contain sensitive data, so the raw URL is excluded from logs,
provenance, runtime events, and learning/correction records. Fragments are removed.
Only HTTP/HTTPS public indicators are accepted; embedded credentials, local names,
single-label names, and non-global IP literals are rejected lexically without DNS.

Omni never connects to, resolves, opens, redirects through, or downloads from the
investigated target. It connects only to `urlhaus-api.abuse.ch` through the central
pinned-TLS gateway. Payload metadata is discarded and no samples or references are
opened. Submission, blocking, quarantine, and other mutations are not implemented.

`query_status=no_results` becomes `not_listed`: URLhaus has no matching record for
the exact URL, which does **not** prove it is safe. An `ok` response becomes
`listed` advisory metadata, not a claim about every path or the entire host. Tags
are bounded to 20 items of 100 characters.

Execution requires both external gates and `OMNI_EXTERNAL_URLHAUS_AUTH_KEY`. Cache
TTL is 30 minutes, local rate limit is 10/minute/process, POST has one attempt, and
the credential is resolved before cache access. Live smoke is opt-in and limited to
one request.

Official sources: <https://urlhaus.abuse.ch/api/> and <https://urlhaus.abuse.ch/>.
