# Execution Manifest

## Propósito

O execution manifest torna explícita a decisão operacional tomada pelo runtime antes da execução efetiva. Ele foi introduzido como camada aditiva, sem substituir o fluxo atual do `BrainOrchestrator`.

## Estrutura

O manifesto serializável inclui:

- `intent`
- `chosen_strategy`
- `selected_tools`
- `step_plan`
- `fallback_strategy`
- `observability_tags`
- `safety_notes`
- `output_mode`
- `summary_rationale`
- `provider_path`

## Como se encaixa no Omni

O manifesto é construído a partir de:

- `OILRequest` já existente
- `RoutingDecision` enriquecido
- metadata conservadora de tool/capability

Ele é usado principalmente para:

- observabilidade segura
- debugging operacional
- futura auditoria de execução cognitiva

## Limites desta versão

- não contém chain-of-thought
- não dirige a execução sozinho
- não redefine o fluxo de reasoning/strategy/control já existente

## Compatibilidade e fallback

Se a construção do manifesto falhar:

- o runtime continua no caminho atual
- a falha é registrada como `runtime_upgrade_fallback`
- nenhum endpoint público muda de contrato

## Próximos passos naturais

- anexar manifests a snapshots observáveis maiores
- conectar manifesto com seleção de provider
- usar o manifesto como entrada de auditoria e replay seguro
