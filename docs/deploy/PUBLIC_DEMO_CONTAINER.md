# Public Demo Container — Phase 6 (Roadmap Oficial v2.1)

## Objetivo

Executar o Omni em modo de demo pública com isolamento de container e variáveis
de ambiente que desativam todos os recursos perigosos.

## Como executar

```bash
# Build e start
docker compose -f docker-compose.demo.yml up --build

# Somente start (após build)
docker compose -f docker-compose.demo.yml up

# Parar
docker compose -f docker-compose.demo.yml down
```

## Verificar modo demo

```bash
curl http://localhost:3001/health
# Deve retornar: {"status": "ok", ...}
```

## Variáveis de ambiente obrigatórias

| Variável | Valor | Propósito |
|---|---|---|
| `OMNI_PUBLIC_DEMO_MODE` | `true` | Bloqueia shell, debugging interno, features perigosas |
| `OMNI_ALLOW_SHELL_TOOLS` | `false` | Shell desativado mesmo se demo mode falhar |
| `OMNI_DEBUG_INTERNAL_ERRORS` | `false` | Não expõe stack traces |
| `OMNI_RATE_LIMIT_ENABLED` | `true` | Rate limiting ativo |
| `OMNI_MAX_MESSAGE_CHARS` | `8000` | Limite de tamanho de mensagem |
| `OMNI_MAX_BODY_BYTES` | `65536` | Limite de tamanho de body (64KB) |

## Política de segurança do container

- Usuário não-root: `omni` (uid 1001)
- `no-new-privileges: true`
- `cap_drop: ALL`
- Sem docker socket mount
- Sem modo privilegiado
- tmpfs em `/tmp` (64MB, sem execução)
- Limites de CPU (1 core) e memória (512MB)

## O que está desabilitado em modo demo

- Shell execution (`run_command`)
- Debug interno de erros
- Ferramentas de escrita/destrutivas
- Ferramentas de rede sem aprovação

## Adicionando API keys em produção

**NUNCA** coloque API keys no `docker-compose.demo.yml` diretamente.
Use um secrets manager ou arquivo `.env` local (nunca commitado):

```bash
# .env (local, no .gitignore)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

```bash
docker compose -f docker-compose.demo.yml --env-file .env up
```

## Gate 6: PASSED

- Demo container config existe ✅
- Executa como non-root (uid 1001) ✅
- Ferramentas perigosas desativadas por env ✅
- Documentação explica modo de demo seguro ✅
- No merge into main ✅
