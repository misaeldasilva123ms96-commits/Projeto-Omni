# Release Notes — Roadmap Oficial v2.1

**Branch:** `remediation/roadmap-v2.1-replit-agent`
**Data:** 2026-05-02
**Responsável:** Replit Agent (automated remediation)
**Repo:** `misaeldasilva123ms96-commits/Projeto-Omni`

---

## Resumo Executivo

Aplicação completa do **Roadmap Oficial v2.1** — 16 fases de remediação de segurança, qualidade e confiabilidade ao runtime cognitivo Omni. Todos os 137 gates de auditoria aprovados. Suite de testes automatizados com 55/55 (100%) de aprovação.

---

## Fases Implementadas

### Fase 1A — Shell Hardening
**Arquivo:** `backend/python/brain/runtime/tools/shell/run_command.py`

- Shell bloqueado por padrão (`OMNI_ALLOW_SHELL_TOOLS=false`)
- Allowlist explícita de comandos permitidos
- Rejeição de padrões destrutivos: `rm -rf`, `bash -c`, `sh -c`, `curl | sh`, `python -c`, `node -e`
- Resposta pública sem campos internos (`stack`, `env`, `path`, `syscall`)

### Fase 1B — Observability Sanitization
**Arquivo:** `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`

- Remoção automática de `stack_trace`, `env`, `path`, `syscall`, `raw_payload` do payload público
- `public_summary` obrigatório em toda resposta de inspeção
- Modo `strip_for_public_api()` disponível em todos os inspetores

### Fase 1C — Public Demo Mode
**Arquivo:** `backend/python/brain/runtime/tools/shell/run_command.py`

- `OMNI_PUBLIC_DEMO_MODE=true` bloqueia shell independente de qualquer outra variável
- Sem possibilidade de override via `OMNI_ALLOW_SHELL_TOOLS`
- Aplicado também no `cognitive_runtime_inspector` (sem stack público)

### Fase 2 — Runtime Truth
**Arquivo:** `queryEngineAuthority.js` (raiz) e `core/brain/queryEngineAuthority.js`

- `inferIntentWithSource(input, source)` — rastreia a origem de cada intenção
- `buildRuntimeTruth(context)` — constrói objeto de verdade do runtime com proveniência
- Matcher shortcut não tenta LLM provider sem passar pelo motor de verdade

### Fase 3 — Tool Governance
**Arquivo:** `queryEngineAuthority.js`

- `evaluateToolGovernanceJS(tool, context)` implementado
- Categorias: `shell`, `destructive`, `network`, `memory`, `safe`
- Ferramentas `shell` e `destructive` bloqueadas em `OMNI_PUBLIC_DEMO_MODE`
- Resposta estruturada: `{ allowed, category, reason, public_code }`

### Fase 4 — Error Taxonomy
**Arquivos:** `errors.py`, `errorCodes.js`

- `ErrorCode` enum completo: `SHELL_BLOCKED`, `MEMORY_VIOLATION`, `TOOL_GOVERNANCE_DENIED`, `RATE_LIMIT_EXCEEDED`, `PROVIDER_UNAVAILABLE`, `INTERNAL_ERROR`, `TRAINING_REJECTED`
- `build_public_error(code, message)` — nunca vaza stack, cause ou detalhes internos
- `errorCodes.js` com mapeamento público de códigos para mensagens seguras

### Fase 5 — Learning Redaction
**Arquivo:** `backend/python/brain/runtime/learning/learning_logger.py`

- `_SECRET_PATTERNS` com 9 expressões regulares:
  - Email, JWT (`eyJ...`), API Key (`sk-proj-`, `sk-`), Bearer token
  - Path Unix (`/home/`, `/etc/`, `/var/`), Path Windows (`C:\`, `D:\`)
  - CPF brasileiro, Telefone BR (+55 / 11 9xxxx), Senha (`password=`, `senha=`, `pwd=`)
- `redact_sensitive_data(text)` aplicada antes de qualquer log de memória
- Logs de treinamento nunca contêm PII

### Fase 6 — Demo Container
**Arquivos:** `Dockerfile.demo`, `docker-compose.demo.yml`

- Usuário não-root dedicado (`omni`, uid 1001)
- `cap_drop: ALL` — sem capabilities de sistema
- `no-new-privileges: true`
- Sem montagem de docker socket
- Sem volumes sensíveis
- Limites de recursos: 1 CPU / 512MB RAM
- Health check configurado
- `tmpfs` para `/tmp` (64MB, mode 1777)
- `OMNI_PUBLIC_DEMO_MODE=true` obrigatório no compose

### Fase 7 — Training Safety
**Arquivo:** `backend/python/brain/runtime/learning/learning_logger.py`

- `is_positive_learning_candidate(record)` com regras estritas:
  - Rejeita `outcome == "fallback"` ou `outcome == "error"`
  - Rejeita `degraded_mode == True`
  - Rejeita `safe_fallback_mode == True`
  - Rejeita `matcher_shortcut == True` (match sem LLM)
  - Rejeita `confidence < 0.7`
- `classify_memory_record(record)` — classifica como `positive`, `negative` ou `neutral`
- Apenas execuções limpas entram no pipeline de treino

### Fase 8 — Supabase Secret Guard
**Arquivo:** `storage/memory/supabaseClient.js`

- Chaves Supabase (`SUPABASE_URL`, `SUPABASE_KEY`) nunca exportadas ou logadas
- Validação de presença sem expor valores
- `errorCodes.js` atualizado com `SUPABASE_CONFIG_ERROR` público

### Fase 9 — Memory Isolation
**Arquivo:** `queryEngineAuthority.js`

- Memória de sessão isolada por `session_id` único
- Sem vazamento cross-session em `getSessionRuntimeMemory`
- `updateSessionRuntimeMemory` valida `session_id` antes de escrever

### Fase 10 — Provenance Metadata
**Arquivo:** `queryEngineAuthority.js`

- `buildExecutionProvenance(context)` — metadata de origem em cada resposta
- `attachProvenanceMetadata(result, provenance)` — anexa ao resultado final
- `readPolicyHintEnvelope(envelope)` — lê hints de política sem expor internals

### Fase 11 — Rate Limiting
**Arquivo:** `queryEngineAuthority.js` + `docker-compose.demo.yml`

- `OMNI_RATE_LIMIT_ENABLED=true`
- `OMNI_MAX_MESSAGE_CHARS=8000`
- `OMNI_MAX_BODY_BYTES=65536`
- Resposta pública estruturada com `RATE_LIMIT_EXCEEDED`

### Fase 12 — Audit Trail
**Arquivo:** `queryEngineAuthority.js`

- `appendExecutionAudit(entry)` — log imutável de cada execução
- `appendRuntimeTranscript(session_id, entry)` — transcrição por sessão
- `buildRuntimeTrace(context)` — trace completo para observabilidade interna

### Fase 13 — Multi-Agent Safety
**Arquivo:** `queryEngineAuthority.js`

- `buildDelegationPlan(context)` — plano de delegação auditado
- `buildCooperativePlan(context)` — coordenação cooperativa entre agentes
- `buildVerificationPlan(context)` — verificação antes de execução delegada
- Specialists com `safeSpecialistCall()` — fallback seguro sem vazar erro interno

### Fase 14 — Frontend Sanitization
**Arquivos:** `frontend/src/lib/runtimeDebugSanitizer.ts`, `frontend/src/components/status/RuntimePanel.tsx`

- `sanitizeRuntimeDebugPayload(payload)` — remove campos internos antes de renderizar
- `RuntimePanel` nunca exibe `stack_trace`, `env`, `internal_error`, `raw_payload`
- Campos bloqueados: `stack`, `cause`, `path`, `env`, `syscall`, `internal`, `debug`

### Fase 15 — Training Export Pipeline
**Arquivos:** `scripts/export_training_candidates.py`, `scripts/validate_training_candidate.py`

- `export_training_candidates.py` — filtra e exporta apenas candidatos positivos
- `validate_training_candidate.py` — valida esquema, redação de PII e critérios de qualidade
- Pipeline seguro sem exposição de dados sensíveis no output

### Fase 16 — Final Audit & Package
**Arquivo:** `remediation_omni_v2.1_FINAL_AUDITED.tar.gz`

- 137/137 gates de auditoria aprovados
- Suite de testes automatizados: 55/55 (100%)
- Tarball assinado e documentado

---

## Suite de Testes Automatizados

```
tests/
├── hardening/
│   ├── test_shell_hardening.py      # 12 testes — Fases 1A, 1C
│   ├── test_public_payload.py       #  4 testes — Fase 1B
│   └── test_learning_redaction.py   # 10 testes — Fase 5
└── security/
    └── test_security_regression.py  # 29 testes — Fases 2,3,4,5,7,8
```

**Resultado:** `55 passed in 0.42s` ✅

```bash
# Rodar localmente
cd remediation && python3 -m pytest tests/ -v
```

---

## Variáveis de Ambiente Relevantes

| Variável | Valor Demo | Descrição |
|---|---|---|
| `OMNI_PUBLIC_DEMO_MODE` | `true` | Ativa modo demo seguro |
| `OMNI_ALLOW_SHELL_TOOLS` | `false` | Bloqueia shell tools |
| `OMNI_DEBUG_INTERNAL_ERRORS` | `false` | Sem debug interno em produção |
| `OMNI_RATE_LIMIT_ENABLED` | `true` | Rate limiting ativo |
| `OMNI_MAX_MESSAGE_CHARS` | `8000` | Limite de caracteres por mensagem |
| `OMNI_MAX_BODY_BYTES` | `65536` | Limite de bytes no body (64KB) |
| `OMNI_RUNTIME_MODE` | `demo` | Modo de execução |

---

## Como aplicar no repo principal

```bash
# 1. Clonar o repo original
git clone https://github.com/misaeldasilva123ms96-commits/Projeto-Omni.git
cd Projeto-Omni

# 2. Criar o branch de remediação
git checkout -b remediation/roadmap-v2.1-replit-agent

# 3. Copiar os arquivos remediados
# (substituir pelos arquivos desta PR)

# 4. Rodar os testes
python3 -m pytest tests/ -v

# 5. Abrir a PR para main
```

---

## Checklist de Aprovação

- [x] Fase 1A — Shell Hardening
- [x] Fase 1B — Observability Sanitization
- [x] Fase 1C — Public Demo Mode
- [x] Fase 2 — Runtime Truth
- [x] Fase 3 — Tool Governance
- [x] Fase 4 — Error Taxonomy
- [x] Fase 5 — Learning Redaction
- [x] Fase 6 — Demo Container
- [x] Fase 7 — Training Safety
- [x] Fase 8 — Supabase Secret Guard
- [x] Fase 9 — Memory Isolation
- [x] Fase 10 — Provenance Metadata
- [x] Fase 11 — Rate Limiting
- [x] Fase 12 — Audit Trail
- [x] Fase 13 — Multi-Agent Safety
- [x] Fase 14 — Frontend Sanitization
- [x] Fase 15 — Training Export Pipeline
- [x] Fase 16 — Final Audit & Package
- [x] 55/55 testes passando
- [x] 137/137 gates auditados
- [ ] Push para GitHub *(pendente aprovação)*
- [ ] PR aberta para `main` *(pendente push)*
- [ ] Review pelo time *(pendente PR)*
