# Typed tool-output bindings

Tool-output bindings let a later governed step consume a small, validated part
of an earlier governed result without asking the model to copy data through text.
They are explicit, typed, source-aware, target-aware, allow-listed, and fail
closed. They are not a general transformation or workflow language.

```text
User
 ↓
Planner
 ↓
geocode_place (step geocode-1)
 ↓
Nominatim normalized unique result
 ↓
Typed Binding Resolver
 ↓
weather_forecast (step weather-2)
 ↓
Open-Meteo normalized result
 ↓
Brain response
```

## Initial contract

The only accepted declaration is:

```json
{
  "type": "geocode_unique_candidate_to_weather",
  "source_step_id": "geocode-1"
}
```

Only those two keys are accepted. There is no JSONPath, JMESPath, template,
expression, `eval`, arbitrary field, URL, source tool, or target tool selection.
The resolver requires target `weather_forecast`; a successful source result from
exactly one completed step with the requested ID; source `geocode_place`; Runtime
Truth identifying Nominatim; `resolution=unique`; exactly one candidate; and
finite, in-range numeric latitude and longitude. It constructs a new action and
never mutates the source result or original target action.

The existing execution loop passes only completed earlier results into a step.
A future source is therefore not visible and fails `binding_source_not_found`.
Duplicate IDs fail `binding_source_ambiguous_identity`; a self-reference fails
`binding_cycle_denied`. The Execution Manifest marks the weather step dependency
and binding type without values.

## Failure semantics

- ambiguous geocoding: `binding_source_ambiguous`; weather is not executed;
- failed geocoding/provider/gate: `dependency_failed`; weather is not executed;
- forged shape, provenance, or coordinates: `binding_source_invalid`;
- direct latitude or longitude plus binding: `binding_argument_conflict`;
- unknown or extended declaration: fail closed;
- wrong target: `binding_target_invalid`.

Binding errors return before trusted execution and self-repair. The resolver does
not retry, re-run geocoding, select candidate zero, or change provider cache/rate
limits. Provider gates remain authoritative independently for both steps.

## Privacy and observability

Events `runtime.tool_binding.started`, `succeeded`, `denied`, and `failed` contain
only binding type, source step/tool, target tool, bound field names, resolution
state, and categorical reason. They never contain coordinate values, place query,
or raw result payload. Stored action receipts redact weather coordinates and
geocoding place queries. Binding provenance records only type, identities,
`bound_fields`, and resolved state.

The binding ignores geocoder query, display name, importance, and provider raw
JSON. Weather retains its own Open-Meteo Runtime Truth and provenance; geocoding
and binding provenance remain separate internal audit evidence.

## Planning boundary

The action/plan contract can now represent named-place weather as two ordered
steps with an explicit binding. Direct coordinate weather remains a one-step
action without binding, and standalone geocoding remains unchanged. Natural
language interpretation stays in the existing planner; the resolver accepts only
the typed action contract and performs no text parsing.
