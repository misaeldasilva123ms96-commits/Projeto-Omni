# Medium Alerts Remediation Report - Projeto Omni

## 1. Resumo executivo

- Branch: `hardening/medium-audit-alerts-remediation`
- Base: `origin/main` at `bdd894c`
- Objetivo: Remediar alertas medios de auditoria em CI, Autonomy receipts, dependencias, deploy e governanca de merge manual.
- Resultado: Correcoes aplicadas; checks criticos diretamente afetados passaram, com falhas residuais documentadas em suites amplas/ambiente local.
- Risco residual: `npm test` amplo e `tests/runtime` amplo ainda exigem revisao separada; Docker nao pode ser validado sem daemon local.

## 2. Alteracoes realizadas

| Area | Arquivo | Alteracao | Motivo |
| --- | --- | --- | --- |
| CI | `.github/workflows/ci.yml` | Frontend build e typecheck separados e bloqueantes; public demo bloqueante; audits Node/Cargo explicitos como advisory. | Evitar mascaramento de falhas criticas e manter audits permitidos como nao bloqueantes documentados. |
| CI | `.github/workflows/security.yml` | Node audit, pip-audit e cargo audit renomeados como advisory com mensagem explicita. | Remover `|| true` silencioso em auditorias informativas. |
| CI | `.github/workflows/omni-security-ci.yml` | Node audit e DevSkim rotulados como advisory; security regression permanece bloqueante. | Preservar regressao de seguranca como gate obrigatorio. |
| CI | `.github/workflows/lint.yml` | Clippy Rust tornou-se bloqueante; linters JS/Python permanecem advisory com mensagem explicita. | Bloquear `cargo clippy --all-targets --all-features -- -D warnings` sem ampliar instabilidade de lint legado. |
| CI | `.github/workflows/omni-rust-ci.yml` | Clippy usa `--all-targets --all-features`; testes Rust usam `cargo test --locked --all`. | Alinhar o gate Rust dedicado aos comandos obrigatorios. |
| Deploy | `.github/workflows/deploy.yml` | Wrangler Pages deploy pula apenas sem token; com token definido, falha de deploy falha o step. | Evitar mascarar falha real de deploy sem expor token. |
| Runtime | `backend/python/brain/runtime/autonomy/autonomy_controller.py` | Adicionado helper `_decide_and_record()` compartilhado por `decide()` e `decide_with_report()`. | Garantir exatamente um receipt por decisao. |
| Testes | `backend/python/tests/runtime/autonomy/test_autonomy_controller.py` | Adicionados asserts para contagem unica de receipts, stats e advisory-only. | Cobrir regressao de dupla contabilizacao. |
| Rust | `backend/rust/src/run_control.rs` | Ajustado helper de teste `seed_run()` de `&PathBuf` para `&Path`. | Corrigir lint `clippy::ptr-arg` exposto pelo gate bloqueante. |
| Dependencias | `docs/audit/dependency-pr-triage.md` | Criada triagem de PRs de dependencias. | Documentar ausencia atual de PRs abertas e ordem manual futura. |

## 3. CI hardening

Checks que passaram a ser bloqueantes:

- Frontend build em `.github/workflows/ci.yml`.
- Frontend typecheck em `.github/workflows/ci.yml`.
- Public Demo Validation em `.github/workflows/ci.yml`.
- `cargo clippy --all-targets --all-features -- -D warnings` em `.github/workflows/lint.yml` e `.github/workflows/omni-rust-ci.yml`.
- Rust tests com `cargo test --locked --all` em `.github/workflows/omni-rust-ci.yml`.
- Security Regression Suite permanece bloqueante em `.github/workflows/omni-security-ci.yml`.
- Gitleaks permanece bloqueante em `.github/workflows/security.yml` e `.github/workflows/ci.yml`.

Checks que permanecem advisory:

| Check | Workflow | Justificativa | Risco residual |
| --- | --- | --- | --- |
| `npm audit` | `ci.yml`, `security.yml`, `omni-security-ci.yml` | Pode conter dependencias transitivas sem correcao imediata; logs agora declaram advisory. | Findings devem ser revisados manualmente. |
| `pip-audit` | `security.yml` | Pode conter excecoes conhecidas/transitivas; logs agora declaram advisory. | Findings devem ser revisados manualmente. |
| `cargo audit` | `ci.yml`, `security.yml` | Instalacao do `cargo-audit` pode ser instavel no ambiente; logs agora declaram advisory. | Findings devem ser revisados manualmente. |
| ESLint, Prettier, Black, Flake8, Pylint | `lint.yml` | Mantidos informativos para evitar instabilidade ampla fora do escopo critico. | Pode haver divida de estilo nao bloqueante. |

## 4. Autonomy Controller

A causa auditada era o risco de `decide_with_report()` depender de `decide()` e registrar ou reconstruir receipts de forma divergente. A solucao aplicada centraliza a avaliacao, criacao de receipt, registro e evento em `_decide_and_record()`.

`decide()` continua retornando apenas `AutonomyDecision`. `decide_with_report()` retorna `decision`, o `receipt` ja registrado e o `escalation` opcional. Os testes confirmam que `decide()` e `decide_with_report()` incrementam `receipt_log` em exatamente 1, que `get_controller_stats()["total_evaluations"]` permanece 1 apos `decide_with_report()`, que escalation report ainda e criado para `ESCALATE_TO_MISAEL`, e que o receipt/stats continuam advisory-only.

## 5. Dependencias

PRs Dependabot abertas: nenhuma PR aberta foi retornada por `gh pr list` em 2026-06-29.

Ordem recomendada de merge manual para futuras PRs:

1. Dev dependencies simples.
2. UI runtime.
3. Build/deploy tooling.
4. Rust/security-sensitive.
5. Dependencias com breaking change, sempre com revisao manual e teste dedicado.

## 6. Deploy

O deploy Cloudflare/Pages agora pula somente quando `CLOUDFLARE_API_TOKEN` nao esta definido, imprimindo `CLOUDFLARE_API_TOKEN not set - skipping deploy`. Quando o token existe, `npx wrangler pages deploy frontend/dist --project-name projeto-omni` e executado sem `|| true`; uma falha real falha o step. O valor do token nao e impresso.

## 7. Checks executados

| Comando | Resultado | Observacao |
| --- | --- | --- |
| `git status` | Passou | Branch com apenas arquivos de escopo apos limpeza de artefatos gerados. |
| `git branch --show-current` | Passou | `hardening/medium-audit-alerts-remediation`. |
| `git diff --stat` | Passou | Usado para revisar escopo; docs novos aparecem como untracked ate staging. |
| `git diff --check` | Passou | Sem erros; Git emitiu avisos locais de CRLF. |
| `npm ci` | Passou | 49 packages, 0 vulnerabilities. |
| `npm run test:security` | Passou | Security Regression Suite passou, incluindo Runtime Truth, sanitizacao, tool governance e public demo container validation. |
| `npm run test:js-runtime` | Passou | Suite JS runtime passou; live HTTP e2e foi pulado porque `OMINI_E2E_API_URL` nao estava definido. |
| `npm test` | Falhou | `test:node` passou; `test:python` falhou em suite ampla com 1 failure e 2 errors ligados a runtime fallback/memory JSON. Nao houve alteracao nesses modulos nesta branch; falha registrada para revisao separada. |
| `cd frontend; npm ci` | Passou | 196 packages, 0 vulnerabilities. |
| `cd frontend; npm run typecheck` | Passou | `tsc --noEmit`. |
| `cd frontend; npm test` | Passou apos rerun isolado | Primeira execucao em paralelo falhou por timeout de 5s em um teste; rerun isolado passou 73 files / 566 tests. |
| `cd frontend; npm run build` | Passou | Vite build passou com avisos de chunk size/plugin timing. |
| `python -m pip install --upgrade pip` | Passou | Pip ja atualizado no venv local. |
| `python -m pip install -r backend/python/requirements.txt` | Passou com aviso | Instalou `cryptography`; pip reportou conflitos ambientais com `microsoft-teams-apps` versus `fastapi/uvicorn`. |
| `python -m pytest -q backend/python/tests/runtime/autonomy` | Passou | 337 passed, 20 subtests passed. |
| `python -m pytest -q tests/runtime` | Falhou no ambiente local | Primeira execucao falhou majoritariamente com `PermissionError [WinError 5]` em temp global; rerun com temp dentro do repo removeu WinError mas invalidou dois testes de boundary. Dois testes focados passaram com temp externo controlado. |
| `python -m pytest -q tests/runtime/observability` | Passou | 71 passed. |
| `cd backend/rust; cargo fmt --check` | Passou | Sem output. |
| `cd backend/rust; cargo clippy --all-targets --all-features -- -D warnings` | Passou apos correcao | Primeiro run expôs `clippy::ptr-arg` em helper de teste; corrigido para `&Path`. |
| `cd backend/rust; cargo test --locked --all` | Passou | 66 passed. |
| `docker build -f Dockerfile.demo -t omni-demo:ci .` | Nao executavel no ambiente | Docker daemon/pipe `dockerDesktopLinuxEngine` indisponivel. |

## 8. Regressoes

- Runtime Truth preservado.
- Governanca preservada.
- Sanitizacao preservada.
- BYOK preservado.
- Public Demo preservado.
- Sem merge automatico.
- Sem push direto na main.
- Autonomy permanece advisory-only.

## 9. Proximos passos

- Revisar os checks advisory de dependencia antes de merge manual.
- Confirmar no PR que os workflows bloqueantes executam sem mascarar falhas.
- Fazer merge manual somente apos aprovacao de Misael e checks relevantes.
