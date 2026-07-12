# Roadmap Pos-Ciclo OmniRoute: Evolucao Nativa do Omni

**Status:** Proposed

**Escopo:** evolucao propria do Projeto Omni apos os PRs #490 a #496

**Governanca:** PRs pequenos, auditaveis e com merge manual exclusivo pelo Misael

## 1. Resumo executivo

O ciclo encerrado pelos PRs #490 a #496 entregou fundacoes nativas para roteamento de providers, inspecao de runtime, compressao de tokens, visibilidade de quota/custo e governanca de agentes. O proximo ciclo deve evoluir essas capacidades a partir dos contratos, riscos e objetivos do proprio Omni. OmniRoute nao e dependencia, baseline de produto nem referencia ativa para as fases abaixo.

A prioridade e transformar fundacoes estaticas e metadata-only em sinais operacionais confiaveis, mantendo Runtime Truth, redaction, fail-closed, BYOK, auditabilidade e aprovacao humana como limites permanentes. Execucao real de tools e interoperabilidade MCP/A2A somente podem avancar depois de policy explicita, threat model, ADR dedicado, testes de fronteira e aprovacao manual.

Este roadmap nao autoriza codigo, runtime, frontend, manifestos, endpoints ou integracoes. Ele ordena futuros PRs independentes e define seus criterios de aceite.

Este documento e o roadmap tematico dos trilhos nativos de provider routing, observabilidade, scoring, Provider Center, governed tool execution e MCP/A2A originados apos o ciclo #490 a #496. Ele nao e o roadmap mestre de todo o repositorio. Nao substitui `ROADMAP.md`, `docs/status/current-state.md` nem os trilhos de historical dry-run audit, API e capability governados de forma independente. Tambem nao sobrescreve nenhum PR merged ou pending fora deste trilho tematico.

## 2. Baseline do ciclo #490 a #496

Este baseline descreve somente o ciclo tematico #490 a #496. Ele nao representa o estado completo e atual de `main`.

**Document baseline:**

- main commit: `b0f3e39abbc1135234b1edf9b3136e1287e2f83d`
- includes PR #530
- snapshot date: `2026-07-12`

O PR #530 e os trilhos de historical dry-run audit nao fazem parte do escopo derivado do ciclo #490 a #496. Sua presenca no baseline registra apenas o snapshot real de `main` usado para este documento.

| PR | Estado entregue |
| --- | --- |
| #490 | Pesquisa arquitetural read-only e ADRs propostos, com limites de compliance registrados. |
| #491 | Provider Auto Routing nativo com modos deterministas, fallback auditavel, BYOK fail-closed e Runtime Truth sanitizado. |
| #492 | Runtime Inspector passou a apresentar `provider_auto_routing` por contrato publico allowlisted. |
| #493 | Token Compression Foundation opt-in, deterministica, governada e metadata-only. |
| #494 | Provider Quota & Cost Foundation baseada em diagnosticos e metadados internos opcionais, sem billing real. |
| #495 | Governed Agent Gateway interno, deterministico, metadata-only e deny-by-default para capacidades sensiveis. |
| #496 | Encerramento documental do ciclo, riscos residuais e limites de compliance consolidados. |

O Omni permanece um sistema experimental, governado e orientado por evidencias. Sucesso de transporte nao equivale a sucesso cognitivo. Toda leitura operacional deve considerar modo de runtime, provider, fallback, policy, tools, provenance e falhas sanitizadas.

## Trilhos paralelos nao substituidos por este roadmap

Continuam independentes e nao sao reabertos, substituidos ou autorizados por este roadmap:

- historical dry-run audit evidence/query service;
- protected Rust route skeleton;
- capability source `historical_audit:read`;
- Supabase capability adapter design;
- production router, que permanece unwired;
- route enablement e endpoint exposure, que permanecem governados separadamente.

Qualquer continuidade desses trilhos exige seus proprios contratos, branches, reviews e aprovacoes. Este documento nao autoriza implementacao, wiring, enablement ou exposure para nenhum deles.

## 3. Capacidades ja entregues

### 3.1 Provider auto-routing

O runtime possui modos `auto`, `auto_fast`, `auto_cheap`, `auto_coding` e `auto_safe`. A selecao usa providers registrados, disponibilidade, executabilidade, compatibilidade BYOK, hints internos e policy. Ausencia de candidato valido, bloqueio de policy ou incompatibilidade BYOK falham fechado.

### 3.2 Runtime Inspector com `provider_auto_routing`

O Runtime Inspector apresenta provider/modelo selecionado, modo, motivo, fallback, candidatos rejeitados e estado fail-closed a partir de Runtime Truth sanitizado. Credenciais, headers, payloads brutos e stack traces ficam fora do contrato publico.

### 3.3 Token compression foundation

A fundacao oferece modos `off`, `lite`, `standard` e `aggressive` para classes textuais allowlisted. A operacao e opt-in, deterministica e bloqueada diante de segredo, payload inseguro, falha de redaction, policy deny ou perda de auditabilidade. Runtime Truth recebe apenas metadados.

### 3.4 Provider quota/cost foundation

O Provider Center/Runtime Inspector aceita um resumo opcional e sanitizado de uso. Quando nao ha dados autoritativos, mostra indisponibilidade em vez de inventar quota, custo ou billing. A fundacao atual nao consulta APIs financeiras.

### 3.5 Governed agent gateway foundation

O gateway avalia capacidades internas por allowlist e deny-by-default. Capacidades seguras de leitura, inspecao e proposta podem ser representadas; escrita, shell, network, Git sensivel, acesso a credenciais e controle de provider permanecem bloqueados. Nao ha execucao real de tools.

### 3.6 Documentacao de encerramento

O estado atual, as fundacoes, os limites de compliance e os riscos residuais estao registrados. A partir deste roadmap, a evolucao deve citar contratos nativos do Omni e evidencias do repositorio, sem reabrir o escopo OmniRoute.

## 4. Principios de sequenciamento

1. Medir antes de otimizar: sinais reais e observabilidade precedem alteracoes de scoring.
2. Separar decisao de execucao: metadata, policy e simulacao precedem qualquer efeito real.
3. Uma fronteira por PR: contrato, runtime, UI e protocolo devem ter revisoes independentes quando o risco justificar.
4. Falhar fechado: ausencia, atraso, conflito, dado malformado ou fonte indisponivel nao pode ampliar autoridade.
5. Evidencia antes de enablement: nenhuma capacidade sensivel e habilitada sem testes, auditabilidade, rollback e aprovacao manual.

## 5. Proximas fases recomendadas

### Fase 1 - Sinais reais de quota, custo e latencia

Definir contratos internos para sinais obtidos apenas de fontes oficiais, consentidas e suportadas. Diferenciar valor observado, estimado e indisponivel; registrar timestamp, origem categorica, freshness e confianca sem expor payload bruto. Latencia deve separar transporte, provider e processamento local quando houver evidencia.

Nao autoriza scraping, endpoints nao oficiais, importacao sensivel de credenciais ou inferencia financeira apresentada como fato.

### Fase 2 - Observabilidade avancada

Criar agregacoes seguras para latencia, fallback, rejeicoes, fail-closed, indisponibilidade, compressao e sinais de custo/quota. Definir cardinalidade, retencao, redaction, sampling e limites de labels antes da instrumentacao. Correlacao deve usar identificadores seguros e nao carregar prompts, respostas, credenciais ou erros brutos.

### Fase 3 - Refinamento do scoring de providers

Evoluir hints estaticos para scoring explicavel baseado nos sinais confiaveis das fases anteriores. Pesos devem ser versionados, bounded e testaveis. O roteador deve registrar fatores usados, rejeicoes e fallback; sinais ausentes ou stale nao podem ser tratados como favoraveis. BYOK e policy continuam gates anteriores ao score.

### Fase 4 - Melhoria do Provider Center

Consolidar estado, origem e freshness dos sinais no Provider Center. A UI deve distinguir observado, estimado, indisponivel e stale; explicar selecao/fallback sem revelar dados sensiveis; e reduzir duplicacao com settings. A fase deve preservar contratos de frontend e nao criar autoridade de configuracao ou roteamento no cliente.

### Fase 5 - Hardening do flake local `WinError 6` em `test:security`

Isolar a causa do handle invalido no subprocesso Windows/Python, criar reproducao minima e corrigir o harness sem relaxar assertions ou pular controles. CI continua autoritativo enquanto a falha for comprovadamente ambiental, mas a meta e obter execucao local repetivel e diagnostico categorico seguro.

### Fase 6 - Documentacao operacional para auditorias diarias

Publicar runbook curto para verificacao diaria de Runtime Truth, provider health, fallback, policy denials, quota/custo, compressao, gateway e checks de seguranca. O runbook deve indicar fontes autoritativas, comandos aprovados, evidencias minimas, redaction, escalonamento e criterios de parada. Nao deve incluir segredos nem dumps brutos.

### Fase 7 - Governed tool execution com policy explicita

Projetar e implementar em etapas uma fronteira de execucao separada do gateway metadata-only. Exigir capability allowlist, schema estrito de input/output, identidade do solicitante, policy explicita, risk tier, approval gate para efeitos sensiveis, timeout, budget, idempotencia, sandbox, auditoria, cancelamento e rollback. O default permanece deny e disabled.

Esta fase nao autoriza shell/network/Git/credenciais de forma generica, execucao autonoma irrestrita ou bypass de controles existentes.

### Fase 8 - ADR separado para MCP/A2A real

Antes de qualquer implementacao, produzir ADR independente com casos de uso nativos do Omni, trust boundaries, autenticacao, autorizacao, discovery, consentimento, schema, isolamento, rate limits, replay protection, SSRF, supply chain, observabilidade, compatibilidade, rollback e public-boundary review. O ADR deve decidir explicitamente go/no-go por transporte e capacidade.

MCP/A2A real permanece bloqueado ate a aprovacao manual do ADR e de um plano de implementacao separado.

## 6. Ordem recomendada dos proximos PRs deste trilho tematico

| Ordem | PR recomendado | Tipo | Dependencia |
| --- | --- | --- | --- |
| 1 | Contrato de sinais oficiais de quota/custo/latencia | Design/contrato | Nenhuma |
| 2 | Instrumentacao server-side dos sinais aprovados | Runtime focado | PR 1 aprovado |
| 3 | Contrato e agregacoes de observabilidade avancada | Design + backend focado | PRs 1-2 |
| 4 | Scoring de providers v2 explicavel | Runtime focado | PRs 2-3 |
| 5 | Provider Center com provenance/freshness | Frontend focado | PRs 2-4 |
| 6 | Reproducao e hardening do `WinError 6` | Test/tooling | Pode ocorrer em paralelo apos PR 1 |
| 7 | Runbook de auditoria diaria | Docs-only | Sinais e observabilidade estabilizados |
| 8 | Governed tool execution - design/threat model | Docs-only | Observabilidade e policy maduras |
| 9 | Governed tool execution - fundacao disabled-by-default | Runtime isolado | PR 8 aprovado |
| 10 | ADR de MCP/A2A real | Docs-only | Policy/tool boundary comprovada |

Cada PR deve ser draft inicialmente quando CI, security review ou validacao de ambiente estiver pendente. Nenhum PR desta sequencia autoriza merge automatico.

## 7. Criterios de aceite por fase

### Fase 1

- Apenas fontes oficiais, documentadas e consentidas.
- Provenance, freshness, timestamp e categoria de confianca definidos.
- Valores observado, estimado, stale e indisponivel sao distinguiveis.
- Segredos e payloads financeiros brutos nao entram em Runtime Truth, logs ou UI.
- Ausencia/falha de fonte degrada com seguranca e nao inventa valores.

### Fase 2

- Metricas e traces usam allowlists e cardinalidade bounded.
- Latencia, fallback, rejeicao, fail-closed e indisponibilidade sao correlacionaveis.
- Nenhum prompt, resposta, token, header, cookie, stack ou erro bruto e exportado.
- Retencao, sampling, alertas e rollback estao documentados.
- Testes provam redaction e comportamento sob fonte indisponivel.

### Fase 3

- Formula, pesos e versao do score sao explicitos e deterministas para a mesma entrada.
- Policy, BYOK, executabilidade e disponibilidade permanecem gates fail-closed.
- Sinal stale/ausente nao melhora score.
- Decisao, fatores e fallback sao auditaveis por metadados seguros.
- Testes cobrem empate, falta de sinais, outliers, provider indisponivel e regressao de fallback.

### Fase 4

- Provider Center distingue observado, estimado, stale e indisponivel.
- Provenance e freshness sao legiveis sem expor payloads ou credenciais.
- Estados loading/empty/error/degraded e responsividade sao cobertos.
- Nao ha duplicacao desnecessaria de configuracao nem autoridade client-side.
- Testes de contrato, redaction, acessibilidade, typecheck e build passam.

### Fase 5

- Reproducao minima identifica pre-condicoes do `WinError 6`.
- Correcao nao pula testes, nao reduz assertions e nao mascara falhas reais.
- `npm run test:security` passa repetidamente no ambiente Windows afetado.
- Falhas restantes produzem categoria segura e orientacao operacional.
- CI permanece verde e sem comportamento especifico inseguro por plataforma.

### Fase 6

- Runbook define checklist diario, fonte autoritativa e dono da decisao.
- Evidencias sao pequenas, sanitizadas e reproduziveis.
- Ha criterios claros de pass, degraded, fail, stop e escalonamento.
- Nenhum segredo, dump bruto ou dado pessoal e solicitado.
- Merge, deploy ou reparo automatico nao fazem parte da auditoria.

### Fase 7

- Execucao nasce disabled-by-default e deny-by-default.
- Capability, identidade, policy, risk tier e approval sao validados server-side.
- Inputs/outputs sao schema-bound, bounded, sanitizados e auditaveis.
- Timeout, cancelamento, budget, idempotencia, sandbox e rollback sao testados.
- Falhas, duplicidade, indisponibilidade e configuracao invalida negam fechado.
- Nao existe autoridade por header/query/body/cookie/frontend ou allowlist somente ambiental.

### Fase 8

- ADR compara alternativas e inclui threat model e abuse cases.
- Autenticacao, autorizacao, discovery, consentimento e revogacao estao definidos.
- SSRF, replay, supply chain, rate limit, schema e isolamento possuem controles verificaveis.
- Superficies publicas e endpoints exigem review separado.
- Implementacao continua bloqueada ate aprovacao manual do Misael.

## 8. Riscos residuais

| Risco | Estado atual | Tratamento recomendado |
| --- | --- | --- |
| Scoring inicial ainda estatico | Hints internos simples nao refletem operacao em tempo real | Fases 1-3: sinais com provenance antes de score v2 |
| Quota/custo sem billing real | UI pode apenas mostrar metadados opcionais ou indisponibilidade | Fontes oficiais, valores tipados e nenhuma inferencia apresentada como fato |
| Agent gateway metadata-only | Avalia, mas nao executa tools | Preservar separacao ate policy e fronteira da Fase 7 |
| Token compression deterministica e limitada | Nao e semantica e pode reduzir contexto util | Medir qualidade/auditabilidade; manter opt-in e fail-closed |
| Flake local Windows/Python em `test:security` | `WinError 6` reduz confianca da validacao local | Reproducao minima e hardening sem relaxar o gate |
| Maior observabilidade pode elevar exposicao/cardinalidade | Novos sinais podem vazar dados ou gerar custo | Allowlists, bounds, redaction, sampling e retencao explicitos |
| Sinais externos podem ficar stale ou indisponiveis | Decisoes podem usar informacao antiga | Freshness obrigatoria; stale nunca favorece autorizacao ou score |

## 9. Regras de compliance permanentes

- Evoluir a partir dos contratos e objetivos nativos do Omni; nao reabrir escopo OmniRoute.
- Nao copiar codigo, dependencias, fluxos ou superficies do OmniRoute.
- Proibir MITM, TLS stealth, proxy/bypass, scraping e endpoints nao oficiais.
- Proibir importacao sensivel, descoberta automatica ou exposicao de credenciais.
- Usar somente APIs/fontes oficiais, consentidas e documentadas.
- Preservar BYOK fail-closed e isolamento server-side de segredos.
- Nunca registrar ou expor API keys, tokens, JWTs, headers de autorizacao, cookies, env vars, connection strings, prompts/respostas brutos, payloads de provider, stack traces, stdout/stderr ou erros brutos.
- Manter Runtime Truth allowlisted, bounded, sanitizado e honesto sobre fallback/degraded/unavailable.
- Nao tratar HTTP 200 ou sucesso de transporte como sucesso cognitivo.
- Manter capabilities sensiveis deny-by-default e features de execucao disabled-by-default.
- Nao aceitar autoridade de capability, caller, provider ou policy por frontend, body, query param, cookie ou header arbitrario.
- Exigir threat model, abuse cases, testes negativos, observabilidade segura e rollback antes de nova superficie sensivel.
- Separar MCP/A2A, tool execution, endpoints publicos e enablement em ADRs/PRs proprios.
- Nao habilitar execucao autonoma irrestrita, self-repair ou mutacao automatica de codigo/policy.
- Nao fazer push direto ou merge automatico em `main`.
- Todo merge permanece manual e exclusivo do Misael apos review e CI.

## 10. Governanca do roadmap

Este roadmap deve ser atualizado quando uma fase mudar de proposta para implementacao, quando sinais autoritativos forem introduzidos ou quando um risco residual mudar de severidade. Atualizacoes devem citar evidencia de PR e validacao do proprio Omni.

Antes de iniciar qualquer fase listada, ela deve ser comparada com o estado corrente de `main`. Branches paralelas existentes e contratos ja merged nao podem ser duplicados, contraditos ou silenciosamente substituidos. Todo PR de implementacao deve citar seus contratos predecessores exatos e o baseline corrente de `main`.

O roadmap nao concede autorizacao implicita. Cada fase requer escopo explicito, branch propria, validacoes proporcionais ao risco, draft PR quando houver pendencias e merge manual pelo Misael. Itens nao aprovados permanecem bloqueados.
