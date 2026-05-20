# Training Readiness — Phase 13 (Roadmap Oficial v2.1)

Branch sugerida: `training/readiness-13`

## Pré-requisitos cumpridos

Antes de iniciar coleta de dados de treinamento, todos os gates abaixo foram verificados:

| Gate | Status |
|---|---|
| 1A — Shell blocked | ✅ PASSED |
| 1B — Specialist error not logged | ✅ PASSED |
| 1C — Backend payload sanitized | ✅ PASSED |
| 1D — Frontend payload sanitized | ✅ PASSED |
| 1E — Learning redacts PII/secrets | ✅ PASSED |
| 2 — Runtime Truth Contract | ✅ PASSED |
| 7 — Security regression tests | ✅ PASSED |
| 9 — Fallback/matcher excluded from training | ✅ PASSED |

---

## Critérios para dado positivo de treinamento

Um registro só pode ser usado como exemplo positivo se **todos** os critérios forem verdadeiros:

| Campo | Valor obrigatório |
|---|---|
| `provider_succeeded` | `true` |
| `fallback_triggered` | `false` |
| `runtime_truth_confidence` | `high` |
| `no_pii_detected` | `true` |
| `governance_status` | `allowed` |
| `user_visible_success` | `true` |
| `runtime_mode` | Um dos: `FULL_COGNITIVE_RUNTIME`, `NODE_EXECUTION_SUCCESS`, `LOCAL_TOOL_SUCCESS`, `DIRECT_LOCAL_RESPONSE` |

---

## Registros que NÃO viram exemplo positivo

Os seguintes padrões geram apenas `failure_memory`, `diagnostic_event` ou `routing_eval_case`:

- `fallback_triggered = true`
- `runtime_mode` em `{MATCHER_SHORTCUT, SAFE_FALLBACK, RULE_BASED_INTENT}`
- `tool_status` em `{failed, blocked}`
- `governance_decision = blocked`
- `provider_succeeded = false`
- Registro com PII detectado (`no_pii_detected = false`)
- Requisição com conteúdo inseguro

---

## Schema do dataset de treinamento

```json
{
  "id": "ctrl-learn-<uuid>",
  "timestamp": "2025-01-01T00:00:00Z",
  "classification": "training_candidate | failure_memory | diagnostic_event | routing_eval_case",
  "runtime_mode": "FULL_COGNITIVE_RUNTIME",
  "intent": "execution",
  "intent_source": "rule_based | embedding | llm",
  "provider_succeeded": true,
  "fallback_triggered": false,
  "tool_invoked": false,
  "tool_executed": false,
  "governance_status": "allowed",
  "no_pii_detected": true,
  "user_visible_success": true,
  "runtime_truth_confidence": "high",
  "input_redacted": "<redacted message>",
  "output_redacted": "<redacted response>"
}
```

---

## Artefatos desta fase

| Artefato | Localização | Status |
|---|---|---|
| Este documento | `docs/training/TRAINING_READINESS.md` | ✅ |
| Runtime truth eval dataset | `data/evals/runtime_truth_eval.jsonl` | ✅ |
| Safety eval dataset | `data/evals/safety_eval.jsonl` | ✅ |
| Intent eval dataset | `data/evals/intent_eval.jsonl` | ✅ |
| Export script | `scripts/export_training_candidates.py` | ✅ |
| Validation script | `scripts/validate_training_candidate.py` | ✅ |

---

## Gate 13: PASSED

- [x] Export de candidatos de training existe
- [x] Registros inseguros excluídos
- [x] Fallback/matcher não são exemplos positivos
- [x] Schema do dataset documentado
- [x] Script de validação existe
- [x] Sem merge direto em main
