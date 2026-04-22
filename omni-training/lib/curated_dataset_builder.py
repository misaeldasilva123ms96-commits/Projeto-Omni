from __future__ import annotations

from pathlib import Path
from typing import Any

from common import write_jsonl
from dataset_enrichment import enrich_curated_example


def _base_examples() -> list[dict[str, Any]]:
    themes = [
        ("architecture", "analysis", "Explique como reduzir acoplamento no orchestrator sem quebrar compatibilidade.", "O runtime já possui control plane, OIL, manifest e governança ativa.", "Separe contratos explícitos, preserve o caminho compatível como fallback e mova apenas a lógica implícita mais estável para módulos pequenos e auditáveis."),
        ("debugging", "runtime", "Diagnostique por que um fallback do runtime disparou mesmo com strategy válida.", "Há eventos de execução, ranking, manifest e response synthesis disponíveis na observabilidade.", "Correlacione `runtime_strategy_execution_fallback`, `runtime_manifest_execution_applied` e o motivo final do `last_runtime_reason` antes de alterar qualquer policy."),
        ("oil", "analysis", "Mostre como a OIL ajuda a distinguir intenção, restrição e forma de saída.", "O time quer reduzir respostas genéricas e melhorar consistência de decisão.", "Use a OIL para tornar explícitos `user_intent`, `constraints`, `desired_output`, `execution_bias` e `memory_relevance`, porque isso reduz ambiguidade antes do runtime sintetizar a resposta."),
        ("routing", "planning", "Planeje a evolução do capability routing para cenários ambíguos.", "O sistema já possui ambiguity detection e ranking conservador.", "Mantenha o roteamento determinístico como fonte primária, use ranking apenas em casos seguros e registre sempre candidate strategies, confidence e fallback path."),
        ("manifest", "coding", "Refatore o manifest builder para enriquecer tool metadata sem quebrar o shape atual.", "O manifesto já influencia execução e observabilidade.", "Adicione metadados de tool e `manifest_id` de forma aditiva, preserve os campos atuais e cubra a serialização com testes curtos e explícitos."),
        ("observability", "governance", "Defina a observabilidade mínima para uma camada nova de execução.", "A equipe quer auditabilidade sem log verboso ou dados sensíveis.", "Registre apenas resumo de decisão, executor usado, status, fallback e notas de segurança. Não serialize raciocínio bruto nem payloads sensíveis."),
        ("fallback", "runtime", "Descreva um fallback seguro quando o dispatcher de strategy falhar.", "O contrato público não pode quebrar nem degradar silenciosamente sem trilha auditável.", "Capture a exceção, emita evento curto de fallback, use o caminho compatível já existente e devolva uma resposta segura e coerente com o modo atual do runtime."),
        ("governance", "governance", "Explique quando governança deve bloquear uma strategy selecionada.", "Há strategies que podem acionar tools, node runtime e reasoning mais profundo.", "Bloqueie quando risco alto, evidência obrigatória ausente ou tool crítica não estiver autorizada. Em dúvida, faça downgrade ou SAFE_FALLBACK."),
        ("providers", "coding", "Planeje uma integração aditiva de providers no Omni.", "O projeto já possui registry de providers, contracts base e observabilidade de provenance.", "Use contratos internos pequenos, preserve a seleção atual e só acrescente campos como `provider_path`, `model_actual` e health signals onde houver valor operacional."),
        ("execution", "runtime", "Explique como `selected_strategy` deve influenciar o executor usado.", "A Fase 4 introduziu executores explícitos por strategy.", "Converta strategy em um request operacional claro, deixe o dispatcher escolher o executor correto e faça a síntese final respeitar `output_mode`, `safety_notes` e fallback semantics."),
    ]
    complexities = [
        ("simple", "low", "balanced"),
        ("medium", "medium", "deep"),
        ("complex", "high", "deep"),
        ("very-complex", "medium", "deep"),
    ]
    examples: list[dict[str, Any]] = []
    counter = 1
    for theme_name, task_family, user_input, context, answer in themes:
        for complexity, urgency, bias in complexities:
            examples.append(
                {
                    "id": f"omni-curated-{counter:04d}",
                    "source": "internal_curated",
                    "language": "pt-BR",
                    "task_family": task_family,
                    "user_input": f"[{complexity}] {user_input}",
                    "context": f"{context} Nível de complexidade: {complexity}.",
                    "oil": {
                        "user_intent": "plan" if task_family in {"planning", "governance"} else "analyze",
                        "entities": {"theme": theme_name, "complexity": complexity},
                        "constraints": {"style": "auditavel", "scope": "omni_runtime"},
                        "desired_output": "plan" if task_family in {"planning", "governance"} else "analysis",
                        "urgency": urgency,
                        "execution_bias": bias,
                        "memory_relevance": "high",
                    },
                    "runtime_hints": {
                        "strategy": "SAFE_FALLBACK" if task_family == "governance" and urgency == "high" else ("TOOL_ASSISTED" if task_family == "coding" else "MULTI_STEP_REASONING"),
                        "requires_tools": task_family == "coding",
                        "requires_node_runtime": theme_name in {"providers", "execution"} and complexity == "complex",
                        "fallback_allowed": True,
                    },
                    "assistant_output": answer,
                    "review_status": "approved" if complexity != "complex" else "reviewed",
                    "metadata": {"theme": theme_name, "complexity": complexity, "dataset_origin": "curated_builder"},
                }
            )
            counter += 1
    return examples


def build_curated_dataset() -> list[dict[str, Any]]:
    return [enrich_curated_example(example) for example in _base_examples()]


def export_curated_dataset(path: Path) -> int:
    return write_jsonl(path, build_curated_dataset())
