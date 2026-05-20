# Service Migration Plan — Phase 10 (Roadmap Oficial v2.1)

Branch sugerida: `architecture/service-migration-10`

## Objetivo

Migrar Python Brain e Node Query Engine de subprocessos (`child_process` / `subprocess`)
para serviços HTTP persistentes, com suporte a circuit breaker e rollback imediato.

---

## Estado atual (baseline)

| Componente | Modo atual | Ponto de entrada |
|---|---|---|
| Python Brain | Subprocess (stdio) | `backend/python/app/main.py` |
| Node Query Engine | Subprocess (child_process) | `core/brain/queryEngineAuthority.js` |
| Rust API | Cliente de subprocesso | `backend/rust/src/main.rs` → `call_python()` |

---

## Migração incremental — 4 sub-fases

### 11A — Python HTTP Service Spike

**Branch:** `architecture/python-service-11a`

Novos endpoints:

```
POST /internal/brain/run
GET  /internal/brain/health
GET  /internal/brain/readiness
```

Regras:
- CLI antigo (`python main.py`) continua 100% funcional.
- O novo server HTTP é levantado APENAS se `OMNI_PYTHON_MODE=service`.
- Porta padrão: `OMNI_PYTHON_INTERNAL_PORT=7001` (não exposta publicamente).
- Framework: FastAPI ou Starlette (já disponível).
- Request/response schema: igual ao contrato atual de `call_python()`.

Estimativa: 2–3 dias de desenvolvimento, 1 dia de testes.

---

### 11B — Node HTTP Service

**Branch:** `architecture/node-service-11b`

Novos endpoints:

```
POST /internal/query-engine/run
GET  /internal/query-engine/health
GET  /internal/query-engine/readiness
```

Regras:
- Runner antigo (`child_process`) continua funcional.
- Novo server ativo apenas se `OMNI_NODE_MODE=service`.
- Porta padrão: `OMNI_NODE_INTERNAL_PORT=7002`.
- Framework: Express (já disponível no projeto).

Estimativa: 2 dias de desenvolvimento, 1 dia de testes.

---

### 11C — Rust Internal Client

**Branch:** `architecture/rust-client-11c`

Modos controlados por env:

```
OMNI_PYTHON_MODE=subprocess|service   (default: subprocess)
OMNI_NODE_MODE=subprocess|service     (default: subprocess)

# Aliases para retrocompatibilidade:
OMINI_PYTHON_MODE
OMINI_NODE_MODE
```

Regras:
- Modo `subprocess`: comportamento atual, sem mudanças.
- Modo `service`: Rust faz HTTP POST para o serviço interno.
- Timeout configurável: `OMNI_INTERNAL_SERVICE_TIMEOUT_MS` (default 30000).

Estimativa: 2–3 dias de desenvolvimento.

---

### 11D — Circuit Breaker

**Branch:** `architecture/circuit-breaker-11d`

Comportamento quando o serviço persistente cai:

1. `circuit_open` → fallback controlado
2. Opcional: fallback para subprocess antigo se `OMNI_ALLOW_SUBPROCESS_FALLBACK=true`
3. Resposta pública: `PROVIDER_UNAVAILABLE` (via `errorCodes.js` / `errors.py`)
4. Evento de telemetria: `runtime_circuit_open`

Estados:
- `CLOSED`: serviço saudável, operação normal.
- `OPEN`: falhas recentes acima do threshold, sem tentar.
- `HALF_OPEN`: tentativa de recuperação a cada N segundos.

Thresholds (configuráveis por env):
```
OMNI_CIRCUIT_FAILURE_THRESHOLD=3
OMNI_CIRCUIT_RESET_TIMEOUT_MS=30000
```

Estimativa: 2 dias de desenvolvimento.

---

## Compatibilidade com subprocessos

**Regra de ouro:** nunca remover o caminho de subprocesso antes do serviço HTTP
passar em produção por 72 horas estável.

Checklist de compatibilidade:
- [ ] `call_python()` no Rust mantém assinatura idêntica
- [ ] Env `OMNI_PYTHON_MODE=subprocess` retorna exatamente ao comportamento atual
- [ ] CLI Python `python main.py` continua funcional independentemente
- [ ] Testes de regressão em `tests/security/` continuam passando em ambos os modos

---

## Rollback

Se qualquer serviço HTTP persistente falhar em produção:

```bash
# Reverter imediatamente para subprocess:
OMNI_PYTHON_MODE=subprocess
OMNI_NODE_MODE=subprocess

# Restart da API Rust
# Nenhuma mudança de código necessária.
```

---

## Estimativas

| Sub-fase | Esforço estimado | Dependência |
|---|---|---|
| 11A Python HTTP | 3–4 dias | Nenhuma |
| 11B Node HTTP | 2–3 dias | Nenhuma (paralela a 11A) |
| 11C Rust Client | 2–3 dias | 11A + 11B concluídos |
| 11D Circuit Breaker | 2 dias | 11C concluído |
| **Total** | **~2 semanas** | |

---

## Gate 10: PASSED

- [x] Plano de migração existe (`docs/architecture/SERVICE_MIGRATION_PLAN.md`)
- [x] Migração é incremental (4 sub-fases com feature flags)
- [x] Compatibilidade com subprocesso documentada
- [x] Rollback documentado (basta alterar env)
- [x] Estimativas documentadas
- [x] Nenhum comportamento de runtime foi alterado nesta fase
- [x] Sem merge direto em main
