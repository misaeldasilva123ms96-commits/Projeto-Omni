const { randomUUID } = require('crypto');
const path = require('path');

const { loadRuntimeConfig } = require('../../configs/runtimeConfig');
const { buildBrainExecutorAction } = require('../planning/brainExecutorContract');
const { buildMemoryLayers } = require('../memory/memoryLayers');
const { chooseProvider } = require('../../platform/providers/providerRouter');
const { runRustExecutor } = require('../../runtime/execution/rustExecutorBridge');
const { resolveExecutionMode } = require('../../runtime/execution/runtimeMode');
const { appendExecutionAudit, appendRuntimeTranscript } = require('../../storage/transcripts/transcriptPersistence');
const { buildSessionSnapshot } = require('../../storage/sessions/sessionPersistence');
const { buildMemorySnapshot } = require('../../storage/memory/memoryPersistence');
const {
  getSessionRuntimeMemory,
  findSemanticMatches,
  recordRuntimeArtifacts,
  updateSessionRuntimeMemory,
  updateWorkingMemory,
} = require('../../storage/memory/runtimeMemoryStore');
const { buildRuntimeTrace } = require('../../observability/tracing/runtimeAudit');
const { buildDelegationPlan } = require('../../features/multiagent/delegationLayer');
const { planTask } = require('../../features/multiagent/specialists/advancedPlannerSpecialist');
const { enrichWithMemory } = require('../../features/multiagent/specialists/memorySpecialist');
const { extractArtifacts, summarizeExecutionResult } = require('../../features/multiagent/specialists/researcherSpecialist');
const { synthesizeFinalAnswer } = require('../../features/multiagent/specialists/reviewerSpecialist');
const { evaluateStepResult } = require('../../features/multiagent/specialists/evaluatorSpecialist');
const { reviewPlan } = require('../../features/multiagent/specialists/criticSpecialist');
const { synthesizeGroundedResponse } = require('../../features/multiagent/specialists/synthesizerSpecialist');
const { normalizeWriteRequest } = require('../../features/multiagent/specialists/coderSpecialist');
const { getFusionSourceMap } = require('./fusedSources');
const { buildRustRuntimeManifest } = require('../../runtime/execution/rustRuntimeManifest');
const { getKairosManifest } = require('../../features/kairos/manifest');
const { getCodexIntegrationStatus } = require('../../platform/integrations/codexIntegration');
const { getCliPlatformManifest } = require('../../platform/cli/manifest');

function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function inferIntent(message) {
  const text = normalizeText(message);
  if (/^(oi|ola|olá|bom dia|boa tarde|boa noite)$/.test(text)) return 'greeting';
  if (text.includes('meu nome') || text.includes('eu trabalho com')) return 'memory';
  if (text.includes('leia') || text.includes('arquivo') || text.includes('readme')) return 'execution';
  if (text.includes('liste') || text.includes('arquivos') || text.includes('pastas')) return 'execution';
  if (text.includes('busque') || text.includes('procure') || text.includes('grep')) return 'execution';
  if (text.includes('crie o arquivo') || text.includes('escreva no arquivo') || text.includes('salve')) return 'execution';
  if (text.includes('analise') || text.includes('resuma')) return 'analysis';
  return 'conversation';
}

function inferComplexity(message) {
  const text = normalizeText(message);
  const words = text.split(/\s+/).filter(Boolean);
  return words.length > 20 || /\b(depois|perspectiva|entao|então|e)\b/.test(text)
    ? 'complex'
    : 'simple';
}

function directResponseFromMemory(message, mergedMemory) {
  const text = normalizeText(message);
  if (text.includes('meu nome') && mergedMemory.nome && !text.includes('meu nome e')) {
    return `Seu nome é ${mergedMemory.nome}.`;
  }
  if (text.includes('com o que eu trabalho') && mergedMemory.trabalho) {
    return `Você trabalha com ${mergedMemory.trabalho}.`;
  }
  if (text.includes('meu nome e')) {
    return 'Entendi. Vou registrar seu nome no contexto desta sessão.';
  }
  if (text.includes('eu trabalho com')) {
    return 'Entendi. Vou registrar seu trabalho no contexto desta sessão.';
  }
  return '';
}

function buildMergedMemory(memoryLayers, runtimeMemory) {
  return {
    ...runtimeMemory,
    ...memoryLayers.long_term,
  };
}

function absolutizeToolArguments(workspace, selectedTool, toolArguments, useRelativeWorkspacePaths = false) {
  const args = { ...(toolArguments || {}) };
  if (selectedTool === 'write_file') {
    return normalizeWriteRequest({
      toolArguments: args,
      goal: args.goal,
    });
  }

  if (typeof args.path === 'string' && args.path) {
    args.path = useRelativeWorkspacePaths || path.isAbsolute(args.path)
      ? args.path
      : path.resolve(workspace, args.path);
  }

  if (selectedTool === 'glob_search' && typeof args.path !== 'string') {
    args.path = useRelativeWorkspacePaths ? '.' : workspace;
  }
  return args;
}

function buildActionAudit(workspace, delegation) {
  return {
    source_map: getFusionSourceMap(workspace),
    rust_runtime: buildRustRuntimeManifest(workspace),
    kairos: getKairosManifest(workspace),
    codex: getCodexIntegrationStatus(),
    cli_platform: getCliPlatformManifest(),
    delegated_by: delegation.master,
    delegation_contract: delegation.delegation_contract,
  };
}

class QueryEngineAuthority {
  constructor(config = {}) {
    this.config = config;
    this.mutableMessages = config.initialMessages || [];
  }

  async submitMessage({ message, memoryContext, history, summary, capabilities, session, cwd }) {
    const workspace = cwd || process.cwd();
    const sessionId = session?.session_id || 'ephemeral-session';
    const runtimeConfig = loadRuntimeConfig();
    const runtimeMode = resolveExecutionMode({
      cwd: workspace,
      requestedMode: session?.runtime_mode || runtimeConfig.requestedExecutionMode,
    });
    const taskId = session?.task_id || `task-${randomUUID()}`;
    const runId = session?.run_id || `run-${randomUUID()}`;
    const actionIdBase = randomUUID();
    const intent = inferIntent(message);
    const complexity = inferComplexity(message);
    const provider = chooseProvider({ complexity });
    const memoryLayers = buildMemoryLayers({ memoryContext, history, session });
    const runtimeMemory = getSessionRuntimeMemory(workspace, sessionId);
    const semanticMatches = findSemanticMatches(workspace, sessionId, message, 3);
    const memoryHints = enrichWithMemory({
      message,
      memoryLayers,
      runtimeMemory,
      semanticMatches,
    });
    const retrievalContext = memoryHints.retrieval_context || {};
    const mergedMemory = buildMergedMemory(memoryLayers, runtimeMemory);
    const directMemoryResponse = directResponseFromMemory(message, {
      ...mergedMemory,
      ...memoryHints,
    });

    const delegation = buildDelegationPlan({
      intent: intent === 'analysis' ? 'analysis' : intent === 'memory' ? 'memory' : 'execution',
      complexity,
    });
    const plannerResult = planTask({
      message,
      sessionId,
      retrievalContext,
      runtimeConfig,
    });
    const criticPlanReview = reviewPlan({
      steps: plannerResult.steps,
      planGraph: plannerResult.plan_graph,
      complexity,
      intent,
      runtimeConfig,
    });

    const actions = plannerResult.steps.map((step, index) => buildBrainExecutorAction({
      actionId: `${actionIdBase}:${index + 1}`,
      stepId: step.step_id,
      strategy: intent === 'analysis' ? 'comparative_analysis' : intent === 'memory' ? 'memory_recall' : 'real_execution',
      stepGoal: step.goal,
      dependencyStepIds: Array.isArray(step.depends_on) ? step.depends_on : [],
      selectedTool: step.selected_tool,
      selectedAgent: step.selected_agent,
      permissionRequirement: step.selected_tool === 'write_file' ? 'explicit_approval_required' : 'allow_read_only',
      approvalState: step.selected_tool === 'write_file' ? 'pending' : 'approved',
      executionContext: {
        session_id: sessionId,
        task_id: taskId,
        run_id: runId,
        project_root: runtimeMode.primary.owner === 'python' ? '..\\..' : workspace,
        provider: provider.name,
        complexity,
        runtime_mode: runtimeMode.primary.mode,
        runtime_mode_fallback: runtimeMode.fallback?.mode || null,
        plan_kind: plannerResult.plan_kind || 'linear',
        available_capabilities: Array.isArray(capabilities) ? capabilities.map(item => item.name) : [],
      },
      toolArguments: absolutizeToolArguments(
        workspace,
        step.selected_tool,
        step.tool_arguments,
        runtimeMode.primary.owner === 'python',
      ),
      timeoutMs: runtimeConfig.stepTimeoutMs,
      retryPolicy: {
        max_attempts: plannerResult.retry_policy.max_attempts,
        backoff_ms: plannerResult.retry_policy.backoff_ms,
      },
      transcriptLink: {
        session_id: sessionId,
        turn_index: this.mutableMessages.length + 1,
      },
      memoryUpdateHints: memoryHints,
      audit: buildActionAudit(workspace, delegation),
    }));

    const allActionsAreDirect = actions.every(action => action.selected_tool === 'none');
    if (allActionsAreDirect) {
      const directResponse = synthesizeFinalAnswer({
        intent,
        directMemoryResponse: directMemoryResponse || (intent === 'greeting' ? 'Olá! Como posso te ajudar hoje?' : ''),
        stepResults: actions.map(action => ({
          ok: true,
          summary: directMemoryResponse || '',
          action,
        })),
      });

      const sessionSnapshot = buildSessionSnapshot({
        session,
        summary: summary || '',
        delegates: delegation.delegates,
        provider,
        contract: actions[0] || { version: '1.0.0' },
      });

      appendExecutionAudit(workspace, {
        ...buildRuntimeTrace({
          thought: { intent, complexity },
          plan: {
            strategy: intent === 'memory' ? 'memory_recall' : 'direct_answer',
            delegates: delegation.delegates,
          },
          action: actions[0],
          provider,
          sessionSnapshot,
        }),
        runtime_mode: 'no-tool-local',
        fallback_mode: null,
        delegated_specialists: delegation.specialists,
        critic_review: criticPlanReview,
        semantic_retrieval: semanticMatches,
        step_results: actions.map(action => ({
          ok: true,
          step_id: action.step_id,
          selected_tool: action.selected_tool,
          selected_agent: action.selected_agent,
        })),
      });

      return {
        response: directResponse,
        confidence: 0.92,
        memory: {
          session: sessionSnapshot,
          layers: buildMemorySnapshot({
            layers: memoryLayers,
            strategy: intent,
            provider,
          }),
          runtime_memory: runtimeMemory,
          provider: provider.name,
          delegates: delegation,
          strategy: intent,
          runtime_mode: 'no-tool-local',
        },
      };
    }

    if (runtimeMode.primary.owner === 'python') {
      return {
        response: directMemoryResponse || '',
        execution_request: {
          task_id: taskId,
          run_id: runId,
          mode: runtimeMode.primary.mode,
          fallback_mode: runtimeMode.fallback?.mode || null,
          message,
          intent,
          provider,
          delegation,
          critic_review: criticPlanReview,
          plan_kind: plannerResult.plan_kind || 'linear',
          plan_graph: plannerResult.plan_graph || null,
          parallelism: {
            enabled: Boolean(plannerResult.plan_graph && plannerResult.plan_graph.mode === 'parallel-read'),
            max_parallel_read_steps: runtimeConfig.maxParallelReadSteps,
          },
          semantic_retrieval: semanticMatches,
          loop: {
            max_steps: plannerResult.max_steps,
            stop_on_error: plannerResult.stop_on_error,
          },
          memory_hints: memoryHints,
          service_contract: {
            start_task: { task_id: taskId, run_id: runId, session_id: sessionId },
            get_status: { run_id: runId },
            resume_task: { run_id: runId },
          },
          actions,
        },
        confidence: 0.82,
      };
    }

    const stepResults = [];
    for (const action of actions) {
      if (action.selected_tool === 'none') {
        stepResults.push({
          ok: true,
          summary: directMemoryResponse || 'Resposta direta sem execução de ferramenta.',
          action,
        });
        continue;
      }

      let execution = null;
      const correctionAttempts = [];
      const attempts = Math.max(1, action.retry_policy?.max_attempts || 1);
      for (let attempt = 0; attempt < attempts; attempt += 1) {
        execution = runRustExecutor({
          cwd: workspace,
          action,
          requestedMode: runtimeMode.primary.mode,
        });
        if (execution.ok) break;
        const evaluation = evaluateStepResult({
          action,
          result: execution,
          attempt: attempt + 1,
          maxAttempts: attempts,
        });
        correctionAttempts.push(evaluation);
        if (execution.error_payload?.kind === 'permission_denied' || execution.error?.kind === 'permission_denied') {
          break;
        }
        if (evaluation.decision !== 'retry_same_step') {
          break;
        }
      }

      const summaryText = execution?.ok ? summarizeExecutionResult(execution) : '';
      stepResults.push({
        ...execution,
        summary: summaryText,
        action,
        correction_attempts: correctionAttempts,
      });

      if (execution?.ok) {
        const artifacts = extractArtifacts(execution);
        if (artifacts.length > 0) {
          recordRuntimeArtifacts(workspace, sessionId, artifacts);
        }
      }

      appendRuntimeTranscript(workspace, {
        timestamp: new Date().toISOString(),
        session_id: sessionId,
        message,
        step_id: action.step_id,
        selected_tool: action.selected_tool,
        selected_agent: action.selected_agent,
        ok: execution?.ok || false,
        result: execution?.result_payload || null,
        error: execution?.error_payload || execution?.error || null,
      });

      if (!execution?.ok && plannerResult.stop_on_error) {
        break;
      }
    }

    const finalResponse = synthesizeFinalAnswer({
      intent,
      directMemoryResponse,
      stepResults,
    });
    const synthesizedResponse = synthesizeGroundedResponse({
      intent,
      directMemoryResponse,
      stepResults: stepResults.map(item => ({
        ...item,
        selected_tool: item.action?.selected_tool || item.selected_tool,
      })),
      fallbackResponse: finalResponse,
    });

    const runtimeMemoryPatch = {};
    if (memoryHints.new_name) runtimeMemoryPatch.nome = memoryHints.new_name;
    if (memoryHints.new_work) runtimeMemoryPatch.trabalho = memoryHints.new_work;
    const updatedRuntimeMemory = Object.keys(runtimeMemoryPatch).length > 0
      ? updateSessionRuntimeMemory(workspace, sessionId, runtimeMemoryPatch)
      : runtimeMemory;

    updateWorkingMemory(workspace, sessionId, {
      last_intent: intent,
      last_runtime_mode: runtimeMode.primary.mode,
    });

    const sessionSnapshot = buildSessionSnapshot({
      session,
      summary: summary || '',
      delegates: delegation.delegates,
      provider,
      contract: actions[0] || { version: '1.0.0' },
    });

    const trace = buildRuntimeTrace({
      thought: { intent, complexity },
      plan: {
        strategy: intent === 'analysis' ? 'comparative_analysis' : 'real_execution',
        delegates: delegation.delegates,
      },
      action: actions[0] || {
        selected_tool: 'none',
        permission_requirement: 'none',
      },
      provider,
      sessionSnapshot,
    });
    appendExecutionAudit(workspace, {
      ...trace,
      runtime_mode: runtimeMode.primary.mode,
      fallback_mode: runtimeMode.fallback?.mode || null,
      plan_kind: plannerResult.plan_kind || 'linear',
      plan_graph: plannerResult.plan_graph || null,
      critic_review: criticPlanReview,
      delegated_specialists: delegation.specialists,
        step_results: stepResults.map(item => ({
          ok: item.ok,
          step_id: item.action?.step_id || null,
          selected_tool: item.action?.selected_tool || null,
          selected_agent: item.action?.selected_agent || null,
          correction_attempts: item.correction_attempts || [],
        })),
        task_id: taskId,
        run_id: runId,
        semantic_retrieval: semanticMatches,
      });

    return {
      response: synthesizedResponse,
      confidence: stepResults.some(item => item.ok) || directMemoryResponse ? 0.9 : 0.55,
      memory: {
        session: sessionSnapshot,
        layers: buildMemorySnapshot({
          layers: memoryLayers,
          strategy: intent,
          provider,
        }),
        runtime_memory: updatedRuntimeMemory,
        provider: provider.name,
        delegates: delegation,
        strategy: intent,
        runtime_mode: runtimeMode.primary.mode,
        task_id: taskId,
        run_id: runId,
      },
    };
  }
}

module.exports = {
  QueryEngineAuthority,
};
