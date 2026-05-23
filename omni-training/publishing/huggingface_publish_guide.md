# Hugging Face Publish Guide

## Publicar dataset

1. Gere os artefatos finais em JSONL.
2. Revise dados públicos e curados separadamente.
3. Prepare:
   - `README.md` ou dataset card
   - licença e restrições
   - descrição do schema
4. Publique no Hub como dataset repository.

Arquivos recomendados:

- dataset final JSONL
- card do dataset
- exemplo de registro
- notas de preprocessing

## Publicar adapter LoRA

1. Confirme o diretório final do adapter salvo por `train_lora.py`.
2. Inclua:
   - pesos do adapter
   - tokenizer se necessário
   - `adapter_config.json`
   - model card
3. Documente o modelo base e limitações.

## Metadados importantes

- idiomas suportados
- domínio Omni
- task families
- riscos conhecidos
- uso responsável
- instruções de inferência

## Boas práticas

- não publicar dataset cru sem filtro
- deixar claro o que é curado internamente
- documentar limitações e possíveis vieses
- manter separação entre dataset e adapter
