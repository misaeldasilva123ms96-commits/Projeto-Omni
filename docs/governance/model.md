# Governance model

Omni’s governance model is **control-plane first**: runs have identity and status, decisions are classified (taxonomy), transitions are explicit, and operator attention paths exist for blocked or waiting states.

## Canonical surfaces

- **Taxonomy** — `brain/runtime/control/governance_taxonomy.py` (reason/source/severity vocabulary)
- **Run registry** — `RunRegistry` persists authoritative run lifecycle
- **Resolution** — governance resolution controller and integration services connect execution outcomes to control-plane state

## Relationship to evolution

Evolution and improvement (Phases 39–40) are **subordinate**: they cannot bypass execution blocks, cannot promote unvalidated mutations, and cannot introduce hidden self-rewrite paths.

## See also

- [gates.md](gates.md)
- [policies.md](policies.md)
- Root `GOVERNANCE.md` — short rule list
