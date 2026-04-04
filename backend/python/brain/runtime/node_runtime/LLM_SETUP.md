# Omini AI LLM Provider Setup

The Node executor can call a real language model through `llm_adapter.js` without changing the current architecture:

`Frontend -> Rust API -> Python brain -> Node multi-agent runtime`

## Supported environment variables

Set only the provider you want to activate.

```env
OPENAI_API_KEY=
OPENAI_MODEL=
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=
OLLAMA_URL=
OLLAMA_MODEL=
```

## Provider selection order

The runtime chooses the first configured provider in this order:

1. `OPENAI_API_KEY`
2. `ANTHROPIC_API_KEY`
3. `OLLAMA_URL`
4. local fallback

If more than one provider is configured, OpenAI wins because it is checked first.

## What happens when nothing is configured

If no provider variable is set, the executor does **not** fail.

It falls back to the current local heuristic response builders already present in the runtime. This keeps the multi-agent flow working offline and preserves compatibility with the Python and Rust layers.

## How to activate each provider

### OpenAI

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

`OPENAI_MODEL` is optional. If omitted, the adapter uses its internal default.

### Anthropic

```env
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-latest
```

`ANTHROPIC_MODEL` is optional. If omitted, the adapter uses its internal default.

### Ollama

```env
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1
```

`OLLAMA_MODEL` is optional. If omitted, the adapter uses its internal default.

## Runtime behavior

- The planner still builds the reasoning plan.
- The executor sends that plan to the LLM adapter as internal context.
- The final answer returned to the user must not expose:
  - execution plans
  - internal reasoning
  - agent names
  - planner text

## Development logging

When `NODE_ENV=development`, the adapter may log:

- selected strategy
- provider name
- execution plan length
- LLM latency

It should not log raw user content in production.

## Safe test commands

Run the Python entrypoint exactly as before:

```powershell
python backend/python/main.py "explique como funciona machine learning"
python backend/python/main.py "analise os prós e contras de usar Python vs Rust para sistemas de IA em produção"
python backend/python/main.py "crie um plano de negócios para um app de delivery"
python backend/python/main.py "me dê 3 ideias inovadoras de startup em IA"
```

Expected behavior:

- with provider configured: natural language should come from the selected LLM
- without provider configured: the local fallback still answers without breaking the runtime
