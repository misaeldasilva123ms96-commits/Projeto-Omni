from __future__ import annotations

from pathlib import Path
from typing import Any

from common import write_jsonl
from dataset_enrichment import enrich_curated_example


CURATION_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "coding": [
        {
            "task_family": "coding",
            "user_input": "Refatore um módulo do Omni sem quebrar contratos públicos.",
            "context": "Preserve compatibilidade, cobertura e fallback seguro.",
            "assistant_output": "Comece pelos contratos explícitos, mantenha adaptação aditiva e valide com testes focados antes da suíte maior.",
        }
    ],
    "architecture": [
        {
            "task_family": "analysis",
            "user_input": "Explique como isolar um control plane sem reescrever o orchestrator inteiro.",
            "context": "O runtime já tem routing, manifest, ranking e governança.",
            "assistant_output": "Encapsule a parte implícita em módulos pequenos, mantenha o orchestrator como coordenador e preserve um caminho compatível para rollback.",
        }
    ],
    "runtime_reasoning": [
        {
            "task_family": "runtime",
            "user_input": "Descreva quando MULTI_STEP_REASONING deve vencer DIRECT_RESPONSE.",
            "context": "Há ambiguidade, OIL e manifest disponíveis.",
            "assistant_output": "Prefira MULTI_STEP_REASONING quando o pedido exigir decomposição explícita, múltiplas etapas verificáveis ou síntese híbrida auditável.",
        }
    ],
    "debugging": [
        {
            "task_family": "runtime",
            "user_input": "Diagnostique por que o runtime caiu em fallback mesmo com strategy válida.",
            "context": "Existem eventos de dispatch, execução, fallback e manifest na observabilidade.",
            "assistant_output": "Correlacione o trace do executor, o motivo de fallback, a governança e os sinais do manifest antes de alterar qualquer policy.",
        }
    ],
    "routing": [
        {
            "task_family": "planning",
            "user_input": "Planeje como reduzir ambiguidades de routing sem dar autoridade total ao modelo.",
            "context": "O runtime já possui ranking conservador e detector de ambiguidade.",
            "assistant_output": "Fortaleça regras locais, use o modelo apenas como sinal opcional e registre candidate strategies, confidence e fallback em toda decisão ambígua.",
        }
    ],
    "manifest": [
        {
            "task_family": "runtime",
            "user_input": "Explique como o manifest deve orientar executor e síntese final.",
            "context": "output_mode, safety_notes e selected_strategy já existem no runtime.",
            "assistant_output": "Use o manifest como contrato operacional limitado: ele escolhe o caminho de execução e a síntese, mas não substitui governança nem inventa capacidades novas.",
        }
    ],
    "fallback": [
        {
            "task_family": "governance",
            "user_input": "Defina um fallback seguro quando uma execução por strategy falha.",
            "context": "O contrato público do Omni não pode quebrar nem degradar silenciosamente.",
            "assistant_output": "Registre o erro, marque a execução como fallback, preserve uma resposta segura e redirecione para o caminho compatível mais estável disponível.",
        }
    ],
    "observability": [
        {
            "task_family": "analysis",
            "user_input": "Quais sinais mínimos de observabilidade uma camada nova deve expor?",
            "context": "O time quer auditoria forte sem log verboso ou dados sensíveis.",
            "assistant_output": "Registre source, strategy, executor, status, fallback, manifest id e resumo do trace. Evite payloads sensíveis e qualquer raciocínio bruto.",
        }
    ],
}


def build_curated_drafts(*, per_category: int = 4) -> list[dict[str, Any]]:
    drafts: list[dict[str, Any]] = []
    counter = 1
    for category, templates in CURATION_TEMPLATES.items():
        for index in range(per_category):
            template = templates[index % len(templates)]
            draft = {
                "id": f"review-draft-{category}-{counter:04d}",
                "source": "internal_curated",
                "language": "pt-BR",
                "review_status": "draft",
                "metadata": {"draft_category": category, "draft_origin": "curation_helpers"},
                **template,
            }
            drafts.append(enrich_curated_example(draft))
            counter += 1
    return drafts


def export_curated_drafts(path: Path, *, per_category: int = 4) -> int:
    return write_jsonl(path, build_curated_drafts(per_category=per_category))

