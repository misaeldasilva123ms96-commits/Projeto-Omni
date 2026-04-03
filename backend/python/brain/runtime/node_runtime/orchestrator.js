const { listAgents, listCapabilities } = require('./registry');
const { buildMemorySignal } = require('./memory');
const { think } = require('./researcher');
const { decide, plan } = require('./planner');
const { act } = require('./executor');
const { review } = require('./reviewer');

function maybeUseName(thought) {
  return thought.userName ? `${thought.userName}, ` : '';
}

function respond(actionResult, thought, decision, reviewResult, memorySignal) {
  const opener = maybeUseName(thought);

  switch (thought.intent) {
    case 'decision':
    case 'conselho':
      return {
        response: `${opener}${actionResult.analysis[0]} ${actionResult.analysis[1]} ${actionResult.recommendation}`,
        confidence: Math.min(0.99, decision.confidence * reviewResult.qualityScore),
        memory: memorySignal,
      };
    case 'dinheiro':
      return {
        response: `${opener}eu seguiria um caminho realista:\n1. ${actionResult.payload[0]}\n2. ${actionResult.payload[1]}\n3. ${actionResult.payload[2]}`,
        confidence: Math.min(0.99, decision.confidence * reviewResult.qualityScore),
        memory: memorySignal,
      };
    case 'aprendizado':
      return {
        response: `${opener}o melhor caminho agora e este:\n1. ${actionResult.steps[0]}\n2. ${actionResult.steps[1]}\n3. ${actionResult.steps[2]}`,
        confidence: Math.min(0.99, decision.confidence * reviewResult.qualityScore),
        memory: memorySignal,
      };
    case 'pessoal':
      return {
        response: thought.userName
          ? `${actionResult.identity} Tambem levo em conta o que voce ja me contou, ${thought.userName}.`
          : actionResult.identity,
        confidence: Math.min(0.99, decision.confidence * reviewResult.qualityScore),
        memory: memorySignal,
      };
    case 'explicacao':
      return {
        response: `${opener}eu pensaria assim: ${actionResult.explanation[0]}, depois ${actionResult.explanation[1]} e por fim ${actionResult.explanation[2]}.`,
        confidence: Math.min(0.99, decision.confidence * reviewResult.qualityScore),
        memory: memorySignal,
      };
    default:
      return {
        response: `${opener}${actionResult.conversation} Se quiser, me diga o objetivo principal e eu organizo a resposta com mais precisao.`,
        confidence: Math.min(0.99, decision.confidence * reviewResult.qualityScore),
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
