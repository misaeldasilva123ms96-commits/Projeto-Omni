# Curated Omni Dataset

Este diretório contém o dataset próprio pequeno e curado do Omni.

## Objetivo

Manter exemplos de alta qualidade, revisáveis e alinhados com:

- arquitetura Omni
- OIL
- capability routing
- execution manifest
- governança
- debugging técnico
- planejamento técnico

## Schema

Cada linha do JSONL segue:

```json
{
  "id": "...",
  "source": "internal_curated",
  "language": "pt-BR",
  "task_family": "coding|planning|governance|analysis|runtime",
  "user_input": "...",
  "context": "...",
  "oil": {
    "user_intent": "...",
    "entities": {},
    "constraints": {},
    "desired_output": "...",
    "urgency": "low|medium|high",
    "execution_bias": "cheap|balanced|deep",
    "memory_relevance": "none|low|high"
  },
  "runtime_hints": {
    "strategy": "DIRECT_RESPONSE|TOOL_ASSISTED|MULTI_STEP_REASONING|NODE_RUNTIME_DELEGATION|SAFE_FALLBACK",
    "requires_tools": false,
    "requires_node_runtime": false,
    "fallback_allowed": true
  },
  "assistant_output": "...",
  "quality_score": 0.0,
  "review_status": "draft|reviewed|approved"
}
```

## Como expandir com qualidade

- adicione poucos exemplos por vez
- prefira casos reais do domínio Omni
- mantenha linguagem precisa e operacional
- não inclua chain-of-thought
- marque `review_status` corretamente
- use `quality_score` para refletir qualidade editorial real

## Seeds atuais

O arquivo `omni_seed_dataset.jsonl` é pequeno por design e serve como base inicial para:

- validar a pipeline
- treinar um adapter LoRA inicial
- estabelecer o tom e o tipo de raciocínio esperado do Omni
