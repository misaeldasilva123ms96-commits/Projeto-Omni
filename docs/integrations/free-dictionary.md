# Free Dictionary API pilot

The governed `dictionary_lookup` tool is an English-only, keyless community and
experimental pilot using v2 `GET /api/v2/entries/en/<word>`. Documentation was
reviewed on 2026-08-29. The service has no assumed SLA and its failure is isolated
from other providers and the runtime.

The dynamic segment is authorized by one closed, maintainer-owned safe path
template. Input is restricted to a single 1–64 character ASCII Latin word with
internal apostrophes or hyphens. Validation occurs before percent encoding; the
model cannot choose language, version, host, path, query, or template.

Responses are bounded to three entries, five meanings per entry, three
definitions per meaning, and ten synonyms/antonyms. Individual text fields are
also truncated. Audio URLs are discarded and no secondary fetch occurs.
Definitions are cached for seven days and live requests are limited to 10 per
minute per process.

Both `OMNI_EXTERNAL_API_ENABLED=true` and
`OMNI_EXTERNAL_FREE_DICTIONARY_ENABLED=true` are required; defaults are off.

Official documentation: <https://dictionaryapi.dev/>
