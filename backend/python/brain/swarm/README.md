# Swarm Layer

Esta camada adiciona orquestracao multiagente em cima do brain atual sem quebrar o fluxo:

`Rust -> Python main.py -> BrainOrchestrator -> SwarmOrchestrator -> Node runner -> stdout`

## Agentes

- `RouterAgent`: classifica a intent e decide quais agentes entram no fluxo
- `PlannerAgent`: decompõe pedidos complexos em subtarefas
- `ExecutorAgent`: executa subtarefas e prepara a chamada principal ao Node
- `CriticAgent`: revisa a qualidade antes da entrega final
- `MemoryAgent`: consolida sinais de memoria e ajuda na persistencia

## Pipeline

```text
Input
  |
  v
RouterAgent
  |
  v
PlannerAgent
  |
  v
ExecutorAgent(s) em paralelo
  |
  v
Node QueryEngine / delegates
  |
  v
CriticAgent
  |
  v
MemoryAgent
  |
  v
Output final
```

## Diagrama ASCII

```text
+-------------+      +-------------+      +---------------+
|   Router    | ---> |   Planner   | ---> |   Executors   |
+-------------+      +-------------+      +---------------+
        |                    |                     |
        |                    v                     v
        |             subtasks/plan        delegate notes
        |                                          |
        +--------------------> Node Runner <-------+
                                   |
                                   v
                             +-----------+
                             |  Critic   |
                             +-----------+
                                   |
                                   v
                             +-----------+
                             |  Memory   |
                             +-----------+
                                   |
                                   v
                               final text
```

## Exemplo de execucao

Entrada:

```text
me de uma ideia de negocio
```

Trace interno esperado:

```text
RouterAgent  -> intent=dinheiro, delegates=[planner_agent, executor_agent, critic_agent, memory_agent]
PlannerAgent -> cria subtarefas de contexto, execucao e revisao
ExecutorAgent -> prepara contexto local e aciona o Node runner principal
CriticAgent -> valida utilidade e tamanho da resposta
MemoryAgent -> consolida sinais e registra trace em sessao/log
```

Arquivos relevantes:

- `brain/runtime/swarm_log.json`
- `brain/runtime/sessions/<session_id>.json`

O campo `agent_trace` fica salvo na sessao para debug e inspeção futura.
