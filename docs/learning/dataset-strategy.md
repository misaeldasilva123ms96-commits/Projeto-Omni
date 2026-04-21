# Dataset Strategy

## Goal

Elevar o dataset do Omni para um padrão profissional, auditável e expansível, sem depender de dados crus sem filtro.

## Layers

- `public normalized`: exemplos externos filtrados, normalizados e convertidos para OIL
- `curated internal`: exemplos pequenos, de alta qualidade, focados no domínio Omni
- `runtime feedback`: candidatos derivados de logs e falhas observadas no runtime

## Quality Controls

- `dataset_quality.py` calcula `quality_score`
- detecção de duplicatas por fingerprint determinístico
- verificação de estrutura mínima
- checagem de alinhamento OIL
- priorização de domínios Omni: `runtime`, `coding`, `planning`, `governance`, `analysis`

## Enrichment

`dataset_enrichment.py` adiciona:

- OIL quando estiver ausente ou incompleto
- `runtime_hints`
- `dataset_origin`
- `quality_score` recalculado

## Feedback Loop

`feedback_loop.py` lê logs de execução do Omni e gera exemplos candidatos a partir de falhas e fallback observados.

