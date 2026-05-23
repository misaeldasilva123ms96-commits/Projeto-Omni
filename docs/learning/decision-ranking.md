# Decision Ranking

## Why Phase 3 Exists

A Fase 3 existe para tratar casos em que mais de uma estratégia parece plausível, sem transferir autoridade do runtime para o modelo.

## Flow

`OIL -> routing -> execution manifest -> ambiguity detection -> candidate builder -> decision ranking -> optional LoRA refinement`

## Key Rules

- o `CapabilityRouter` continua sendo a fonte determinística inicial
- ranking só roda quando a ambiguidade é segura
- governança e bloqueios continuam acima do ranking
- empate ou baixa confiança favorecem a regra
- exceções degradam para o caminho determinístico

## Model Usage

O modelo é opcional e só atua como um sinal leve de preferência entre candidatos.

