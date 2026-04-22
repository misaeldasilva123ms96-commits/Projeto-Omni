# LoRA Usage

## Intended Role

O adapter LoRA do Omni é um componente opcional de refinamento. Ele existe para:

- melhorar coerência textual
- reduzir respostas genéricas
- ajudar em casos ambíguos
- sugerir refinamento controlado

## Explicit Non-Goals

- não substitui o `CapabilityRouter`
- não substitui o `ExecutionManifest`
- não substitui governança nem fallbacks existentes

## Runtime Behavior

- se o adapter existir, o runtime pode consultá-lo em turnos ambíguos
- se faltar adapter, dependência ou confiança, o runtime segue no caminho determinístico
- decisões do modelo nunca têm autoridade total

## Operational Notes

- o adapter esperado vem de `omni-training/configs/training_config.json`
- a origem do dataset é propagada para observabilidade como `dataset_origin`
- eventos de fallback permanecem auditáveis

