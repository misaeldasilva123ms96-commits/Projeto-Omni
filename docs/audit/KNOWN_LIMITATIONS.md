# Known Limitations — Phase 15 (Roadmap Oficial v2.1)

## O que ainda não está pronto para produção

| Limitação | Categoria | Severidade | Fase que resolve |
|---|---|---|---|
| Serviços Python e Node via subprocess (não HTTP persistente) | Arquitetura | Média | Fase 11 |
| Circuit breaker não implementado | Resiliência | Média | Fase 11 |
| Classificador de intent é 100% regex | Qualidade | Baixa | Fase 12 |
| Sem dataset de avaliação com 550+ exemplos por classe | Training | Média | Fase 12 |
| Rate limiting declarado em env mas implementação parcial no Rust | Segurança | Média | Fase 11 |
| Rotação de logs de runtime não configurada | Operacional | Baixa | Backlog |
| Sem autenticação na rota `/chat` público | Segurança | Alta | Backlog |
| Supabase não configurado em ambiente de demo | Persistência | Baixa | Configuração externa |

---

## O que ainda não está pronto para treinamento

| Limitação | Motivo |
|---|---|
| Dataset de intent eval tem apenas 25 exemplos | Mínimo recomendado é 550 (Fase 12) |
| Dataset de runtime truth eval tem 10 exemplos | Expandir com logs reais de produção |
| Export de candidatos de training requer logs reais | Sem logs de produção não há candidatos |
| Classificador regex rotula tudo como `rule_based` — sem ground truth de LLM | Requer Fase 12 |

---

## O que está bloqueado em demo pública

| Funcionalidade | Motivo do bloqueio |
|---|---|
| Shell / bash | `OMNI_ALLOW_SHELL_TOOLS=false` + governança JS |
| Ferramentas destrutivas | `_BLOCKED_IN_DEMO` + `_BLOCKED_BY_DEFAULT` |
| Ferramentas de escrita de arquivo | `_BLOCKED_IN_DEMO` |
| Operações de rede sem aprovação | `_BLOCKED_IN_DEMO` |
| Git actions | `_BLOCKED_IN_DEMO` |
| Debug interno de erros | `OMNI_DEBUG_INTERNAL_ERRORS=false` |

---

## Rollback disponível

| Situação | Rollback |
|---|---|
| Rust input validation causa falsos positivos | `OMNI_MAX_MESSAGE_CHARS=0` desativa limite (env) |
| Demo mode bloqueia algo necessário | `OMNI_PUBLIC_DEMO_MODE=false` restaura comportamento anterior |
| Supabase key removal quebra alguma feature | Restaurar exports em `supabaseClient.js` (reversível) |
| Qualquer fase aplicada causa regressão | Reverter ao commit anterior ao da branch de remediation |

---

## Fases pendentes (Roadmap Oficial v2.1)

| Fase | Nome | Prioridade |
|---|---|---|
| 11 | Persistent Runtime Services | Alta, posterior |
| 12 | Intelligence Upgrade | Alta, posterior |
