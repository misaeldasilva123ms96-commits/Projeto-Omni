from __future__ import annotations

from pathlib import Path
from typing import Any

from common import write_jsonl
from dataset_enrichment import enrich_curated_example


TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "ambiguity_pairs": [
        {
            "task_family": "runtime",
            "user_input": "Escolha entre DIRECT_RESPONSE e MULTI_STEP_REASONING para explicar um fluxo do Omni sem detalhes de implementação.",
            "context": "Há duas strategies plausíveis e o runtime deve preferir segurança e auditabilidade.",
            "assistant_output": "Use MULTI_STEP_REASONING apenas se o pedido exigir decomposição explícita; caso contrário mantenha DIRECT_RESPONSE para reduzir latência e complexidade.",
            "candidate_strategies": ["DIRECT_RESPONSE", "MULTI_STEP_REASONING"],
            "selected_strategy": "DIRECT_RESPONSE",
        }
    ],
    "fallback_cases": [
        {
            "task_family": "governance",
            "user_input": "O que fazer quando uma strategy nova falha em produção?",
            "context": "O contrato público deve permanecer estável e observável.",
            "assistant_output": "Registre o erro, degrade para o caminho compatível e mantenha uma resposta segura antes de tentar qualquer ampliação de comportamento.",
            "selected_strategy": "SAFE_FALLBACK",
        }
    ],
    "governance_block_examples": [
        {
            "task_family": "governance",
            "user_input": "Como bloquear uma tool de risco alto durante uma execução TOOL_ASSISTED?",
            "context": "A governança precisa vencer o modelo e o ranking.",
            "assistant_output": "Negue a execução da tool de alto risco, emita um evento de bloqueio claro e faça downgrade ou fallback para um caminho seguro e auditável.",
            "selected_strategy": "SAFE_FALLBACK",
        }
    ],
    "provider_selection_examples": [
        {
            "task_family": "coding",
            "user_input": "Como selecionar um provider sem acoplamento forte no Omni?",
            "context": "O sistema já possui provider registry e contracts base.",
            "assistant_output": "Use metadata interna, preserve fallback local e registre `provider_path` na observabilidade para manter rastreabilidade sem acoplamento rígido.",
            "selected_strategy": "MULTI_STEP_REASONING",
        }
    ],
    "manifest_driven_cases": [
        {
            "task_family": "runtime",
            "user_input": "Explique como o execution manifest deve guiar a execução real.",
            "context": "A strategy já foi escolhida e o dispatcher precisa respeitar output_mode e safety_notes.",
            "assistant_output": "O manifest deve orientar executor, síntese e fallback. Ele não substitui governança, mas limita e documenta a execução de forma operacional.",
            "selected_strategy": "MULTI_STEP_REASONING",
        }
    ],
}


def generate_synthetic_examples(*, category: str, limit: int = 20) -> list[dict[str, Any]]:
    templates = list(TEMPLATES.get(category, []) or [])
    output: list[dict[str, Any]] = []
    if not templates:
        return output
    for index in range(1, max(1, limit) + 1):
        template = templates[(index - 1) % len(templates)]
        example = {
            "id": f"synthetic-{category}-{index:04d}",
            "source": "synthetic_controlled",
            "language": "pt-BR",
            "review_status": "draft",
            "metadata": {"synthetic_category": category, "requires_review": True},
            **template,
        }
        output.append(enrich_curated_example(example))
    return output


def export_synthetic_examples(path: Path, records: list[dict[str, Any]]) -> int:
    return write_jsonl(path, records)
