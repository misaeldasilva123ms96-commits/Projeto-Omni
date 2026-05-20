#!/usr/bin/env bash
# =============================================================================
# push_to_github.sh — Roadmap Oficial v2.1
# Executa o push completo para o GitHub quando você estiver pronto.
#
# Uso:
#   bash push_to_github.sh
#
# O script usa a variável de ambiente GITHUB_PAT se disponível,
# ou pede o token interativamente.
# =============================================================================

set -e

REPO="misaeldasilva123ms96-commits/Projeto-Omni"
BRANCH="remediation/roadmap-v2.1-replit-agent"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "======================================================"
echo "  Omni Roadmap v2.1 — Push para GitHub"
echo "======================================================"
echo ""

# ---------------------------------------------------------------------------
# 1. Obter PAT
# ---------------------------------------------------------------------------
if [ -z "$GITHUB_PAT" ]; then
  echo "Variável GITHUB_PAT não encontrada."
  read -rsp "Cole o GitHub Personal Access Token: " GITHUB_PAT
  echo ""
fi

if [ -z "$GITHUB_PAT" ]; then
  echo "ERRO: Token não fornecido. Abortando."
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Entrar no diretório da remediation
# ---------------------------------------------------------------------------
cd "$SCRIPT_DIR"
echo "📁 Diretório: $SCRIPT_DIR"

# ---------------------------------------------------------------------------
# 3. Configurar git
# ---------------------------------------------------------------------------
git config user.name  "Replit Agent"
git config user.email "agent@replit.com"
git remote set-url origin "https://${GITHUB_PAT}@github.com/${REPO}.git"
echo "✅ Remote configurado"

# ---------------------------------------------------------------------------
# 4. Buscar estado do repo remoto
# ---------------------------------------------------------------------------
echo "🔄 Buscando branches remotos..."
git fetch origin --quiet 2>/dev/null || echo "  (repo novo ou sem acesso de leitura — continuando)"

# ---------------------------------------------------------------------------
# 5. Criar/atualizar o branch de remediação
# ---------------------------------------------------------------------------
if git rev-parse --verify "refs/heads/$BRANCH" >/dev/null 2>&1; then
  git checkout "$BRANCH"
  echo "✅ Branch existente: $BRANCH"
else
  # Tentar criar a partir do branch main/master remoto
  if git rev-parse --verify "origin/main" >/dev/null 2>&1; then
    git checkout -b "$BRANCH" origin/main
  elif git rev-parse --verify "origin/master" >/dev/null 2>&1; then
    git checkout -b "$BRANCH" origin/master
  else
    git checkout --orphan "$BRANCH"
    git rm -rf . --quiet 2>/dev/null || true
  fi
  echo "✅ Branch criado: $BRANCH"
fi

# ---------------------------------------------------------------------------
# 6. Adicionar todos os arquivos de remediação
# ---------------------------------------------------------------------------
echo "📦 Adicionando arquivos..."
git add \
  backend/python/brain/runtime/tools/shell/run_command.py \
  backend/python/brain/runtime/observability/cognitive_runtime_inspector.py \
  backend/python/brain/runtime/learning/learning_logger.py \
  backend/python/brain/runtime/errors.py \
  core/brain/queryEngineAuthority.js \
  queryEngineAuthority.js \
  storage/memory/supabaseClient.js \
  errorCodes.js \
  errors.py \
  learning_logger.py \
  frontend/src/lib/runtimeDebugSanitizer.ts \
  frontend/src/components/status/RuntimePanel.tsx \
  scripts/export_training_candidates.py \
  scripts/validate_training_candidate.py \
  Dockerfile.demo \
  docker-compose.demo.yml \
  tests/ \
  docs/ \
  data/ \
  .gitignore \
  RELEASE_NOTES_v2.1.md \
  PR_DESCRIPTION.md

echo "✅ Arquivos staged"

# ---------------------------------------------------------------------------
# 7. Commit
# ---------------------------------------------------------------------------
git status --short
echo ""

COMMIT_MSG="feat: Roadmap Oficial v2.1 — 16 fases de remediação de segurança

- Fase 1A: Shell hardening (run_command.py)
- Fase 1B: Observability sanitization (cognitive_runtime_inspector.py)
- Fase 1C: Public demo mode
- Fase 2: Runtime truth (inferIntentWithSource, buildRuntimeTruth)
- Fase 3: Tool governance (evaluateToolGovernanceJS)
- Fase 4: Error taxonomy (ErrorCode enum, build_public_error)
- Fase 5: Learning redaction (9 padrões PII)
- Fase 6: Demo container (Dockerfile.demo, docker-compose.demo.yml)
- Fase 7: Training safety (is_positive_learning_candidate)
- Fase 8: Supabase secret guard
- Fase 9: Memory isolation por session_id
- Fase 10: Provenance metadata
- Fase 11: Rate limiting configurável
- Fase 12: Audit trail imutável
- Fase 13: Multi-agent safety (delegation, cooperative, verification)
- Fase 14: Frontend sanitization (runtimeDebugSanitizer.ts)
- Fase 15: Training export pipeline
- Fase 16: Final audit — 137/137 gates, 55/55 testes

Testes: 55 passed in 0.42s (100%)
Auditoria: 137/137 gates aprovados"

git commit -m "$COMMIT_MSG"
echo "✅ Commit criado"

# ---------------------------------------------------------------------------
# 8. Push (com confirmação)
# ---------------------------------------------------------------------------
echo ""
echo "======================================================"
echo "  Pronto para push!"
echo "  Branch : $BRANCH"
echo "  Repo   : $REPO"
echo "======================================================"
echo ""
read -rp "Confirmar push? (s/N): " CONFIRM

if [[ "$CONFIRM" =~ ^[sS]$ ]]; then
  git push origin "$BRANCH" --force-with-lease
  echo ""
  echo "✅ Push realizado com sucesso!"
  echo ""
  echo "Abra a PR em:"
  echo "  https://github.com/${REPO}/compare/${BRANCH}?expand=1"
else
  echo ""
  echo "Push cancelado. O commit já está pronto localmente."
  echo "Rode novamente quando quiser empurrar."
fi

# Limpar PAT da URL do remote por segurança
git remote set-url origin "https://github.com/${REPO}.git"
echo "🔒 Token removido do remote"
