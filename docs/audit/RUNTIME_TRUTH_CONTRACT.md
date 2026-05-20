# Runtime Truth Contract — Phase 15 (Roadmap Oficial v2.1)

## Princípio

O sistema Omni nunca mente sobre o que aconteceu durante uma execução.
Toda resposta pública contém um objeto `runtime_truth` que declara
exatamente o que foi usado, tentado e executado.

---

## Estrutura do objeto `runtime_truth`

```json
{
  "runtime_mode": "MATCHER_SHORTCUT",
  "intent": "greeting",
  "intent_source": "rule_based",
  "classifier_version": "regex_v1",
  "matcher_used": true,
  "llm_provider_attempted": false,
  "llm_provider_succeeded": false,
  "tool_invoked": false,
  "tool_executed": false,
  "fallback_triggered": false,
  "node_invoked": false,
  "node_exit_code": null,
  "public_summary": "Responded using a local matcher. No provider or tool execution occurred."
}
```

---

## Campos e contratos

| Campo | Tipo | Contrato |
|---|---|---|
| `runtime_mode` | string | Nunca `FULL_COGNITIVE_RUNTIME` quando um matcher foi usado |
| `intent` | string | Sempre declara o intent inferido, mesmo que seja `unknown` |
| `intent_source` | string | `rule_based` \| `embedding` \| `llm` — nunca omitido |
| `classifier_version` | string | Identifica o classificador usado (`regex_v1`, `embedding_v1`, etc) |
| `matcher_used` | bool | `true` se e somente se um matcher local respondeu |
| `llm_provider_attempted` | bool | `false` quando `matcher_used=true` — nunca contradiz |
| `llm_provider_succeeded` | bool | `false` quando `llm_provider_attempted=false` |
| `tool_invoked` | bool | `true` quando uma ferramenta foi solicitada |
| `tool_executed` | bool | `true` somente se a ferramenta completou com sucesso |
| `fallback_triggered` | bool | `true` quando qualquer fallback de segurança foi ativado |
| `node_exit_code` | int \| null | `null` quando nenhum processo Node foi invocado |
| `public_summary` | string | Resumo em linguagem natural, sem detalhes internos |

---

## Invariantes garantidas

1. `matcher_used=true` → `llm_provider_attempted=false`
2. `fallback_triggered=true` → `tool_executed=false`
3. `tool_executed=true` → `tool_invoked=true`
4. `llm_provider_succeeded=true` → `llm_provider_attempted=true`
5. `runtime_mode=MATCHER_SHORTCUT` → `public_summary` declara explicitamente que não houve provider

---

## Implementação

- JS: `buildRuntimeTruth()` e `inferIntentWithSource()` em `core/brain/queryEngineAuthority.js`
- Python: `classify_memory_record()` e `_is_positive_learning_candidate()` em `learning_logger.py`
- Rust: campos de runtime truth propagados via `call_python()` response

---

## O que o Runtime Truth NÃO contém

- Stack traces
- Tokens ou API keys
- Paths de sistema de arquivos
- Mensagem original do usuário
- Erros internos com detalhes técnicos
- Session IDs completos
