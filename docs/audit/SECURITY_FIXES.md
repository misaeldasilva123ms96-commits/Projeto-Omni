# Security Fixes — Phase 15 (Roadmap Oficial v2.1)

## Lista de vulnerabilidades corrigidas

| ID | Categoria | Severidade | Arquivo | Correção |
|---|---|---|---|---|
| SEC-001 | Shell Injection | Crítica | `run_command.py` | Shell bloqueado por padrão; lista de comandos proibidos |
| SEC-002 | Information Disclosure | Alta | `cognitive_runtime_inspector.py` | Stack trace e tokens removidos de payloads públicos |
| SEC-003 | Information Disclosure | Alta | `RuntimePanel.tsx` + `runtimeDebugSanitizer.ts` | Sanitizador no frontend bloqueia campos internos |
| SEC-004 | PII Exposure | Alta | `learning_logger.py` | Redação de email, CPF, telefone, JWT, API keys, paths |
| SEC-005 | Secret Exposure | Alta | `supabaseClient.js` | Supabase key/url removidos dos exports |
| SEC-006 | Misleading Runtime Claims | Média | `queryEngineAuthority.js` | Runtime truth contract impede claims falsos |
| SEC-007 | Uncontrolled Tool Execution | Alta | `queryEngineAuthority.js` | Governance check antes de toda execução de ferramenta |
| SEC-008 | Unbounded Input | Média | `main.rs` | Max 8000 chars, sem control chars, session_id validado |
| SEC-009 | Training Data Poisoning | Média | `learning_logger.py` | Fallback/matcher excluídos de dados positivos |
| SEC-010 | Inconsistent Error Codes | Baixa | `errorCodes.js`, `errors.py` | Códigos centralizados, sem detalhes internos |

---

## Riscos residuais conhecidos

| Risco | Severidade | Mitigação atual | Plano |
|---|---|---|---|
| Rate limiting dependente de env | Média | Flag `OMNI_RATE_LIMIT_ENABLED` existe, implementação no Rust é parcial | Fase 11 |
| Classificador de intent é regex puro | Baixa | Declarado via `runtime_truth.intent_source=rule_based` | Fase 12 |
| Subprocess sem timeout configurável | Média | Existe timeout, mas não em todas as rotas | Fase 11 |
| Sem autenticação em `/chat` público | Alta | Aceito como risco de demo; rate limit mitiga | Fase 14 docs |
| Logs de runtime podem crescer sem rotação | Baixa | Não há rotação automática ainda | Backlog |

---

## Mudanças que NÃO foram feitas (intencionalmente)

- **Fase 11 (Persistent Services):** Arquitetura HTTP para Python/Node — planejada, não implementada.
- **Fase 12 (Intelligence Upgrade):** Classificador embedding/LLM — planejado, não implementado.
- Nenhuma mudança de comportamento de runtime além do especificado por gate.
- Nenhuma remoção de código existente funcional sem substituição equivalente.
