# Publishing Checklist — Phase 15 (Roadmap Oficial v2.1)

## Pré-requisitos antes de publicar

### Gates de segurança
- [ ] Gate 1A — Shell bloqueado por padrão ✅
- [ ] Gate 1B — Erros de especialista não logados com detalhes ✅
- [ ] Gate 1C — Backend payload sanitizado ✅
- [ ] Gate 1D — Frontend payload sanitizado ✅
- [ ] Gate 1E — PII redacted nos logs de aprendizado ✅
- [ ] Gate 2 — Runtime Truth Contract ✅
- [ ] Gate 3 — Tool Governance Enforcement ✅
- [ ] Gate 4 — Supabase key removida dos exports ✅
- [ ] Gate 5 — Input validation no Rust ✅
- [ ] Gate 6 — Container de demo documentado ✅
- [ ] Gate 7 — Security regression tests existem ✅
- [ ] Gate 8 — Error taxonomy centralizada ✅
- [ ] Gate 9 — Fallback/matcher excluídos do training ✅

### Documentação obrigatória
- [ ] `docs/audit/REMEDIATION_SUMMARY.md` existe ✅
- [ ] `docs/audit/SECURITY_FIXES.md` existe ✅
- [ ] `docs/audit/RUNTIME_TRUTH_CONTRACT.md` existe ✅
- [ ] `docs/audit/TEST_EVIDENCE.md` existe ✅
- [ ] `docs/audit/KNOWN_LIMITATIONS.md` existe ✅
- [ ] `docs/release/PUBLIC_DEMO_READINESS.md` existe ✅
- [ ] `docs/release/PUBLISHING_CHECKLIST.md` este documento ✅

---

## Checklist de ambiente antes do deploy

```bash
# Variáveis obrigatórias para demo pública
export OMNI_PUBLIC_DEMO_MODE=true
export OMNI_ALLOW_SHELL_TOOLS=false
export OMNI_DEBUG_INTERNAL_ERRORS=false
export OMNI_RATE_LIMIT_ENABLED=true
export OMNI_MAX_MESSAGE_CHARS=8000
export OMNI_MAX_BODY_BYTES=65536

# Verificar que secrets NÃO estão hardcoded
grep -r "supabaseKey\s*=" storage/memory/supabaseClient.js | grep -v "process.env"
# Deve retornar vazio

# Rodar security regression tests
pytest tests/security/test_security_regression.py -v
# Todos devem passar

# Build do container de demo
docker compose -f docker-compose.demo.yml build
docker compose -f docker-compose.demo.yml up -d
curl http://localhost:3001/health
docker compose -f docker-compose.demo.yml down
```

---

## Passos de publicação

1. **Aplicar todos os arquivos de remediation** na branch `remediation/roadmap-v2.1-replit-agent`
2. **Abrir Pull Request** para `main` com link para este checklist
3. **Revisor** verifica gates e documentação
4. **Rodar security regression tests** no CI antes do merge
5. **Merge** somente após todos os gates aprovados
6. **Deploy** com variáveis de ambiente de demo pública configuradas

---

## O que NÃO fazer no publish

- Nunca commitar `.env` com secrets reais
- Nunca habilitar `OMNI_DEBUG_INTERNAL_ERRORS=true` em produção
- Nunca remover `OMNI_PUBLIC_DEMO_MODE=true` em ambiente de demo pública
- Nunca fazer merge das Fases 11 e 12 sem gates específicos passando

---

## Contato e rollback

Em caso de incidente após publicação:

1. Setar `OMNI_PUBLIC_DEMO_MODE=true` e reiniciar serviço (mitiga a maioria dos riscos)
2. Reverter para commit anterior se necessário
3. Consultar `docs/audit/KNOWN_LIMITATIONS.md` para riscos documentados
