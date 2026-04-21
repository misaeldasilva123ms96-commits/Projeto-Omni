# Runtime Integration

## Purpose

Esta camada conecta o adapter LoRA treinado localmente ao runtime cognitivo do Omni sem substituir os componentes determinísticos já existentes.

## Flow

`user input -> OIL -> capability routing -> execution manifest -> optional LoRA refinement -> execution -> observability`

## Design

- O `BrainOrchestrator` continua sendo o dono do fluxo.
- `LoRAInferenceEngine` só é usado se houver adapter local válido.
- `LoRARouterAdapter` decide quando vale consultar o modelo.
- `LoRADecisionEngine` combina o caminho determinístico com o sinal probabilístico do modelo.
- Divergência ou erro volta imediatamente para o caminho determinístico.

## Observability

Os seguintes sinais são anexados ao runtime:

- `lora_used`
- `model_confidence`
- `decision_source`
- `dataset_origin`

Também são registrados eventos `runtime_lora` e `runtime_lora_fallback`.

## Current Limits

- O modelo não substitui routing, manifest nem governança.
- A inferência depende de adapter local e dependências opcionais de ML.
- Sem adapter, o runtime continua inalterado.

