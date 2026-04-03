const { runMultiAgentRuntime } = require('./orchestrator');
const { listAgents, listCapabilities } = require('./registry');

async function runQueryEngine({ message, memoryContext, history, summary, capabilities, session }) {
  return runMultiAgentRuntime({
    message,
    memoryContext,
    history,
    summary,
    capabilities: Array.isArray(capabilities) && capabilities.length > 0 ? capabilities : listCapabilities(),
    session: {
      ...(session && typeof session === 'object' ? session : {}),
      agent_registry: Array.isArray(session?.agent_registry) ? session.agent_registry : listAgents(),
    },
  });
}

module.exports = {
  runQueryEngine,
};
