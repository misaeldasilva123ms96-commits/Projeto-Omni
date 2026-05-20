# Public Demo Readiness — Phase 14 (Roadmap Oficial v2.1)

Branch sugerida: `release/public-demo-readiness-14`

---

## Variáveis de ambiente obrigatórias para demo pública

```bash
OMNI_PUBLIC_DEMO_MODE=true
OMNI_ALLOW_SHELL_TOOLS=false
OMNI_DEBUG_INTERNAL_ERRORS=false
OMNI_RATE_LIMIT_ENABLED=true
OMNI_MAX_MESSAGE_CHARS=8000
OMNI_MAX_BODY_BYTES=65536

# Aliases para retrocompatibilidade
OMINI_PUBLIC_DEMO_MODE=true
OMINI_ALLOW_SHELL_TOOLS=false
```

---

## Checklist de segurança para demo pública

### Execução e ferramentas

| Item | Status | Implementado em |
|---|---|---|
| Shell bloqueado por padrão | ✅ | `run_command.py` — Gate 1A |
| Ferramentas destrutivas bloqueadas | ✅ | `queryEngineAuthority.js` — Gate 3 |
| Debug interno desativado | ✅ | `run_command.py`, env flag — Gate 1A |
| Ferramentas de demo pública bloqueadas via `OMNI_PUBLIC_DEMO_MODE` | ✅ | `evaluateToolGovernanceJS()` — Gate 3 |

### Payload e dados

| Item | Status | Implementado em |
|---|---|---|
| Backend payload sanitizado (sem stack trace, tokens, paths) | ✅ | `cognitive_runtime_inspector.py` — Gate 1C |
| Frontend payload sanitizado (sem campos internos) | ✅ | `runtimeDebugSanitizer.ts` / `RuntimePanel.tsx` — Gate 1D |
| Secrets não expostos (Supabase key removida de exports) | ✅ | `supabaseClient.js` — Gate 4 |
| PII redacted nos logs de aprendizado | ✅ | `learning_logger.py` — Gate 1E |

### Inputs e rede

| Item | Status | Implementado em |
|---|---|---|
| Tamanho de mensagem limitado (8000 chars) | ✅ | `main.rs` — Gate 5 |
| Control chars rejeitados | ✅ | `main.rs` — Gate 5 |
| Session ID validado (alphanum, max 128) | ✅ | `main.rs` — Gate 5 |
| Rate limiting ativo (env flag) | ✅ | `OMNI_RATE_LIMIT_ENABLED` — Gate 5 |

### Transparência e observabilidade

| Item | Status | Implementado em |
|---|---|---|
| Runtime truth visível nas respostas | ✅ | `queryEngineAuthority.js` — Gate 2 |
| Fallback labeled publicamente | ✅ | `runtime_truth.fallback_triggered` — Gate 2 |
| Matcher labeled (nunca finge ser provider) | ✅ | `runtime_truth.matcher_used` — Gate 2 |
| Provider unavailable labeled | ✅ | `errorCodes.js` + `errors.py` — Gate 8 |
| Códigos de erro públicos centralizados | ✅ | `errorCodes.js` / `errors.py` — Gate 8 |

### Container e infraestrutura

| Item | Status | Implementado em |
|---|---|---|
| Container docs disponível | ✅ | `docs/deploy/PUBLIC_DEMO_CONTAINER.md` — Gate 6 |
| Executa como non-root (uid 1001) | ✅ | `Dockerfile.demo` — Gate 6 |
| `cap_drop: ALL` | ✅ | `docker-compose.demo.yml` — Gate 6 |
| Sem docker socket mount | ✅ | `docker-compose.demo.yml` — Gate 6 |
| Limites de CPU/memória definidos | ✅ | `docker-compose.demo.yml` — Gate 6 |

### Testes

| Item | Status | Implementado em |
|---|---|---|
| Security regression tests existem | ✅ | `tests/security/test_security_regression.py` — Gate 7 |
| Testes cobrem todos os gates de segurança | ✅ | 9 classes de teste — Gate 7 |

---

## Limitações conhecidas para demo pública

As limitações abaixo devem ser documentadas explicitamente para usuários da demo:

| Limitação | Motivo | Plano |
|---|---|---|
| Shell/bash indisponível | Bloqueado por segurança em modo demo | Fase 11 — feature flag avançado |
| Ferramentas de escrita de arquivo indisponíveis | Bloqueado por governança demo | Fase 11 |
| Memória persistente pode estar indisponível | Supabase requer configuração externa | Fase 10/11 |
| Rate limiting pode rejeitar requisições | Proteção de demo pública | Comportamento esperado |
| Classificador de intent baseado em regex | Não usa embedding/LLM ainda | Fase 12 |
| Serviços Python/Node via subprocess | Serviços HTTP persistentes são Fase 11 | Fase 11 |

---

## Procedimento de verificação pré-publicação

```bash
# 1. Build do container de demo
docker compose -f docker-compose.demo.yml build

# 2. Start
docker compose -f docker-compose.demo.yml up -d

# 3. Health check
curl http://localhost:3001/health

# 4. Verificar shell bloqueado
curl -X POST http://localhost:3001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "run bash command"}'
# Esperado: error_public_code: TOOL_BLOCKED_PUBLIC_DEMO ou SHELL_TOOL_BLOCKED

# 5. Verificar input muito longo rejeitado
python3 -c "print('A' * 9000)" | \
  curl -X POST http://localhost:3001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "'$(python3 -c "print('A'*9000)'"}"}'
# Esperado: 400 Bad Request, message exceeds maximum length

# 6. Rodar security regression tests
pytest tests/security/test_security_regression.py -v

# 7. Parar container
docker compose -f docker-compose.demo.yml down
```

---

## Gate 14: PASSED

- [x] Modo demo pública funciona com envs obrigatórias
- [x] Operações perigosas bloqueadas (shell, destrutivas, network sem aprovação)
- [x] UI exibe diagnósticos seguros (runtime_truth visível, fallback labeled)
- [x] Security regression tests documentados e existem
- [x] Limitações conhecidas documentadas explicitamente
- [x] Sem merge direto em main
