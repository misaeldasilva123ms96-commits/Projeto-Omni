# Cognitive Decision Model

This document defines what counts as a good execution decision in Omni.

## Decision Goal

A correct decision chooses the cheapest safe path that can still satisfy the request.

The order is:

1. Use a direct response when the request is explanatory, conversational, or status-only.
2. Use a local tool when the request requires deterministic workspace evidence and a trusted local tool can satisfy it.
3. Use Node execution when the request needs the Node planner, Node-specific runtime behavior, or an action graph that local tools cannot satisfy alone.
4. Use fallback only when execution is unsafe, unavailable, invalid, or produces an empty result.

## Correct Decision

A decision is correct when it:

- matches the task shape
- uses tools only when evidence is required
- avoids fallback when a supported execution path exists
- avoids generic text when a file, test, or action was explicitly requested
- stays consistent across equivalent prompts

## Incorrect Decision

A decision is incorrect when it:

- answers with plain text even though the request explicitly requires reading, searching, testing, or editing
- sends a read-only request to Node when a deterministic local tool would suffice
- falls back despite a valid local or Node path being available
- uses a higher-risk path without a concrete need
- produces different strategy choices for semantically equivalent prompts

## Strategy Selection Rules

### Direct Response

Use when:

- the user asks for explanation, summary, status, or general clarification
- no workspace evidence is required
- no execution or verification is required

Examples:

- "o que e uma api?"
- "explique o fluxo do runtime"
- "gere um resumo da sessao"

Bad decision:

- replying directly to "analise o arquivo package.json"

### Local Tool

Use when:

- the request explicitly mentions a file or deterministic workspace lookup
- the task can be satisfied with trusted local tools such as `read_file`, `glob_search`, or `test_runner`
- no Node-only graph is required

Examples:

- "analise o arquivo package.json" -> `read_file`
- "encontre o arquivo tsconfig.json" -> `glob_search`
- "rode os testes e valide" -> `test_runner`

Bad decision:

- routing these requests to a generic conversational answer
- sending them to Node when a local engineering tool already covers the task

### Node Execution

Use when:

- the request explicitly requires the Node runtime or Node-side planner
- the action graph contains delegated execution or non-local actions
- the request is a Node-specific code mutation or runtime bridge task

Examples:

- "implemente ajuste no js-runner e queryengine"
- "corrija o node bridge do queryengine"

Bad decision:

- using Node for a simple file read or file search

### Fallback

Use only when:

- the primary path is unavailable
- the result is empty or invalid
- the action is denied or unsafe
- a bridge or provider failure prevents execution

Fallback is acceptable only after a real path was considered and rejected with evidence.

## Decision Evidence

The runtime should expose decision evidence through structured fields, not only natural-language text.

Important fields:

- `selected_strategy`
- `primary_execution_type`
- `decision_task_type`
- `decision_reasoning`
- `decision_reason_codes`
- `decision_requires_tools`
- `decision_requires_node_runtime`
- `decision_must_execute`
- `decision_suggested_tools`
- `decision_preferred_capability_path`

## Good vs Bad Examples

| Input | Good Decision | Bad Decision |
| --- | --- | --- |
| `analise o arquivo package.json` | `TOOL_ASSISTED` + `read_file` + `LOCAL_TOOL_EXECUTION` | `DIRECT_RESPONSE` or generic explanation |
| `encontre o arquivo tsconfig.json` | `TOOL_ASSISTED` + `glob_search` + `LOCAL_TOOL_EXECUTION` | `NODE_EXECUTION` without need |
| `rode os testes e valide` | `TOOL_ASSISTED` + `test_runner` | fallback without attempting validation |
| `explique o que o sistema faz` | `DIRECT_RESPONSE` | unnecessary tool or Node execution |
| `ajuste o js-runner e queryengine` | `NODE_RUNTIME_DELEGATION` + `NODE_EXECUTION` | local direct response or read-only tool path |

## Validation Standard

Decision quality is considered acceptable when:

- curated decision dataset cases pass
- explicit file requests prefer deterministic local tools
- conversational prompts do not request tools
- Node-specific prompts consistently select `NODE_RUNTIME_DELEGATION`
- fallback is not chosen for cases with a valid deterministic path
