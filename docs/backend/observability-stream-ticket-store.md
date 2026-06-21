# Observability stream ticket store

The Rust API issues opaque, 256-bit, single-use tickets for the observability
EventSource connection. Tickets expire after 30 seconds and are scoped to the
observability stream. Supabase JWTs, API keys, authorization headers, and
cookies are not accepted in the EventSource URL.

## Current mode

`OMNI_OBSERVABILITY_STREAM_TICKET_STORE_MODE` defaults to `process_local`.
The active mode is also exposed as the safe
`observability_stream_ticket_store_mode` field on `/health` and in a startup
diagnostic that contains only the mode name.

`process_local` stores ticket records in the Rust process. The repository's
demo Compose definition declares one Rust API process, and no checked-in
deployment definition configures horizontal Rust API replicas. If a deployment
runs multiple Rust API instances, ticket issuance and EventSource validation
must reach the same instance through sticky routing.

Non-sticky multi-instance deployments require a shared atomic store so that a
ticket can be consumed exactly once across instances. The Rust
`ObservabilityStreamTicketStore` trait is the extension point for that future
implementation. `shared_external` is intentionally rejected at startup until
a supported shared backend exists; the service does not silently fall back to
unsafe process-local behavior when that mode is requested.

## Security invariants

- ticket values remain opaque and are generated from 32 random bytes;
- each ticket has a 30-second TTL;
- successful consumption removes the ticket;
- scope is stored with the ticket and checked before consumption;
- wrong-scope attempts do not consume a valid stream ticket;
- missing, expired, reused, and unknown tickets receive the same generic
  unauthorized response;
- request logging redacts both `ticket` and legacy `token` query values;
- no raw ticket or JWT is included in diagnostics or errors.
