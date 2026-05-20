# Test Evidence — Phase 15 (Roadmap Oficial v2.1)

## Suite de testes de segurança

**Localização:** `tests/security/test_security_regression.py`
**Framework:** pytest
**Comando:** `pytest tests/security/test_security_regression.py -v`

---

## Classes de teste e gates cobertos

| Classe | Gate | O que valida |
|---|---|---|
| `TestShellHardening` | 1A | Shell bloqueado por padrão; comandos perigosos rejeitados; sem campos internos no erro |
| `TestBackendPayloadSanitization` | 1C | `strip_internal_fields()` remove stack/token; `build_public_cognitive_runtime_inspection` existe e tem `public_summary` |
| `TestLearningRedaction` | 1E | Email, JWT, API key (sk-proj-*), Unix path, CPF, telefone BR redacted |
| `TestSupabaseSecrets` | 4 | `supabaseKey` e `supabaseUrl` não nos exports; `getSupabaseClient` exportado |
| `TestRuntimeTruth` | 2 | `inferIntentWithSource` e `buildRuntimeTruth` existem; `llmProviderAttempted: false` nos matchers; `runtime_truth` anexado |
| `TestToolGovernance` | 3 | `evaluateToolGovernanceJS` existe; categorias shell/destrutiva definidas; `_BLOCKED_IN_DEMO` inclui shell |
| `TestErrorTaxonomy` | 8 | Códigos críticos presentes; `build_public_error` existe; sem stack trace em erros públicos |
| `TestTrainingSafety` | 9 | `_is_positive_learning_candidate` exclui MATCHER_SHORTCUT, SAFE_FALLBACK; `classify_memory_record` retorna `routing_eval_case` |

---

## Datasets de avaliação criados

| Dataset | Localização | Registros |
|---|---|---|
| Runtime Truth Eval | `data/evals/runtime_truth_eval.jsonl` | 10 |
| Safety Eval | `data/evals/safety_eval.jsonl` | 10 |
| Intent Eval | `data/evals/intent_eval.jsonl` | 25 |

---

## Scripts de validação

| Script | Localização | Uso |
|---|---|---|
| Export de candidatos de training | `scripts/export_training_candidates.py` | `python scripts/export_training_candidates.py --dry-run` |
| Validação de candidato | `scripts/validate_training_candidate.py` | `python scripts/validate_training_candidate.py --file data/exports/candidates.jsonl` |

---

## Gates verificados em smoke tests

Todos os 26 checks do smoke test passaram, confirmando:

- ✅ `inferIntentWithSource` presente
- ✅ `buildRuntimeTruth` presente
- ✅ `runtime_truth` anexado a respostas de matcher
- ✅ `llmProviderAttempted: false` em ambas as chamadas de matcher
- ✅ `evaluateToolGovernanceJS` presente
- ✅ `_BLOCKED_IN_DEMO` e `_BLOCKED_BY_DEFAULT` definidos
- ✅ `buildPublicError` importado
- ✅ `validate_chat_input`, `max_message_chars`, `validate_message_chars`, `validate_session_id` no Rust
- ✅ Control char detection (`is_control`) no Rust
- ✅ `OMNI_MAX_MESSAGE_CHARS` configurável via env
- ✅ `Dockerfile.demo`, `docker-compose.demo.yml`, documentação de container existem
- ✅ Suite de testes de segurança existe
- ✅ Todos os 6 error codes críticos em `errors.py`
- ✅ `build_public_error` em Python
- ✅ `_is_positive_learning_candidate`, `MATCHER_SHORTCUT` excluído, `classify_memory_record`, `training_candidate` em `learning_logger.py`

---

## Cobertura de gates

| Gate | Coberto por testes | Smoke test | Dataset |
|---|---|---|---|
| 1A | ✅ `TestShellHardening` | ✅ | — |
| 1B | Parcial (módulo isolado) | — | — |
| 1C | ✅ `TestBackendPayloadSanitization` | — | — |
| 1D | Frontend (Vitest) | — | — |
| 1E | ✅ `TestLearningRedaction` | — | `safety_eval.jsonl` |
| 2 | ✅ `TestRuntimeTruth` | ✅ | `runtime_truth_eval.jsonl` |
| 3 | ✅ `TestToolGovernance` | ✅ | — |
| 4 | ✅ `TestSupabaseSecrets` | — | — |
| 5 | Integração (Rust) | ✅ | — |
| 6 | Existência de arquivos | ✅ | — |
| 7 | — (é a própria suite) | ✅ | — |
| 8 | ✅ `TestErrorTaxonomy` | ✅ | — |
| 9 | ✅ `TestTrainingSafety` | ✅ | `runtime_truth_eval.jsonl` |
