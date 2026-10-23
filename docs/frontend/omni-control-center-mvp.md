# Omni Control Center — MVP somente leitura

**Branch de implementação:** `feat/omni-control-center-readonly-20261023`  
**Base original da main:** `bbec59575c5ce2e9bad3b124f3d38f4c5242c04c`  
**Política:** não realizar merge automático; revisão e merge somente pelo mantenedor.

## Escopo entregue nesta branch

- Rota `/control-center` integrada ao shell e sidebar atuais.
- Proteção por sessão Supabase usando o gate existente; dados internos continuam protegidos também pelo backend Rust.
- Mapa clicável e descritivo das quatro camadas documentadas: React/Vite, Rust/Axum, Python Brain e Node/QueryEngine.
- Polling HTTP de `/api/v1/status`, `/api/v1/runtime/signals/summary`, `/api/v1/milestones/summary` e `/api/v1/strategy/summary`, a cada 15 segundos.
- Detalhes de Runtime Truth preferindo `/api/v1/operator/runtime/signals` com JWT e fallback legado `/internal/runtime-signals` — nunca reinterpretados como garantia de execução completa.
- Evento em tempo real por `/api/observability/stream-ticket` e `/api/observability/stream`, reaproveitando o hook de SSE com reconexão e snapshot inicial autenticado.
- Configuração/saúde de provedores pelo `GET /api/v1/settings/providers`, lida a cada 60 segundos, sem expor credenciais e sem disparar testes automáticos.
- Cadastro local de agentes mostrado explicitamente como **configuração do navegador**, e não como processo/worker em execução.
- Runs governados consultados por GET /api/control/runs, com capacidade run_control:read e escopo do operador; projeção limitada sem metadata. Estado `running` registrado não é heartbeat de um agente.
- Tokens históricos de sessões acessíveis, identificados como amostra. Não se apresenta custo financeiro sem base de preços/billing.
- Estados vazios, indisponibilidade por fonte, timestamps de leitura, atualização manual e testes de semântica de saúde.

## Fontes, cadência e confiança

| Bloco | Fonte | Atualização | Restrição |
| --- | --- | --- | --- |
| Estado do serviço e resumos | Rust `/api/v1/*` | 15 s | Público, dado reduzido |
| Último runtime | Operador + legado interno | 15 s | Bearer Supabase; degradar quando negado |
| Observabilidade | SSE + snapshot autenticado | Stream; em geral ~2 s | Ticket efêmero, sessão autenticada |
| Provedores | API de configurações | 60 s | Saúde só é afirmada com `health_valid=true` |
| Agentes | `fetchAgents()` | Inicial/manual | Armazenamento local; status não é execução |
| Runs governados | GET `/api/control/runs` | 60 s | Capability `run_control:read`, filtragem por operador; status do registro não prova liveness |
| Tokens | `fetchTokenUsage()` | Inicial/manual | Amostra derivada de mensagens acessíveis |
| Cobrança monetária | Não disponível | — | Mostrar "indisponível", nunca R$ fictício |

### Guardrails

1. Nenhum novo endpoint administrativo, execução remota, comando de shell, mutation ou proxy de segredos.
2. `/control-center` exige sessão, mas endpoints Rust preservam autorização e sanitização independentes.
3. Não confundir `rust_service`, `status=success` ou HTTP 200 com `FULL_COGNITIVE_RUNTIME`.
4. Provedor apenas configurado não é "conectado", e cadastro de agente ativo não é worker rodando; run marcado `running` não prova heartbeat.
5. Manter a UI operacional no escopo read-only; sem efeito colateral no polling.
6. Distinguir leitura recente de disponibilidade real: SSE tem estado próprio e leitura HTTP tem timestamp.
7. Os dados apresentados devem permanecer redigidos/sanitizados conforme a política do Omni.

## Gap analysis / implementação futura

### P1 — Telemetria real de execução dos agentes

Criar read model **autenticado** e limitado para agentes, com `agent_id`, `run_id`, `status` derivado de heartbeat/execução, `started_at`, `last_seen_at` e origem. Nunca usar dados de localStorage como status operacional. Definir contrato e testes Rust/Python antes de adicionar à tela.

### P2 — Custos verificáveis

Consolidar uso de tokens por requisição, modelo, provedor e preço **versionado**; vincular a registros de execução e permitir `estimated_cost` separado de `billed_cost` (somente com integração oficial). Não fazer inferência silenciosa, nem somar snapshots duplicados. Respeitar quotas e limites de acesso.

### P3 — Timeline unificada

Unificar eventos de SSE com diagnósticos de `provider_auto_routing`, `token_compression`, `tool_execution`, `fallback_triggered` e `execution_provenance` num read model sanitizado, com IDs de correlação por run. Necessário contrato novo; não interpretar descrições genéricas como campos confirmados.

### P4 — Operação de longa duração

Implementar status derivado de liveness do stream, alertas, refresh backoff, retenção limitada, paginação e monitoração de drift/erros da API. Evitar polling de listas muito extensas.

## Validação requerida antes do merge

- `cd frontend && npm ci && npm run typecheck && npm test && npm run build`
- Testar rota `/control-center` com e sem sessão.
- Forçar Rust offline: painel deve mostrar ausência/erro, nunca estado online inventado.
- Forçar SSE desconectado: snapshot inicial pode permanecer visível com origem correta; status SSE não pode ser "ao vivo".
- Provedores: configured sem `health_valid` = sem teste válido.
- Runs: acesso sem capability deve degradar somente este painel; garantir que metadata/resolution nunca sejam expostos.
- Expor dados sensíveis nos payloads de teste para verificar redação.
- Validar acessibilidade (teclado, rótulos e mobile) e tempo de refresh.
- Verificar que `main` permanece idêntica e o PR está em draft.

**Aviso:** este é um MVP de integração de frontend com contratos atuais, não um novo runtime. Fluxos novos de custos reais e liveness de workers dependem de contratos de backend ainda não implementados.
