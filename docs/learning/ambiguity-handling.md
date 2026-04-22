# Ambiguity Handling

## Detection

O detector de ambiguidade avalia:

- estratégia determinística atual
- confiança do roteamento
- `oil_summary`
- `execution_manifest`
- urgência e risco

## Typical Conflicts

- `DIRECT_RESPONSE` vs `MULTI_STEP_REASONING`
- `TOOL_ASSISTED` vs `NODE_RUNTIME_DELEGATION`
- `MULTI_STEP_REASONING` vs `SAFE_FALLBACK`

## Guardrails

- risco alto desabilita ranking assistido por modelo
- urgência alta favorece caminho mais seguro
- estratégia proibida nunca pode vencer
- fallback é obrigatório em inconsistência

