# Remediation Summary — Phase 15 (Roadmap Oficial v2.1)

## O que foi corrigido

Este documento resume todas as correções aplicadas no projeto Omni como parte do
Roadmap Oficial v2.1. Todas as mudanças foram desenvolvidas em ambiente isolado
e entregues para aplicação manual no repositório.

---

## Correções por gate

### Gate 1A — Shell Hardening
**Arquivo:** `backend/python/brain/runtime/tools/shell/run_command.py`

**Problema:** Shell poderia ser executado sem validação de policy.
**Correção:**
- Adicionada verificação de `OMNI_ALLOW_SHELL_TOOLS` / `OMINI_ALLOW_SHELL_TOOLS` antes de qualquer execução.
- Adicionada lista de comandos perigosos (`_BLOCKED_COMMANDS`).
- Retorna `error_public_code: SHELL_TOOL_BLOCKED` quando bloqueado.
- Sem stack trace no payload público.

---

### Gate 1B — Specialist Error Logging
**Arquivo:** `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`

**Problema:** Erros internos de especialista podiam ser logados com detalhes sensíveis.
**Correção:**
- Adicionada função `sanitize_specialist_error()` que redige campos sensíveis antes de qualquer log.
- Erros internos nunca aparecem no payload público.

---

### Gate 1C — Backend Payload Sanitization
**Arquivo:** `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`

**Problema:** Payload de resposta do backend podia conter campos internos (stack, token, paths).
**Correção:**
- Adicionada `strip_internal_fields()` que remove campos proibidos.
- Adicionada `build_public_cognitive_runtime_inspection()` para construir visão pública.

---

### Gate 1D — Frontend Debug Sanitizer
**Arquivos:** `frontend/src/lib/runtimeDebugSanitizer.ts`, `frontend/src/components/status/RuntimePanel.tsx`

**Problema:** Frontend exibia campos internos no painel de debug.
**Correção:**
- Criada biblioteca `runtimeDebugSanitizer.ts` com lista de campos proibidos.
- `RuntimePanel.tsx` passa todos os dados pelo sanitizador antes de exibir.

---

### Gate 1E — Learning Log Redaction
**Arquivo:** `backend/python/brain/runtime/learning/learning_logger.py`

**Problema:** Logs de aprendizado podiam conter PII (emails, CPF, telefones, JWTs, API keys, paths).
**Correção:**
- Adicionada lista `_SECRET_PATTERNS` com 12+ padrões de redação.
- Todos os campos de texto passam pela redação antes de persistir.

---

### Gate 2 — Runtime Truth Contract
**Arquivo:** `core/brain/queryEngineAuthority.js`

**Problema:** Respostas de matcher e fallback não declaravam honestamente o que havia acontecido.
**Correção:**
- Adicionada `inferIntentWithSource()` — wrapper que declara a fonte do classificador.
- Adicionada `buildRuntimeTruth()` — constrói objeto de verdade observável para cada resposta.
- `runtime_truth` anexado a todas as respostas de matcher shortcut.

---

### Gate 3 — Tool Governance Enforcement
**Arquivo:** `core/brain/queryEngineAuthority.js`

**Problema:** Não havia verificação de governança JS antes de invocar ferramentas.
**Correção:**
- Adicionada `evaluateToolGovernanceJS()` com categorias de ferramentas.
- Shell e destrutivas bloqueadas por padrão.
- Demo pública bloqueia shell, write, destrutivas, git e network.

---

### Gate 4 — Supabase Secret Removal
**Arquivo:** `storage/memory/supabaseClient.js`

**Problema:** `supabaseKey` e `supabaseUrl` estavam expostos em exports.
**Correção:**
- Removidos dos exports públicos.
- Apenas `getSupabaseClient()` exportada.
- `.env.example` criado com placeholders seguros.
- `.gitignore` atualizado.

---

### Gate 5 — Input Validation (Rust)
**Arquivo:** `backend/rust/src/main.rs`

**Problema:** Chat handlers aceitavam mensagens de qualquer tamanho e formato.
**Correção:**
- `validate_chat_input()`: max 8000 chars (configurável), sem control chars, session_id validado.
- Aplicado em `/chat` e `/api/v1/chat`.
- Configurável via `OMNI_MAX_MESSAGE_CHARS`, `OMNI_MAX_SESSION_ID_CHARS`.

---

### Gate 6 — Container Demo Público
**Arquivos:** `Dockerfile.demo`, `docker-compose.demo.yml`, `docs/deploy/PUBLIC_DEMO_CONTAINER.md`

**Problema:** Não havia forma segura e documentada de executar em demo pública.
**Correção:**
- `Dockerfile.demo` com usuário não-root (omni, uid 1001).
- `docker-compose.demo.yml` com `cap_drop: ALL`, sem docker socket, limites de recursos.
- Documentação completa de como executar e verificar.

---

### Gate 7 — Security Regression Tests
**Arquivo:** `tests/security/test_security_regression.py`

**Problema:** Não havia testes de regressão para as correções de segurança.
**Correção:**
- 9 classes de teste cobrindo todos os gates 1A, 1C, 1E, 2, 3, 4, 7, 8, 9.
- Executável com `pytest tests/security/test_security_regression.py -v`.

---

### Gate 8 — Error Taxonomy Centralizada
**Arquivos:** `core/brain/errorCodes.js`, `backend/python/brain/runtime/errors.py`

**Problema:** Códigos de erro públicos estavam espalhados e inconsistentes.
**Correção:**
- 19 códigos de erro públicos definidos em ambas as linguagens.
- `buildPublicError()` / `build_public_error()` garante que nunca há vazamento interno.
- `internal_error_redacted: true` em todo erro público.

---

### Gate 9 — Memory & Training Safety
**Arquivo:** `backend/python/brain/runtime/learning/learning_logger.py`

**Problema:** Respostas de matcher e fallback podiam ser usadas como dados positivos de treinamento.
**Correção:**
- `_is_positive_learning_candidate()`: exclui `MATCHER_SHORTCUT`, `SAFE_FALLBACK`, `RULE_BASED_INTENT`.
- `classify_memory_record()`: classifica corretamente como `routing_eval_case` ou `diagnostic_event`.
- `_execution_success()`: removido `MATCHER_SHORTCUT` da lista de modos de sucesso positivo.
