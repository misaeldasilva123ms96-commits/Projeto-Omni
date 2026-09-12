# Internal service request safety

## Python session identity

The Python HTTP service maps `session_id` to the canonical bridge field
`client_session_id`. Identity is scoped to the current request with a context
variable, rather than written to process environment variables shared by HTTP
threads. Concurrent requests retain separate transcript identities, and the
context is restored on both success and failure.

In service mode an explicit session ID takes precedence over `AI_SESSION_ID`.
Requests without an ID receive a fresh `service-<uuid>` identity; clients that
want history continuity should retain and send a stable session ID. Nonempty
IDs must use 1–128 ASCII letters, digits, underscores, hyphens or periods.
Slashes and colons are rejected to keep IDs safe as filenames on Windows too.
The existing subprocess environment contract is unchanged.

## Rust delivery and recovery

The Rust bridge may retry or use its configured subprocess fallback only when
no request was sent: connection refusal, connection timeout, or a circuit
breaker that prevented a connection. Retry counts remain bounded by
`OMNI_PYTHON_SERVICE_RETRY_ATTEMPTS`.

After writing starts, errors have an uncertain execution outcome. A read or
write failure, response timeout, non-2xx HTTP status, malformed JSON or invalid
chat envelope therefore returns a public-safe failure without repeating the
task, even when retries and subprocess fallback are enabled. `request_id` is
for correlation and is not an idempotency guarantee. Automatic replay after
delivery requires a separate durable deduplication protocol before it can be
enabled safely.

See [Node service authentication](../architecture/node-internal-query-engine-service.md)
for the required bearer token on the Node HTTP endpoint.
