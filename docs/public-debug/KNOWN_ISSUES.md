# Known Issues

## Execution collapse

Status: **PARTIALLY FIXED**

What changed:

- The orchestrator no longer treats `compat_execute()` as the only effective strategy-execution path.
- A primary node execution branch now exists and is attempted before compatibility fallback when the turn is execution-capable.
- Empty node responses are treated as failure in the recovered primary execution path.

What is still true:

- Compatibility execution still exists and remains necessary as a safe fallback path.
- Routing/classification can still choose conservative strategies for prompts that are actually tool-capable.
- Additional work is still needed to increase the activation rate and success rate for non-compat paths beyond the first recovered path.

## Current public debug focus

- improving strategy selection accuracy without hiding degraded behavior
- extending reliable non-compat execution beyond the first recovered path
- reducing generic or compatibility-heavy responses when execution evidence is available
