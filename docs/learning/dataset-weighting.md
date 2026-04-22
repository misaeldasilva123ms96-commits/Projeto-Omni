# Dataset Weighting

## Purpose

`dataset_weighting.py` permite priorizar exemplos melhores e mais úteis para o domínio Omni.

## Supported Fields

- `quality_score`
- `sample_weight`
- `ambiguity_label`
- `runtime_value`
- `review_priority`

## Current Policy

- exemplos de alta qualidade recebem peso maior
- casos ambíguos resolvidos recebem peso extra
- exemplos de alto valor de runtime recebem prioridade maior
- exemplos fracos ou incorretos perdem peso

## Compatibility

O seed dataset atual continua válido mesmo sem esses campos; os pesos são derivados de forma aditiva.

