# Open-Meteo weather pilot

The governed `weather_forecast` tool is a deny-by-default development and
evaluation pilot using `https://api.open-meteo.com/v1/forecast` with `GET` only.
Both `OMNI_EXTERNAL_API_ENABLED=true` and
`OMNI_EXTERNAL_OPEN_METEO_ENABLED=true` are required. Callers cannot provide an
endpoint, host, path, method, redirect policy, or arbitrary provider field.

The adapter accepts finite latitude and longitude within geographic bounds and
one to seven forecast days. It fixes the current fields to temperature,
apparent temperature, precipitation, weather code, and wind speed; daily fields
are fixed to weather code, maximum/minimum temperature, and precipitation sum.
It also fixes `timezone=auto`.

Responses are size-bounded JSON and are normalized to location, timezone,
current conditions, daily values, provider, and provenance. Provider structures
and numeric values are type-checked before they cross the adapter boundary.

The Omni provider definition uses an eight-second timeout, at most two bounded
GET attempts, a five-minute process-local cache, and a configured process-local
transport-attempt throttle of 30 requests per 60 seconds. These values are Omni
safety controls; they are not a statement of application-wide, account-wide, or
provider-wide quota compliance. Horizontally scaled deployment requires a
separate operational review.

Provenance retains the required `Weather data by Open-Meteo.com` attribution.
The integration remains a non-commercial pilot subject to provider/licensing
review before production use. It is default OFF and does not authorize any
caller-defined URL or additional provider capability.
