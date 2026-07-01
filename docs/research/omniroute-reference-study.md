# OmniRoute Reference Study

Data da análise: 2026-07-01

Fonte analisada: `https://github.com/diegosouzapw/OmniRoute`

Snapshot read-only: commit `1085514c56bbaf41a632f3ca56d4564d07366afa` (`1085514`, 2026-06-30, "Fix grammatical errors in readme (#5738)").

Escopo: análise arquitetural para o Projeto Omni. Este estudo não autoriza cópia de código, integração direta, merge, alteração de `main`, uso de fluxos sensíveis ou adoção sem auditoria de licença, segurança e compatibilidade.

## Resumo executivo

OmniRoute é um gateway local de IA em Node.js/TypeScript que agrega muitos provedores, expõe endpoints compatíveis com OpenAI, oferece dashboard, CLI, Electron, MCP, A2A, roteamento automático, fallback em camadas, quota/custo e compressão de tokens.

Para o Projeto Omni, o valor está na referência de arquitetura, não na importação de implementação. Os padrões mais aproveitáveis são:

- roteamento `auto/*` por pesos normalizados;
- separação entre falha de provedor, cooldown de conexão e lockout de modelo;
- simulação/explicação de decisão de rota;
- quota/custo como sinais de roteamento;
- pipeline de compressão com precedência clara e fail-open controlado;
- MCP/A2A com escopos, auditoria e superfícies reduzidas;
- dashboard operacional para explicar decisões, custos, saúde e limites.

Os principais bloqueios para adoção direta são:

- presença explícita de MITM, TLS stealth, proxy anti-deteccao, interceptação e bypass regional;
- fluxos de importação de credenciais/cookies/tokens de ferramentas e provedores;
- exposição programática ampla via MCP/A2A que pode executar ações sensíveis se mal escopada;
- dependências e optional dependencies relacionadas a proxy, fingerprint/TLS e credenciais;
- licença MIT permissiva, mas sem resolver compatibilidade de partes inspiradas em outros projetos citados no README.

Recomendação: usar como benchmark de design para Provider Center/Runtime Truth do Omni, mas implementar uma versão soberana, compliance-first e API-oficial-only. Não copiar código. Não portar MITM, TLS stealth, bypass, interceptação, importação de credenciais de apps ou fluxos que dependam de endpoints nao oficiais.

## O que o OmniRoute faz

Pelo README e manifests, OmniRoute se apresenta como um "AI gateway" local com:

- endpoint unificado em `http://localhost:20128/v1`;
- dashboard em `http://localhost:20128`;
- catalogo de provedores e modelos;
- OpenAI-compatible API e tradutores para varios formatos;
- combos de modelos/provedores;
- fallback automatico;
- tracking de free tiers, quota, custo e uso;
- compressao RTK/Caveman/LLMLingua e filtros MCP;
- MCP server e A2A server;
- CLI e pacote npm;
- app Electron;
- SQLite/LowDB/Redis opcional;
- circuit breakers, cooldowns, guardrails, rate limits, logs e auditoria.

## Stack principal

- Linguagem/runtime: TypeScript/JavaScript ESM, Node.js `>=22`.
- Framework web: Next.js 16, React 19.
- UI: dashboard Next/React, Recharts, React Flow/xyflow, lucide/material symbols, Tailwind.
- CLI: `bin/omniroute.mjs`, Commander, Ink.
- Desktop: Electron.
- Persistencia: SQLite via `better-sqlite3`, `sql.js`, LowDB legado, Redis opcional para rate limiting/infra.
- Protocolos: OpenAI-compatible HTTP, SSE, WebSocket, MCP stdio/HTTP/SSE, A2A JSON-RPC 2.0 + SSE.
- Segurança declarada: JWT, API keys, OAuth PKCE, AES-256-GCM, Zod, CORS, rate limit, guardrails.
- Dependencias sensiveis/relevantes: `@modelcontextprotocol/sdk`, `@ngrok/ngrok`, `http-proxy-middleware`, `fetch-socks`, `socks`, `selfsigned`, `node-machine-id`, `keytar`, `tls-client-node`, `wreq-js`.

`npm audit --package-lock-only --omit dev --audit-level=moderate` no snapshot clonado retornou `found 0 vulnerabilities`. Isso nao substitui SCA completo, revisao de transitive deps, Socket/Snyk/OSV, avaliacao de optional deps nem analise de comportamento.

## Estrutura de pastas

Mapa de alto nivel observado:

- `src/app`: rotas Next.js, dashboard e APIs.
- `src/sse`: handlers de chat, auth e resolucao de modelo.
- `src/lib`: servicos de quota, uso, A2A, providers, DB, seguranca, proxy e utilitarios.
- `src/shared`: constantes, schemas, componentes, validadores e utilitarios compartilhados.
- `src/mitm`: MITM/proxy/captura TLS/TPROXY/Traffic Inspector. Area nao apropriada para o Omni.
- `open-sse`: servicos de runtime, combo, auto-combo, compressao e MCP server.
- `bin`: CLI e comandos MCP/A2A.
- `electron`: app desktop.
- `docs`: arquitetura, seguranca, compressao, routing, referencias e i18n.
- `tests`: testes unitarios/e2e/integracao.
- `skills`: skills locais para MCP/A2A/CLI.
- `@omniroute`: pacotes auxiliares.

## Arquitetura de provider router

OmniRoute organiza roteamento em "combos" e `auto/*` virtual combos.

Elementos observados:

- estrategias declaradas: `priority`, `weighted`, `round-robin`, `context-relay`, `fill-first`, `p2c`, `random`, `least-used`, `cost-optimized`, `reset-aware`, `reset-window`, `headroom`, `strict-random`, `auto`, `lkgp`, `context-optimized`, `fusion`;
- estrategia interna `quota-share`;
- prefixos `auto`, `auto/coding`, `auto/fast`, `auto/cheap`, `auto/offline`, `auto/smart`, `auto/<category>:<tier>`;
- candidatos gerados a partir de conexoes ativas com credenciais validas;
- pontuacao por fatores como saude, quota, custo inverso, latencia inversa, fit de tarefa, estabilidade, tier e afinidade de contexto;
- modo `lkgp` para last-known-good path e stickiness por sessao;
- `fusion` com fan-out para painel de modelos e sintese por judge model;
- explicabilidade e metricas de decisao por rotas e dashboard.

Inspiracao para Omni: separar declaracao de estrategia, construcao de candidatos, scoring, execucao, fallback e explicacao. O Omni deve usar apenas provedores oficiais, contratos BYOK/Provider Center e runtime truth.

## Estrategias de fallback

O design documentado separa tres camadas:

- circuit breaker de provedor: falhas upstream/servico em nivel de provedor;
- cooldown de conexao/conta/chave: uma conta ruim nao desabilita todo o provedor;
- model lockout: bloqueio temporario por triple provider/conexao/modelo.

Tambem ha:

- retry cooldown-aware;
- pre-screen por quota;
- fail-open em partes de quota;
- self-healing por probes;
- exclusao temporaria de candidatos;
- degradacao quando muitos provedores estao abertos;
- backoff exponencial.

Inspiracao para Omni: preservar a granularidade. Um erro 429 ou credencial expirada deve afetar apenas a chave/conexao/modelo correspondente, nao todo o provider. A politica do Omni deve preferir fail-closed quando houver risco de compliance/seguranca e fail-open apenas para indisponibilidade de telemetria nao sensivel.

## Gerenciamento de quota/custo

OmniRoute possui:

- tracking de free tiers e "pool-deduped" quota;
- `quota-share` com planos, pools, dimensoes (`requests`, `tokens`, `usd`, percentuais), fair share e per-model caps;
- saturacao por sinais upstream;
- rotas/API para budget, quota, usage, provider limits e combo health;
- custo como sinal de roteamento (`costInv`, `cost-optimized`, relatorios e headers);
- limite por API key e no-log por chave.

Adaptacao segura para Omni:

- aproveitar a ideia de quota/custo como input de decisao;
- manter origem dos dados em Provider Center/BYOK/runtime truth;
- exigir trilha de auditoria para qualquer ajuste automatico;
- nao usar "free-tier stacking" como objetivo sem validacao de termos de cada provedor;
- nao inferir quota de endpoints nao oficiais.

## Compressao de tokens

O pipeline observado inclui:

- modos `off`, `lite`, `standard`, `aggressive`, `ultra`, `rtk`, `stacked`;
- engine registry com contrato comum (`id`, `apply`, `compress`, config schema e validacao);
- RTK para saidas de comandos/logs/testes;
- Caveman para condensacao de prosa;
- LLMLingua-2 opcional/fail-open;
- CCR/headroom/ionizer/session-dedup para compressoes estruturais e referencias;
- filtro de resultados MCP para accessibility tree/browser snapshots;
- precedencia por header, combo, profile, adaptive/auto-trigger, default;
- dashboards e APIs de preview/comparacao/configuracao.

Inspiracao para Omni:

- pipeline explicito, reversivel quando possivel e com medicao de economia;
- protecao de codigo, JSON, URLs, paths, stack traces e evidencias;
- fail-open apenas quando a compressao falha, nunca quando a integridade/seguranca falha;
- modo `off` sempre disponivel;
- telemetria comparando tokens antes/depois, qualidade e motivo da decisao.

Exige cuidado:

- compressoes semanticas podem alterar intent, requisitos legais ou dados de auditoria;
- raw output retido para recuperacao deve ter politica de retencao/redacao;
- optional dependencies de ML podem baixar modelos externos e aumentar superficie de supply chain.

## MCP/A2A

MCP observado:

- server stdio/HTTP/SSE;
- ferramentas para health, combos, quota, routing, custo, cache, compressao, modelos e simulacao;
- escopos como `read:health`, `read:combos`, `write:combos`, `write:budget`, `execute:completions`;
- audit logging com SQLite/SHA-256;
- compressao de descricoes/metadados de ferramentas.

A2A observado:

- agent card em `/.well-known/agent.json`;
- endpoint `/a2a` JSON-RPC 2.0;
- `message/send`, `message/stream`, `tasks/get`, `tasks/cancel`;
- skills como `smart-routing`, `quota-management`, `provider-discovery`, `cost-analysis`, `health-report`;
- metadados de explicacao, custo, trace de resiliencia e policy verdict.

Inspiracao para Omni:

- expor runtime truth e provider routing como capacidades auditaveis;
- escopos minimos por ferramenta;
- dry-run/simulate/explain antes de mutacoes;
- separacao forte entre leitura, escrita, execucao e administracao.

Risco:

- MCP/A2A que altera budget, combos, resiliencia, cache ou executa completions vira superficie de controle remoto;
- precisa de kill-switch, allowlist de tools, rate limit, auditoria, redacao e escopo por tenant/ator.

## Dashboard

O dashboard cobre:

- provedores e conexoes;
- combos/roteamento;
- free tiers;
- logs, proxy logs, console/activity;
- quota, limites, budget, provider health;
- MCP/A2A;
- compressao, Compression Studio e analytics;
- settings de auth, proxy, MITM, oneproxy, quota-store, task-routing;
- screenshots e fluxo onboarding.

Inspiracao para Omni:

- explicar por que um provider foi escolhido;
- mostrar custo estimado/real e quota restante;
- visualizar fallback/circuit breaker/model lockout;
- permitir simulacao read-only antes de aplicar estrategia;
- separar paineis de controle de paineis de observabilidade.

## Segurança

Pontos positivos documentados:

- policy de vulnerabilidades;
- JWT, API keys e OAuth PKCE;
- AES-256-GCM para campos sensiveis quando `STORAGE_ENCRYPTION_KEY` esta configurado;
- fail-fast para secrets fracos;
- API keys com HMAC/CRC e permissoes;
- Zod para validacao;
- CORS/rate limit;
- guardrails PII/prompt-injection/vision;
- logs/auditoria/no-log por chave;
- rota guard tiers e gerenciamento de escopos;
- gitleaks, secret checks e docs de public credentials;
- `npm audit` sem vulnerabilidades moderadas+ no lockfile de producao analisado.

Riscos/alertas:

- `STORAGE_ENCRYPTION_KEY` vazio ativa passthrough/plaintext em desenvolvimento;
- README e docs promovem TLS fingerprint spoofing, stealth, proxy anti-deteccao, MITM e TPROXY decrypt;
- existem rotas e docs para importacao/aplicacao local de credenciais de Codex/Claude/Antigravity/Zed/CLIProxy;
- web-cookie/session-token providers e no-auth providers ampliam risco de ToS, privacidade e abuso;
- proxy relays em Cloudflare/Vercel/Deno/ngrok podem mascarar origem e criar risco de abuso se mal protegidos;
- MCP/A2A remoto com ferramentas de escrita/executar completions deve ser tratado como administracao sensivel;
- telemetria de request phases fica em memoria, mas logs de proxy/usage/MCP e DB podem conter metadados sensiveis se redacao falhar;
- `selfsigned`, `tls-client-node`, `wreq-js`, `socks`, `fetch-socks`, `http-proxy-middleware`, `@ngrok/ngrok` exigem revisao extra;
- o proprio repo reconhece que scanners SCA podem sinalizar MITM/root-CA/credential import.

## Licença

O repositorio raiz declara MIT License, copyright 2026 diegosouzapw.

MIT permite uso, copia, modificacao, distribuicao, sublicenciamento e venda, desde que o aviso de copyright e permissao sejam preservados.

Mesmo assim, para o Projeto Omni:

- nao copiar codigo sem revisao legal;
- verificar se todos os subpacotes e assets tambem sao MIT ou compativeis;
- revisar referencias a projetos inspiradores citados no README, pois a licenca deles pode impor condicoes proprias;
- revisar imagens, logos de provedores, screenshots e dados de pricing/free tiers;
- registrar qualquer decisao de aproveitamento em ADR e SBOM/licensing notes.

## Mapa de features

| Area | Evidencia no OmniRoute | Classificacao para Omni |
| --- | --- | --- |
| Provider routing `auto/*` | Auto-combo por candidatos ativos e scoring ponderado | Pode inspirar |
| Multi-fator scoring | Saude, quota, custo, latencia, tarefa, estabilidade | Pode inspirar |
| Fallback em camadas | Provider circuit breaker, connection cooldown, model lockout | Pode inspirar |
| Quota/custo | Pools, per-key caps, budget, cost reports | Pode ser adaptado com cuidado |
| Token compression | RTK, Caveman, LLMLingua, CCR, session-dedup | Pode ser adaptado com cuidado |
| MCP | Tools com escopos e auditoria | Pode ser adaptado com cuidado |
| A2A | Agent card, JSON-RPC, skills, SSE | Pode ser adaptado com cuidado |
| Dashboard | Provider health, combos, quota, cost, compression | Pode inspirar |
| Guardrails | PII, prompt injection, vision bridge | Pode inspirar |
| MITM/TPROXY | TLS intercept, root CA, transparent decrypt | Nao deve entrar no Omni |
| TLS stealth/fingerprint | JA3/JA4, header/body ordering, anti-detection | Nao deve entrar no Omni |
| Proxy/bypass regional | oneproxy, relays, geo-bypass messaging | Nao deve entrar no Omni |
| Credential import | zip extract, apply-local, keychain/cookie/session imports | Exige auditoria profunda; default nao |
| No-auth/free endpoints | provedores sem credenciais e free-tier stacking | Exige auditoria profunda |
| Fusion/judge | fan-out e sintese por judge | Exige auditoria profunda por custo/privacidade |
| Optional ML deps | LLMLingua/transformers/model downloads | Exige auditoria profunda |

## Comparação OmniRoute vs Projeto Omni

| Dimensao | OmniRoute | Projeto Omni |
| --- | --- | --- |
| Postura | Gateway local pragmatica, amplo suporte a CLIs/proxies/free tiers | Compliance-first, Provider Center, BYOK, runtime truth, governanca |
| Provider model | Muitos provedores, inclusive web/OAuth/no-auth/proxy | Deve priorizar provedores oficiais e contratos auditaveis |
| Routing | Combos e auto-combo com scoring dinamico | Pode adotar estrategia auto, mas sob policy/governance |
| Fallback | Aggressivo, com auto-healing e fail-open em partes | Deve preservar fail-closed para compliance e auth |
| Quota/custo | Otimizacao de free/cheap/quota | Deve integrar a billing/runtime truth e limites do tenant |
| Compressao | Economia agressiva de tokens | Deve ser opt-in/policy-controlled, com integridade e redacao |
| MCP/A2A | Controle amplo do gateway por agentes | Deve ser tool-scoped, tenant-scoped e auditavel |
| Dashboard | Operacional e abrangente | Pode inspirar explicabilidade e cockpit |
| Segurança sensivel | Inclui MITM, stealth, proxy anti-detection | Deve excluir esses fluxos |
| Licenca | MIT no root | Precisa revisao legal/SBOM antes de qualquer reaproveitamento |

## Ideias aproveitáveis

### Pode inspirar o Omni

- Provider router com candidatos dinamicos e estrategias declarativas.
- `auto/<perfil>` como API ergonomica para estrategias: `auto`, `auto/coding`, `auto/fast`, `auto/cheap`, `auto/offline`.
- Peso normalizado por saude, custo, quota, latencia, fit de tarefa e estabilidade.
- Last-known-good path com stickiness por sessao.
- Separacao de falha por provedor/conexao/modelo.
- Dashboard de explicacao de rota e fallback.
- Simulacao de rota e estimativa de custo antes da execucao.
- Circuit breaker e cooldown com observabilidade.
- Guardrails como pipeline registravel.
- Compression preview e comparacao antes de ativacao.

### Pode ser adaptado com cuidado

- Quota-share, fair-share e per-model caps.
- Cost-aware routing e budget guard.
- Compression pipeline e filtros de outputs de ferramentas.
- MCP/A2A com escopos granulares.
- Fusion/judge, apenas para casos autorizados e com limites de custo/privacidade.
- Optional local ML compression, apenas com modelo fixado, cache controlado e SBOM.
- Free-tier catalog, apenas como metadado informativo validado contra termos oficiais.

### Não deve entrar no Omni

- MITM, TPROXY decrypt, root CA dinamica, interceptacao TLS.
- TLS stealth, JA3/JA4 spoofing, header/body ordering para imitar clientes oficiais.
- Geo-bypass, anti-detection, proxy marketplace e relay para mascarar origem.
- Automacoes contra endpoints nao oficiais ou fluxos que dependam de cookies de sessao web.
- Importacao automatica de credenciais de ferramentas locais sem consentimento forte, revisao legal e threat model.
- Bypass de assinaturas, obfuscation anti-classifier ou qualquer mecanismo para contornar controles de provedor.

### Exige auditoria profunda

- Licenca de todos os subcomponentes, assets e projetos inspiradores.
- Storage de credenciais e modo plaintext quando encryption key nao existe.
- Cloud sync/credential write-back e assinatura de payload.
- Web-cookie/session-token providers.
- No-auth providers e free-tier stacking.
- MCP/A2A remoto com ferramentas de escrita.
- Dependencias de proxy/TLS/self-signed/ngrok/keychain.
- Logs de proxy, usage, MCP audit e retencao.
- Rotas `apply-local`, `zip-extract`, `import-bulk`, keychain import e OAuth imports.

## Riscos

### Segurança

- Superficie sensivel de MITM/proxy/stealth nao e compatível com a postura de compliance do Omni.
- Ferramentas MCP/A2A podem virar plano de controle remoto.
- Rotas de importacao de credenciais e alteracao local podem criar escalation ou vazamento se expostas.
- Dependencias nativas/optional deps ampliam risco de supply chain.

### Privacidade

- Logs de proxy, roteamento, MCP, custo, quota e compression analytics podem reter metadados de prompts, modelos, contas e provedores.
- Compressao e CCR/session-dedup podem armazenar blocos de contexto reutilizaveis.
- Fusion envia o mesmo prompt para varios modelos/provedores.

### Armazenamento de chaves

- A criptografia de campos depende de `STORAGE_ENCRYPTION_KEY`.
- Sem chave, ha passthrough/plaintext para conveniencia de dev.
- Importacao de OAuth/cookies/tokens exige consentimento, redacao e isolamento por tenant.

### Telemetria

- Telemetria operacional e util, mas precisa de redacao, retencao e opt-out por chave/tenant.
- Headers de custo e usage devem evitar expor dados de outro tenant.

### Dependências

- `selfsigned`, proxy libraries, `tls-client-node`, `wreq-js`, `keytar`, `ngrok` e ML optional deps precisam de SCA/behavior review.
- `npm audit` do lockfile de producao nao encontrou vulnerabilidades moderadas+, mas isso e apenas um sinal inicial.

### Endpoints não oficiais

- Varios fluxos parecem suportar CLIs/provedores por OAuth publico, cookies, web tokens, assinatura e headers especificos.
- Para Omni, usar apenas APIs oficiais, contratos documentados e termos validados.

### MITM/proxy/TLS stealth

- Deve ser exclusao explicita.
- Nao portar docs, UX, rotas, dependencias ou automacoes relacionadas.

### Licença

- MIT no root e permissiva, mas nao basta.
- Necessario revisar subpacotes, assets, dados de pricing/free tiers, forks, inspiracoes e qualquer codigo gerado/copilado.

## Recomendação final

Usar OmniRoute como referencia arquitetural limitada para:

- estrategia `auto` de provider routing;
- fallback granular;
- quota/cost-aware routing;
- explicabilidade operacional;
- pipeline de compressao;
- MCP/A2A governado por escopos;
- dashboard de runtime truth.

Nao usar OmniRoute como base de codigo. Nao copiar implementacoes. Nao adotar qualquer parte de MITM, TLS stealth, proxy anti-detection, geo-bypass, web-cookie/session-token scraping, importacao de credenciais de CLIs ou endpoints nao oficiais.

O caminho seguro e desenhar ADRs proprios no Omni e implementar os conceitos sobre Provider Center, BYOK, runtime truth, governanca, tokens, fallback e observabilidade ja existentes.

## Roadmap seguro para eventual adaptação no Omni

1. Criar inventario interno dos provedores oficiais ja suportados pelo Provider Center.
2. Definir contrato `ProviderRouteCandidate` com sinais de saude, custo, quota, latencia, capacidade e compliance.
3. Implementar `simulateRoute` read-only antes de qualquer roteamento automatico.
4. Adicionar estrategias `auto`, `cost-aware`, `quota-aware`, `lkgp` e `balanced` como policy-driven.
5. Separar fallback em provider breaker, connection cooldown e model lockout.
6. Registrar toda decisao de rota em runtime truth com redacao.
7. Adicionar cockpit de explicacao: candidato escolhido, candidatos rejeitados, motivo, custo estimado e quota.
8. Criar pipeline de compressao opt-in com `off` default, preview, medicao e protecao de evidencias.
9. Adicionar MCP/A2A somente leitura primeiro: health, quota, route simulation, cost report.
10. Liberar ferramentas de escrita apenas com escopos, tenant policy, auditoria, kill-switch e aprovacao.
11. Rodar threat model e legal review antes de qualquer suporte a provider novo.
12. Bloquear explicitamente MITM, TLS stealth, bypass, proxy anti-detection e endpoints nao oficiais nos guardrails de arquitetura.

## Evidências consultadas

- `README.md`
- `package.json`
- `.env.example`
- `LICENSE`
- `SECURITY.md`
- `docs/routing/AUTO-COMBO.md`
- `docs/architecture/RESILIENCE_GUIDE.md`
- `docs/compression/COMPRESSION_ENGINES.md`
- `open-sse/mcp-server/README.md`
- `src/lib/a2a/README.md`
- `src/shared/constants/routingStrategies.ts`
- `open-sse/services/combo.ts`
- `src/lib/quota/enforce.ts`
- `src/lib/db/encryption.ts`
- `src/shared/utils/requestTelemetry.ts`
- `docs/security/MITM-TPROXY-DECRYPT.md`
- `docs/security/STEALTH_GUIDE.md`
- `docs/security/SOCKET_DEV_FINDINGS.md`
