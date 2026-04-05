const SPECIALIST_AGENTS = [
  {
    id: 'master_orchestrator',
    role: 'master',
    source: 'project',
    description: 'Single authority that coordinates planning, delegation, execution, and final response synthesis.',
    allowedTools: [],
    capabilities: ['plan', 'delegate', 'final-synthesis', 'runtime-routing'],
    failurePolicy: 'stop-and-report',
  },
  {
    id: 'task_planner',
    role: 'planner',
    source: 'src.zip',
    description: 'Builds task decomposition, constraints, and step ordering from the QueryEngine lineage.',
    allowedTools: [],
    capabilities: ['task-decomposition', 'constraint-extraction', 'step-budgeting'],
    failurePolicy: 'fallback-to-master',
  },
  {
    id: 'memory_manager',
    role: 'memory',
    source: 'src.zip',
    description: 'Hydrates session, working, and persistent memory into the live task context.',
    allowedTools: [],
    capabilities: ['memory-retrieval', 'memory-write-filtering', 'context-injection'],
    failurePolicy: 'degrade-context',
  },
  {
    id: 'researcher_agent',
    role: 'researcher',
    source: 'src.zip',
    description: 'Executes read/search-oriented steps and normalizes findings for the orchestrator.',
    allowedTools: ['read_file', 'glob_search', 'grep_search'],
    capabilities: ['workspace-reading', 'search', 'artifact-summarization'],
    failurePolicy: 'stop-on-read-failure',
  },
  {
    id: 'coder_agent',
    role: 'coder',
    source: 'src.zip',
    description: 'Owns write-oriented steps under explicit approval and returns structured write results.',
    allowedTools: ['write_file'],
    capabilities: ['content-generation', 'file-write-preparation'],
    failurePolicy: 'require-approval',
  },
  {
    id: 'reviewer_agent',
    role: 'reviewer',
    source: 'openclaude-main.zip',
    description: 'Reviews step outputs, detects partial failure, and helps normalize the final grounded answer.',
    allowedTools: [],
    capabilities: ['result-normalization', 'failure-propagation', 'completion-check'],
    failurePolicy: 'warn-only',
  },
  {
    id: 'evaluator_agent',
    role: 'evaluator',
    source: 'project',
    description: 'Inspects step outputs and chooses whether to continue, retry, revise, or stop.',
    allowedTools: [],
    capabilities: ['step-evaluation', 'retry-decision', 'blocker-detection'],
    failurePolicy: 'fallback-to-stop',
  },
  {
    id: 'critic_agent',
    role: 'critic',
    source: 'project',
    description: 'Reviews risky plans and weak outcomes to recommend bounded revision, retry, escalation, or stop.',
    allowedTools: [],
    capabilities: ['plan-review', 'outcome-critique', 'risk-gating'],
    failurePolicy: 'warn-only',
  },
  {
    id: 'synthesizer_agent',
    role: 'synthesizer',
    source: 'project',
    description: 'Turns multi-step grounded execution history into the final user-facing answer.',
    allowedTools: [],
    capabilities: ['grounded-synthesis', 'multi-step-summary'],
    failurePolicy: 'fallback-to-raw-results',
  },
  {
    id: 'provider_router',
    role: 'platform',
    source: 'openclaude-main.zip',
    description: 'Keeps provider/model routing separate from cognition and execution.',
    allowedTools: [],
    capabilities: ['provider-selection', 'fallback-routing', 'bootstrap-awareness'],
    failurePolicy: 'fallback-to-local',
  },
  {
    id: 'rust_executor',
    role: 'executor',
    source: 'claw-code-main.zip',
    description: 'Real execution authority for permissioned tool use, usage tracking, and auditable actions.',
    allowedTools: ['read_file', 'glob_search', 'grep_search', 'write_file'],
    capabilities: ['permissioned-execution', 'usage-accounting', 'audit-trail'],
    failurePolicy: 'authoritative-stop',
  },
];

function listSpecialistAgents() {
  return SPECIALIST_AGENTS.map(agent => ({ ...agent }));
}

function getSpecialistAgent(agentId) {
  return SPECIALIST_AGENTS.find(agent => agent.id === agentId) || null;
}

function resolveSpecialistsForIntent(intent) {
  switch (intent) {
    case 'memory':
      return ['master_orchestrator', 'memory_manager', 'reviewer_agent'];
    case 'analysis':
      return ['master_orchestrator', 'task_planner', 'researcher_agent', 'evaluator_agent', 'critic_agent', 'reviewer_agent', 'synthesizer_agent', 'provider_router'];
    case 'execution':
      return ['master_orchestrator', 'task_planner', 'memory_manager', 'researcher_agent', 'coder_agent', 'evaluator_agent', 'critic_agent', 'reviewer_agent', 'synthesizer_agent', 'rust_executor'];
    case 'planning':
      return ['master_orchestrator', 'task_planner', 'evaluator_agent', 'critic_agent', 'reviewer_agent', 'synthesizer_agent', 'provider_router'];
    default:
      return ['master_orchestrator', 'task_planner', 'memory_manager', 'researcher_agent', 'evaluator_agent', 'critic_agent', 'reviewer_agent', 'synthesizer_agent', 'provider_router', 'rust_executor'];
  }
}

module.exports = {
  getSpecialistAgent,
  listSpecialistAgents,
  resolveSpecialistsForIntent,
};
