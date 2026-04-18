# Analise Evolutiva dos ZIPs

## Resumo Executivo

Os dois ZIPs trazem evolucoes importantes, mas com papeis diferentes:

- `claw-code-main.zip` traz uma camada Python/Rust bem modelada para runtime, sessao, registro de comandos/tools e persistencia simples.
- `src.zip` traz o cerebro mais completo em TypeScript, com `QueryEngine`, memoria em arquivo, sessao persistente, fila de mensagens, planejamento, busca em historico e base para multiagentes.

O projeto atual ficou funcional, mas simplificou demais tres areas:

1. inteligencia de decisao
2. memoria persistente e recuperacao de contexto
3. orquestracao de agente e execucao de capacidades

---

## Melhorias Encontradas

### 1. Runtime com registro real de capacidades

- Onde estava no zip:
  - `claw-code-main/src/execution_registry.py`
  - `claw-code-main/src/commands.py`
  - `claw-code-main/src/tools.py`
- O que fazia:
  - organizava comandos e tools espelhados em um `ExecutionRegistry`
  - permitia roteamento por nome e execucao por categoria
  - desacoplava runtime, engine e implementacoes
- Por que e melhor:
  - hoje o sistema atual responde quase so por heuristica textual
  - com um registro de capacidades, o agente pode raciocinar sobre o que sabe fazer antes de responder
- Como integrar:
  - manter o fluxo atual
  - adicionar um modulo Python que carregue um manifesto de capacidades e repasse isso para o Node runner como contexto de decisao

Prioridade: ALTA

Aplicar em:
- `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\python\main.py`
- `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\python\js-runner\queryEngineRunner.js`
- novo arquivo `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\python\brain_registry.py`

Codigo sugerido:

```python
# project/backend/python/brain_registry.py
from __future__ import annotations

import json
from pathlib import Path


def load_brain_registry() -> dict[str, list[dict[str, str]]]:
    root = Path(__file__).resolve().parents[2]
    commands_path = root / "claw-code-main" / "src" / "reference_data" / "commands_snapshot.json"
    tools_path = root / "claw-code-main" / "src" / "reference_data" / "tools_snapshot.json"

    def _safe_load(path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [item for item in data if isinstance(item, dict)]
        except Exception:
            return []

    return {
        "commands": _safe_load(commands_path),
        "tools": _safe_load(tools_path),
    }
```

```python
# trecho para main.py
from brain_registry import load_brain_registry

payload = json.dumps(
    {
        "message": message,
        "memory": memory_store.get("user", {}),
        "history": memory_store.get("history", []),
        "summary": summarize_history(memory_store.get("history", [])),
        "capabilities": load_brain_registry(),
    },
    ensure_ascii=False,
)
```

---

### 2. Sessao persistente de verdade, nao so ultimas 6 mensagens

- Onde estava no zip:
  - `claw-code-main/src/session_store.py`
  - `claw-code-main/src/transcript.py`
  - `src.zip/src/utils/sessionStorage.ts`
  - `src.zip/src/assistant/sessionHistory.ts`
- O que fazia:
  - salvava sessao, transcript, uso e mensagens
  - permitia retomar sessao e recuperar contexto historico
- Por que e melhor:
  - o projeto atual guarda so uma janela curta em `memory.json`
  - isso limita continuidade, aprendizado e coerencia em conversas maiores
- Como integrar:
  - manter `memory.json` como cache rapido
  - adicionar um `transcript.jsonl` ou `sessions/` para persistir historico completo
  - passar apenas recorte relevante ao Node runner

Prioridade: ALTA

Aplicar em:
- `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\python\main.py`
- novo arquivo `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\python\transcript_store.py`

Codigo sugerido:

```python
# project/backend/python/transcript_store.py
from __future__ import annotations

import json
from pathlib import Path


class TranscriptStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "transcript.jsonl"

    def append(self, role: str, content: str) -> None:
        entry = {"role": role, "content": content}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

```python
# trecho para main.py
from transcript_store import TranscriptStore

transcript_store = TranscriptStore(Path(__file__).resolve().parent / "sessions")
transcript_store.append("user", message)
transcript_store.append("assistant", response)
```

---

### 3. Memoria em arquivo com tipos e recall semantico

- Onde estava no zip:
  - `src.zip/src/memdir/memdir.ts`
  - `src.zip/src/memdir/memoryScan.ts`
  - `src.zip/src/memdir/memoryTypes.ts`
  - `src.zip/src/utils/teamMemoryOps.ts`
- O que fazia:
  - usava diretorio de memoria em arquivos Markdown
  - escaneava memorias, tipos, descricoes e tempos
  - separava memoria de usuario, projeto, referencia e feedback
- Por que e melhor:
  - o `memory.json` atual e util, mas pobre
  - ele nao diferencia tipos, nao indexa nem seleciona memorias relevantes por topico
- Como integrar:
  - manter `memory.json` para dados pequenos e estruturados
  - adicionar `memory/` com arquivos `.md`
  - na fase de `think()`, montar um manifesto das memorias mais relevantes

Prioridade: ALTA

Aplicar em:
- novo diretÃ³rio `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\python\memory`
- novo arquivo `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\python\memory_scan.py`
- `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\src\queryEngineRunnerAdapter.js`

Codigo sugerido:

```python
# project/backend/python/memory_scan.py
from __future__ import annotations

from pathlib import Path


def load_memory_manifest(memory_dir: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if not memory_dir.exists():
        return items

    for file_path in memory_dir.rglob("*.md"):
        if file_path.name.upper() == "MEMORY.MD":
            continue
        try:
            text = file_path.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        if not text:
            continue
        items.append(
            {
                "path": str(file_path),
                "preview": text[:220],
            }
        )
    return items[:40]
```

```js
// trecho para src/queryEngineRunnerAdapter.js
function retrieveRelevantMemory(thought) {
  const prefs = thought.preferences.join(' ');
  const haystack = normalizeText(`${thought.message} ${thought.contextSummary} ${prefs}`);
  const files = Array.isArray(thought.memoryFiles) ? thought.memoryFiles : [];
  return files.filter(item => normalizeText(item.preview).includes(haystack.split(' ')[0])).slice(0, 3);
}
```

---

### 4. Montagem inteligente de contexto antes da resposta

- Onde estava no zip:
  - `src.zip/src/utils/queryContext.ts`
  - `src.zip/src/QueryEngine.ts`
- O que fazia:
  - separava `systemPrompt`, `userContext`, `systemContext`, memoria e mensagens
  - criava contexto consistente para o loop principal
- Por que e melhor:
  - hoje o adapter recebe tudo junto e usa de forma rasa
  - isso reduz qualidade da decisao e dificulta evoluir para agente real
- Como integrar:
  - criar uma etapa `buildAgentContext()` no adapter
  - usar contexto resumido, preferencias, memoria recuperada, historico recente e capacidades

Prioridade: ALTA

Aplicar em:
- `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\src\queryEngineRunnerAdapter.js`

Codigo sugerido:

```js
function buildAgentContext(thought, capabilities) {
  return {
    objective: thought.message,
    user: {
      nome: thought.userName,
      preferencias: thought.preferences,
    },
    contextSummary: thought.contextSummary,
    recentHistory: thought.recentHistory,
    capabilities,
  };
}
```

---

### 5. Planejamento e execucao incremental

- Onde estava no zip:
  - `src.zip/src/utils/plans.ts`
  - `src.zip/src/utils/messageQueueManager.ts`
  - `src.zip/src/utils/forkedAgent.ts`
- O que fazia:
  - mantinha plano persistido
  - controlava fila de comandos/eventos
  - criava agentes forkados com contexto seguro
- Por que e melhor:
  - o sistema atual tem `THINK -> DECIDE -> ACT -> RESPOND`, mas tudo acontece em uma unica funcao curta
  - nao existe estado de execucao nem decomposicao de tarefa
- Como integrar:
  - sem quebrar o sistema atual, adicionar um `executionPlan` opcional no `thought`
  - usar isso primeiro para respostas complexas
  - depois evoluir para subagentes

Prioridade: MEDIA

Aplicar em:
- `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\src\queryEngineRunnerAdapter.js`

Codigo sugerido:

```js
function createExecutionPlan(thought) {
  if (thought.intent === 'dinheiro') {
    return ['diagnosticar contexto', 'escolher alavanca', 'montar plano pratico'];
  }
  if (thought.intent === 'aprendizado') {
    return ['avaliar nivel', 'ordenar fundamentos', 'propor pratica'];
  }
  return ['entender pedido', 'responder com utilidade'];
}
```

---

### 6. Busca agentica no historico

- Onde estava no zip:
  - `src.zip/src/utils/agenticSessionSearch.ts`
- O que fazia:
  - pesquisava sessoes passadas com relevancia semantica
  - selecionava historicos uteis antes de responder
- Por que e melhor:
  - hoje a IA so enxerga 6 mensagens
  - perguntas como "continuar aquilo que conversamos semana passada" nao escalam
- Como integrar:
  - manter simples no curto prazo
  - criar busca textual em transcripts persistidos
  - devolver 3 trechos relevantes ao adapter

Prioridade: MEDIA

Aplicar em:
- novo arquivo `C:\ORÃ‡AMETOS ANUAIS\Projeto omini\project\backend\python\history_search.py`

---

### 7. Thinking configuravel e governanca de custo/limite

- Onde estava no zip:
  - `src.zip/src/utils/thinking.ts`
  - `src.zip/src/query.ts`
- O que fazia:
  - controlava modo de pensamento, budget, compactacao e recuperacao de erro
- Por que e melhor:
  - o sistema atual nao tem niveis de profundidade reais
  - nao existe degradacao elegante para perguntas mais complexas
- Como integrar:
  - adicionar `thinking_mode` e `max_reasoning_steps` no payload Python -> Node

Prioridade: MEDIA

---

### 8. Multiagente e swarm

- Onde estava no zip:
  - `src.zip/src/utils/teammate.ts`
  - `src.zip/src/utils/forkedAgent.ts`
  - `src.zip/src/utils/standaloneAgent.ts`
- O que fazia:
  - suportava agentes auxiliares, isolamento de contexto e coordenacao
- Por que e melhor:
  - isso viabiliza automacao e execucao paralela de subtarefas
- Como integrar:
  - nao ativar agora no backend principal
  - preparar arquitetura para `delegates[]` no futuro

Prioridade: BAIXA no curto prazo, ALTA na visao de produto

---

## O Que Existia Antes e Nao Existe Agora

### Perdido ou simplificado demais

- Memoria em diretorios e arquivos tipados
- Sessao persistente completa
- Transcript estruturado
- Registro real de comandos e tools
- Montagem de contexto em camadas
- Busca em historico/sessoes
- Planejamento persistente
- Forked agents e swarm
- Controle de thinking/budget/compactacao

### O que foi preservado parcialmente

- ideia de runtime intermediario
- ideia de sessao
- ideia de memoria
- ideia de agente

### O que a versao atual tem de bom

- fluxo simples e estavel: Rust -> Python -> Node
- boa compatibilidade para stdout limpo
- memoria curta funcional
- adapter atual ja estruturado em `THINK -> DECIDE -> ACT -> RESPOND`

---

## Melhor Arquitetura Combinando Atual + ZIPs

```text
React / Mobile
  -> Rust API
    -> Python Orchestrator
      -> Context Builder
      -> Memory Layer
        -> memory.json
        -> memory/*.md
        -> sessions/transcript.jsonl
      -> Capability Registry
      -> Node QueryEngine Agent
        -> think
        -> decide
        -> plan
        -> act
        -> respond
      -> safe fallback
```

---

## Ordem Recomendada de Evolucao

### Fase 1

- adicionar `brain_registry.py`
- adicionar `transcript_store.py`
- enriquecer payload Python -> Node com `capabilities`
- criar `buildAgentContext()` no adapter

### Fase 2

- adicionar `memory/` com manifesto de memorias
- criar busca por memoria relevante
- melhorar `think()` com evidencias de memoria e historico

### Fase 3

- introduzir plano incremental
- buscar historico persistido
- preparar execucao delegada

### Fase 4

- multiagente real
- auto-melhoria
- aprendizado continuo com curadoria

---

## Recomendacao Final

A melhor direcao nao e substituir o sistema atual.

A melhor direcao e:

1. manter o backend atual estavel
2. importar do `claw-code-main` a modelagem Python de runtime, registro e sessao
3. importar do `src.zip` a inteligencia de contexto, memoria, busca, plano e agente
4. usar o adapter atual como ponto de encaixe para evoluir gradualmente

O ganho imediato mais forte vem de:

- memoria em arquivo + manifesto
- transcript persistido
- capability registry
- contexto montado antes do `THINK`

