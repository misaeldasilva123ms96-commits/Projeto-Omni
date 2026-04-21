# Capability Routing

## Propósito

O Omni já possuía um `CapabilityRouter` operacional para classificar pedidos entre fluxos como exploração, mutação, verificação, recuperação e reporting. Esta evolução adiciona uma camada de contrato mais explícita para o runtime cognitivo sem substituir o roteador existente.

## O que foi adicionado

- campos canônicos de runtime no `RoutingDecision`:
  - `intent`
  - `strategy`
  - `confidence`
  - `requires_tools`
  - `requires_node_runtime`
  - `fallback_allowed`
  - `internal_reasoning_hint`
- shape compatível em `brain.runtime.models.capability_routing.CapabilityRoutingRecord`
- mapeamento explícito para estratégias de alto nível:
  - `DIRECT_RESPONSE`
  - `TOOL_ASSISTED`
  - `MULTI_STEP_REASONING`
  - `NODE_RUNTIME_DELEGATION`
  - `SAFE_FALLBACK`

## Como se encaixa no Omni

O orquestrador continua consumindo os campos legados já usados em produção. Os novos campos entram como enriquecimento aditivo para:

- observabilidade
- construção do execution manifest
- futura evolução para policy-based routing

## Limites desta versão

- o roteamento continua deterministic-first e heurístico
- não há chamada externa para classificação básica
- a taxonomia de intenção ainda segue a linguagem e os registries já vivos do Omni

## Compatibilidade e fallback

Os call sites existentes não precisam mudar para continuar funcionando. Se uma camada mais nova consumir apenas o shape canônico, ela pode usar `RoutingDecision.as_runtime_record()`.

## Próximos passos naturais

- introduzir políticas declarativas de roteamento
- conectar confiança de roteamento com sinais de aprendizado/feedback
- enriquecer estratégias com conhecimento por domínio ou provider
