# Omni — Cognitive Runtime System

> Not a chatbot.  
> A runtime that decides, executes, observes, and learns.

---

## What is Omni?

Omni is an experimental cognitive runtime system designed to go beyond text generation.

Instead of only responding, Omni can:

- interpret intent
- choose an execution strategy
- execute real actions through tools, runtimes, and providers
- observe outcomes
- evaluate decision quality
- learn from every interaction

---

## Why Omni Exists

Most AI systems today:

- generate text
- hide execution details
- fail silently
- cannot explain why they did something
- do not learn from their own behavior

Omni is built to solve that by treating each turn as an explicit runtime flow instead of a text-only answer.

---

## Core Idea

Every interaction follows a full cognitive loop:

```txt
Input -> Decision -> Execution -> Observation -> Evaluation -> Learning
```

Omni makes this loop:

- explicit
- traceable
- testable
- improvable

---

## Architecture

Omni is a multi-runtime system:

- Rust -> API boundary
- Python -> cognitive runtime, orchestration, control
- Node/Bun -> execution engine, providers, tool planning
- React/Vite -> UI and runtime observability

Core layers:

- Decision Layer
- Execution Layer
- Observability Layer
- Provider Layer
- Learning Layer

Architecture references:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/architecture/layers.md](docs/architecture/layers.md)
- [docs/architecture/runtime-flow.md](docs/architecture/runtime-flow.md)
- [docs/architecture/runtime-modes.md](docs/architecture/runtime-modes.md)
- [docs/architecture/provider-routing.md](docs/architecture/provider-routing.md)
- [docs/architecture/tool-runtime.md](docs/architecture/tool-runtime.md)
- [docs/architecture/cognitive-decision-model.md](docs/architecture/cognitive-decision-model.md)
- [docs/architecture/learning-loop.md](docs/architecture/learning-loop.md)

---

## Runtime Truth

Omni exposes what actually happened on a turn:

- execution path used
- provider selected
- fallback triggered
- compatibility execution state
- tool execution result
- failure classification
- decision reasoning
- learning signals

No hidden behavior. No fake success.

---

## Learning Loop

Omni records every execution as a structured learning record:

```json
{
  "input": "...",
  "strategy": "...",
  "execution_path": "...",
  "tool_used": "...",
  "success": true,
  "decision_correct": true
}
```

It then generates advisory improvement signals such as:

- routing improvements
- fallback reduction
- tool selection improvements

Important:

- Omni does not auto-modify itself
- learning signals are stored locally
- all improvements remain controlled and observable

---

## Current Status

Experimental and under active development.

What works:

- real execution paths through tools and Node runtime
- truthful runtime classification
- failure-safe bridge pipeline
- provider diagnostics
- tool execution diagnostics
- decision validation system
- controlled learning loop

What is still evolving:

- decision quality for ambiguous prompts
- tool success rate across environments
- dataset expansion
- adaptive routing improvements

Current public debug posture:

- [docs/public-debug/PROJECT_STATUS.md](docs/public-debug/PROJECT_STATUS.md)
- [docs/public-debug/KNOWN_ISSUES.md](docs/public-debug/KNOWN_ISSUES.md)
- [docs/public-debug/REPRODUCTION.md](docs/public-debug/REPRODUCTION.md)
- [docs/public-debug/LEARNING_DEBUGGING.md](docs/public-debug/LEARNING_DEBUGGING.md)

---

## Getting Started

```bash
git clone <repo>
cd project
cp .env.example .env
```

Install dependencies:

```bash
npm install
pip install -r backend/python/requirements.txt
```

Optional training dependencies:

```bash
pip install -r omni-training/requirements.txt
```

Run the Python runtime directly:

```bash
python backend/python/main.py
```

Run the Rust API:

```bash
cargo run --manifest-path backend/rust/Cargo.toml
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Useful validation commands:

```bash
npm run test:node
npm run test:python
npm run test:e2e:chat-contract
```

---

## Debugging Omni

The frontend includes a runtime debug panel showing:

- runtime mode
- execution path
- provider diagnostics
- tool execution state
- failure class
- decision reasoning
- learning signals

You can inspect most failures without opening backend logs first.

---

## Contributing

We want contributors in:

- runtime execution
- decision logic
- tool integration
- observability
- frontend debug UX
- dataset and evaluation

Start here:

1. [CONTRIBUTING.md](CONTRIBUTING.md)
2. [docs/public-debug/PROJECT_STATUS.md](docs/public-debug/PROJECT_STATUS.md)
3. [docs/public-debug/REPRODUCTION.md](docs/public-debug/REPRODUCTION.md)
4. [docs/public-debug/LEARNING_DEBUGGING.md](docs/public-debug/LEARNING_DEBUGGING.md)

---

## Roadmap

- Phase 1-6 -> runtime foundation
- Phase 7-8 -> providers and tools
- Phase 9 -> decision validation
- Phase 10 -> learning loop
- Next:
  - dataset auto-generation
  - model improvement with LoRA
  - adaptive routing
  - controlled evolution

See [ROADMAP.md](ROADMAP.md).

---

## Philosophy

Omni is built on one principle:

> A system is only as good as its ability to explain and improve its own decisions.

---

## License

See [LICENSE](LICENSE).

---

## Final Note

Omni is not trying to be another AI wrapper.

It is an attempt to build a transparent, executable, and evolvable cognitive runtime.
