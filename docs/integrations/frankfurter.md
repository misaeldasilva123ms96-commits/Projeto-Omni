# Frankfurter v2

The governed `currency_convert` tool uses the keyless Frankfurter v2 API at the
fixed `GET /v2/rates` path. Documentation was reviewed on 2026-08-29.

The adapter sends only `base` and one `quotes` currency. It multiplies the
returned rate locally with `decimal.Decimal`; only `converted_amount` is rounded
to two decimal places using round-half-even. The original rate is preserved.
Same-currency conversion uses rate 1 locally and performs no network request.

Rates are cached for 30 minutes by base/quote and limited locally to 30 live
requests per minute per process. They are informational and may differ from a
bank, card, exchange-house, or final transaction rate. The integration does not
claim PTAX or a particular official source. Future deployment may consider a
self-hosted Frankfurter instance.

Both `OMNI_EXTERNAL_API_ENABLED=true` and
`OMNI_EXTERNAL_FRANKFURTER_ENABLED=true` are required; defaults are off.

Official documentation: <https://frankfurter.dev/>
