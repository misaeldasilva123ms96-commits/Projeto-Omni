const fs = require('fs');
const path = require('path');
const { listAgents, listCapabilities } = require('./registry');
const { buildMemorySignal } = require('./memory');
const { think } = require('./researcher');
const { decide, plan } = require('./planner');
const { act } = require('./executor');
const { review } = require('./reviewer');

function maybeUseName(thought) {
  if (!thought.userName) {
    return '';
  }

  if (['decision', 'conselho', 'dinheiro', 'planejamento'].includes(thought.intent)) {
    return `${thought.userName}, `;
  }

  return '';
}

function respond(actionResult, thought, decision, reviewResult, memorySignal) {
  const opener = maybeUseName(thought);
  const confidence = Math.min(0.99, decision.confidence * reviewResult.qualityScore);

  if (typeof actionResult?.response === 'string' && actionResult.response.trim()) {
    return {
      response: actionResult.response.trim(),
      confidence,
      memory: memorySignal,
    };
  }

  switch (thought.intent) {
    case 'saudacao':
      return { response: actionResult.greeting || 'Olá! Como posso te ajudar hoje?', confidence, memory: memorySignal };
    case 'pergunta_direta':
      return { response: actionResult.answer, confidence, memory: memorySignal };
    case 'comparativo':
      return {
        response: `${actionResult.comparison.intro} Prós: ${actionResult.comparison.pros.join(' ')} Contras: ${actionResult.comparison.cons.join(' ')} ${actionResult.comparison.recommendation}`,
        confidence,
        memory: memorySignal,
      };
    case 'planejamento':
      return {
        response: `${opener}${actionResult.plan.title}:\n1. ${actionResult.plan.steps[0]}\n2. ${actionResult.plan.steps[1]}\n3. ${actionResult.plan.steps[2]}\n${actionResult.plan.closing}`,
        confidence,
        memory: memorySignal,
      };
    case 'ideacao':
      return {
        response: `Aqui vão 3 ideias fortes:\n1. ${actionResult.ideas[0]}\n2. ${actionResult.ideas[1]}\n3. ${actionResult.ideas[2]}`,
        confidence,
        memory: memorySignal,
      };
    case 'decision':
    case 'conselho':
      return {
        response: `${opener}${actionResult.analysis[0]} ${actionResult.analysis[1]} ${actionResult.recommendation}`,
        confidence,
        memory: memorySignal,
      };
    case 'dinheiro':
      return {
        response: `${opener}Eu seguiria um caminho realista:\n1. ${actionResult.payload[0]}\n2. ${actionResult.payload[1]}\n3. ${actionResult.payload[2]}`,
        confidence,
        memory: memorySignal,
      };
    case 'aprendizado':
      return {
        response: `${opener}O melhor caminho agora é este:\n1. ${actionResult.steps[0]}\n2. ${actionResult.steps[1]}\n3. ${actionResult.steps[2]}`,
        confidence,
        memory: memorySignal,
      };
    case 'pessoal':
      return {
        response: thought.userName ? `${actionResult.identity} Também levo em conta o que você já me contou, ${thought.userName}.` : actionResult.identity,
        confidence,
        memory: memorySignal,
      };
    case 'explicacao':
      return {
        response: Array.isArray(actionResult.explanation) ? actionResult.explanation.join(' ') : 'Posso te explicar esse conceito de forma clara e prática.',
        confidence,
        memory: memorySignal,
      };
    default:
      return {
        response: `${actionResult.conversation} Se quiser, me diga o objetivo principal e eu organizo a resposta com mais precisão.`,
        confidence,
        memory: memorySignal,
      };
  }
}

function persistRuntimeMeta(session, executionMeta) {
  if (typeof session?.runtime_meta_path !== 'string' || !session.runtime_meta_path.trim()) {
    return;
  }

  try {
    fs.mkdirSync(path.dirname(session.runtime_meta_path), { recursive: true });
    fs.writeFileSync(session.runtime_meta_path, JSON.stringify(executionMeta, null, 2), 'utf8');
  } catch (_error) {
    // Keep runtime resilient if metadata persistence fails.
  }
}

async function runMultiAgentRuntime({ message, memoryContext, history, summary, capabilities, session }) {
  const thought = think({
    message,
    memoryContext,
    history,
    summary,
    capabilities: Array.isArray(capabilities) && capabilities.length > 0 ? capabilities : listCapabilities(),
    session,
  });
  const decision = decide(thought);
  const planResult = plan(thought, decision);
  const actionResult = await act(thought, decision, planResult);
  const reviewResult = review(thought, decision, actionResult);
  const memorySignal = buildMemorySignal(thought, planResult.executionPlan);
  const response = respond(actionResult, thought, decision, reviewResult, memorySignal);
  const executionMeta = {
    strategy: decision.strategy,
    intent: thought.intent,
    provider: actionResult?.provider || 'unknown',
    latency_ms: typeof actionResult?.latencyMs === 'number' ? actionResult.latencyMs : 0,
    fallback_used: Boolean(actionResult?.fallbackUsed),
    selected_mode: actionResult?.selectedMode || 'heuristic',
    adaptive_reason: actionResult?.adaptiveReason || 'unknown',
    task_category: thought.taskCategory,
    prompt_complexity: thought.promptComplexity,
  };
  const executorTrace = {
    agent: 'executor_agent',
    output: {
      strategy: decision.strategy,
      provider: executionMeta.provider,
      latencyMs: executionMeta.latency_ms,
      fallbackUsed: executionMeta.fallback_used,
      selectedMode: executionMeta.selected_mode,
      adaptiveReason: executionMeta.adaptive_reason,
      confidence: typeof actionResult?.confidence === 'number' ? actionResult.confidence : undefined,
      planLength: Array.isArray(actionResult?.executionPlan) ? actionResult.executionPlan.length : 0,
      taskCategory: thought.taskCategory,
    },
  };

  persistRuntimeMeta(session, executionMeta);

  return {
    ...response,
    strategy: decision.strategy,
    executionMeta,
    delegates: thought.delegates,
    agentTrace: [
      { agent: 'researcher_agent', output: { intent: thought.intent, contextSummary: thought.contextSummary, taskCategory: thought.taskCategory, promptComplexity: thought.promptComplexity } },
      { agent: 'planner_agent', output: planResult },
      executorTrace,
      { agent: 'reviewer_agent', output: reviewResult },
      { agent: 'memory_agent', output: memorySignal },
    ],
    registry: listAgents(),
  };
}

module.exports = {
  runMultiAgentRuntime,
};
