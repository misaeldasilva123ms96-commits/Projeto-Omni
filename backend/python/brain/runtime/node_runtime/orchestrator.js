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

  switch (thought.intent) {
    case 'saudacao':
      return { response: actionResult.greeting, confidence, memory: memorySignal };
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
        response: `${opener}${actionResult.plan.title}:
1. ${actionResult.plan.steps[0]}
2. ${actionResult.plan.steps[1]}
3. ${actionResult.plan.steps[2]}
${actionResult.plan.closing}`,
        confidence,
        memory: memorySignal,
      };
    case 'ideacao':
      return {
        response: `Aqui vão 3 ideias fortes:
1. ${actionResult.ideas[0]}
2. ${actionResult.ideas[1]}
3. ${actionResult.ideas[2]}`,
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
        response: `${opener}Eu seguiria um caminho realista:
1. ${actionResult.payload[0]}
2. ${actionResult.payload[1]}
3. ${actionResult.payload[2]}`,
        confidence,
        memory: memorySignal,
      };
    case 'aprendizado':
      return {
        response: `${opener}O melhor caminho agora é este:
1. ${actionResult.steps[0]}
2. ${actionResult.steps[1]}
3. ${actionResult.steps[2]}`,
        confidence,
        memory: memorySignal,
      };
    case 'pessoal':
      return {
        response: thought.userName
          ? `${actionResult.identity} Também levo em conta o que você já me contou, ${thought.userName}.`
          : actionResult.identity,
        confidence,
        memory: memorySignal,
      };
    case 'explicacao':
      return {
        response: actionResult.explanation.join(' '),
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
  const actionResult = act(thought, decision, planResult);
  const reviewResult = review(thought, decision, actionResult);
  const memorySignal = buildMemorySignal(thought, planResult.executionPlan);
  const response = respond(actionResult, thought, decision, reviewResult, memorySignal);

  return {
    ...response,
    strategy: decision.strategy,
    delegates: thought.delegates,
    agentTrace: [
      { agent: 'researcher_agent', output: { intent: thought.intent, contextSummary: thought.contextSummary } },
      { agent: 'planner_agent', output: planResult },
      { agent: 'executor_agent', output: actionResult },
      { agent: 'reviewer_agent', output: reviewResult },
      { agent: 'memory_agent', output: memorySignal },
    ],
    registry: listAgents(),
  };
}

module.exports = {
  runMultiAgentRuntime,
};
