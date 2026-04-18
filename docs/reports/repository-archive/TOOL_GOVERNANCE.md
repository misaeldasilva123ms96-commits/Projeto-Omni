# Tool Governance

## Taxonomy
- `direct_response`
- `information_gathering`
- `code_file_read`
- `file_mutation`
- `execution_shell`
- `external_network`
- `human_approval`

## Policy mapping
- Low risk: read-only inspection tools
- Medium risk: file mutation
- High risk: shell, external network, human approval paths

## Specialist scope
- researcher_agent: read-only inspection only
- coder_agent: read + mutation
- reviewer_agent: read-only / direct analysis
- master_orchestrator: bounded orchestration set

## Live enforcement
- Policy decisions are attached to actions before execution.
- The Python runtime can stop a step before tool execution with `policy_stop`.
- Audit logs now include governance and goal lineage.
