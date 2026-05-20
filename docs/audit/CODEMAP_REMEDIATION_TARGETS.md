# CODEMAP REMEDIATION TARGETS — 2026-04-30

## Fase 0.5 — Mapeamento Real do Código

**Branch base:** main  
**Commit base:** b187269bb83d74842c7cd17d3a529a59371d65d3

---

## Tabela de Alvos

| Alvo Lógico | Path Real | Existe? | Observação |
|---|---|---|---|
| Shell tool | `backend/python/brain/runtime/tools/shell/run_command.py` | NÃO (criado na 1A) | Crítico — ausente antes da remediação |
| Governed tools | `backend/python/brain/runtime/control/governed_tools.py` | SIM | Usa `OMINI_GOVERNED_TOOLS_STRICT` |
| Governance controller | `backend/python/brain/runtime/control/governance_controller.py` | SIM | OK |
| Query engine authority | `core/brain/queryEngineAuthority.js` | SIM | `safeSpecialistCall` vaza err.message |
| Execution provenance | `core/brain/executionProvenance.js` | SIM | OK |
| Provider router | `platform/providers/providerRouter.js` | SIM | OK |
| Supabase client | `storage/memory/supabaseClient.js` | SIM | Exporta `supabaseKey` e `supabaseUrl` — crítico |
| Runtime panel | `frontend/src/components/status/RuntimePanel.tsx` | SIM | Sem sanitizador de debug |
| Learning logger | `backend/python/brain/runtime/learning/learning_logger.py` | SIM | Redação parcial — faltam padrões |
| Public runtime outcome | `backend/python/brain/runtime/observability/public_runtime_outcome.py` | SIM | OK |
| Cognitive runtime inspector | `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py` | SIM | Falta visão pública separada |
| Tests dir | `tests/` | SIM | pytest.ini existe |
| jest.config | não encontrado | NÃO | |

---

## Env Vars Mapeadas

| Nome | Arquivo | Tipo |
|---|---|---|
| `OMINI_GOVERNED_TOOLS_STRICT` | `governed_tools.py` | Python (legacy) |
| `OMINI_SKIP_CONVERSATIONAL_MATCHERS` | `queryEngineAuthority.js` | JS (legacy) |
| `SUPABASE_URL` | `supabaseClient.js` | JS |
| `SUPABASE_ANON_KEY` | `supabaseClient.js` | JS |
| `SUPABASE_SERVICE_ROLE_KEY` | `.env.example` | Env |

**Canônicos recomendados:** `OMNI_*` (aliases legados `OMINI_*` mantidos para compatibilidade)

---

## Importadores do Supabase

| Arquivo | Importa de |
|---|---|
| `storage/memory/runtimeMemoryStore.js` | `supabaseClient.js` |

---

## GATE 0.5: PASSED

- All remediation target files mapped ✅
- Missing files explicitly listed (run_command.py) ✅
- Test structure mapped ✅
- Env var naming mapped ✅
- Supabase importers mapped ✅
- No behavior changed ✅
- No merge into main ✅
