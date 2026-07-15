# Canonical environment configuration

Runtime configuration is accepted exclusively through environment variables whose names use the `OMNI_*` prefix.

## Contract

- Canonical values are read directly; no fallback name is consulted.
- Unknown or obsolete prefixes are ignored and behave like an unset variable.
- Child processes receive only canonical Omni configuration names.
- Deployment manifests, examples, workflows, and current operational documentation must contain only canonical names.
- The repository check `npm run validate:env-aliases` fails if an obsolete name is reintroduced outside explicit negative tests or immutable historical evidence.

## Deployment action

Before deploying this revision, copy every required configuration value to its canonical `OMNI_*` key in the target platform. Remove obsolete keys only after confirming the canonical key is present. Secret values must never be printed during that verification.

Historical audit documents may retain old spellings as evidence. Such files carry an explicit notice that those names are obsolete and are not accepted by the current runtime.
