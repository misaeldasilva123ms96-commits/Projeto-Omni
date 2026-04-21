# Omni Training Pipeline

Pipeline incremental e auditável para:

- ingestão de datasets
- filtro e normalização
- conversão para OIL
- geração de dataset SFT em JSONL
- preparação para fine-tuning LoRA
- preparação para publicação futura no Hugging Face Hub

## Estrutura

```text
omni-training/
  data/
    raw/
    normalized/
    oil/
    sft/
    curated/
  scripts/
  configs/
  lib/
  publishing/
  reports/
```

## Instalação

Crie um ambiente Python dedicado e instale:

```bash
pip install -r omni-training/requirements.txt
```

## Pipeline básica

Baixar um dataset pequeno e seguro:

```bash
python omni-training/scripts/download_dataset.py --dataset-key default_small
```

Filtrar:

```bash
python omni-training/scripts/filter_dataset.py ^
  --input omni-training/data/raw/default_small.jsonl ^
  --output omni-training/data/normalized/default_small.filtered.jsonl
```

Normalizar:

```bash
python omni-training/scripts/normalize_dataset.py ^
  --input omni-training/data/normalized/default_small.filtered.jsonl ^
  --output omni-training/data/normalized/default_small.normalized.jsonl
```

Converter para OIL:

```bash
python omni-training/scripts/convert_to_oil.py ^
  --input omni-training/data/normalized/default_small.normalized.jsonl ^
  --output omni-training/data/oil/default_small.oil.jsonl
```

Gerar SFT:

```bash
python omni-training/scripts/build_sft_dataset.py ^
  --public-input omni-training/data/oil/default_small.oil.jsonl ^
  --curated-input omni-training/data/curated/omni_seed_dataset.jsonl ^
  --output omni-training/data/sft/omni_sft_seed.jsonl
```

## Treino LoRA

Treino conservador:

```bash
python omni-training/scripts/train_lora.py
```

Smoke evaluation:

```bash
python omni-training/scripts/evaluate_lora.py --max-samples 3
```

## Decisões de arquitetura

- O código de treino fica isolado do runtime principal.
- A conversão para OIL reaproveita a OIL do Omni quando possível.
- Se o import da OIL do runtime falhar, a pipeline usa heurísticas locais compatíveis.
- Todos os artefatos intermediários são JSONL.
- Cada etapa é reexecutável e gera relatório resumido em `omni-training/reports/`.

## Limites atuais

- O treino LoRA é mínimo e reproduzível, não otimizado para clusters.
- O dataset público baixado nunca é usado cru; passa por filtro, normalização e conversão.
- O dataset curado inicial é pequeno por design.
