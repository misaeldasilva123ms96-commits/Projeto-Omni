# Omni Intermediate Language (OIL)

## Propósito

A OIL já existia no Omni como envelope estruturado para interpretação, reasoning e handoff interno. Esta etapa adiciona uma projeção menor e mais estável para uso operacional e observável no runtime.

## O que foi adicionado

- `OILProjection` em `brain.runtime.language.oil_models`
- `oil_translator.py` com:
  - `translate_to_oil_projection(...)`
  - `interpret_to_oil_projection(...)`
  - `oil_summary(...)`

A projeção resume a entrada em:

- `user_intent`
- `entities`
- `constraints`
- `desired_output`
- `urgency`
- `execution_bias`
- `memory_relevance`

## Como se encaixa no Omni

O schema OIL existente continua sendo a fonte de verdade de transporte (`OILRequest`, `OILResult`, `OILError`). A nova projeção é uma visão normalizada de runtime para:

- manifestos
- observabilidade mínima
- debugging seguro

## Limites desta versão

- a projeção é derivada de heurísticas locais
- não há compressão semântica avançada nesta camada
- não substitui reasoning, planning ou strategy adaptation

## Compatibilidade e fallback

Se a projeção falhar, o runtime continua usando o caminho atual do orquestrador. O erro é registrado como `runtime_upgrade_fallback`, sem interromper `/chat`.

## Próximos passos naturais

- alinhar `execution_bias` com policy/performance hints
- enriquecer `memory_relevance` com sinais da memória unificada
- usar a projeção como entrada estável para seleção de provider e custo
