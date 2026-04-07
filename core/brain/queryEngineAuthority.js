const { randomUUID } = require('crypto');
const path = require('path');

const { loadRuntimeConfig } = require('../../configs/runtimeConfig');
const { buildBrainExecutorAction } = require('../planning/brainExecutorContract');
const { buildExecutionTree } = require('../planning/executionTree');
const { analyzeRepository } = require('../repository/repositoryAnalyzer');
const { analyzeRepositoryImpact } = require('../repository/repoImpactAnalyzer');
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
  recordSemanticEntry,
  recordRuntimeArtifacts,
  updateSessionRuntimeMemory,
  updateWorkingMemory,
  updateRepositoryAnalysis,
} = require('../../storage/memory/runtimeMemoryStore');
const { findLearningMatches, suggestRankedStrategies } = require('../../storage/memory/executionLearningMemory');
const { buildRuntimeTrace } = require('../../observability/tracing/runtimeAudit');
const { buildDelegationPlan } = require('../../features/multiagent/delegationLayer');
const { buildCooperativePlan } = require('../../features/multiagent/cooperativeCoordinator');
const { buildVerificationPlan } = require('../../features/multiagent/verificationPlanner');
const { planTask } = require('../../features/multiagent/specialists/advancedPlannerSpecialist');
const { enrichWithMemory } = require('../../features/multiagent/specialists/memorySpecialist');
const { extractArtifacts, summarizeExecutionResult } = require('../../features/multiagent/specialists/researcherSpecialist');
const { synthesizeFinalAnswer } = require('../../features/multiagent/specialists/reviewerSpecialist');
const { evaluateStepResult } = require('../../features/multiagent/specialists/evaluatorSpecialist');
const { reviewPlan } = require('../../features/multiagent/specialists/criticSpecialist');
const { negotiatePlan } = require('../../features/multiagent/specialists/negotiationSpecialist');
const { simulatePlan } = require('../../features/multiagent/specialists/simulationSpecialist');
const { optimizeStrategySelection } = require('../../features/multiagent/specialists/strategyOptimizerSpecialist');
const { reviewEngineeringPlan } = require('../../features/multiagent/specialists/codeReviewSpecialist');
const { reviewDependencyImpact } = require('../../features/multiagent/specialists/dependencyImpactSpecialist');
const { selectVerificationTargets } = require('../../features/multiagent/specialists/testSelectionSpecialist');
const { synthesizeGroundedResponse } = require('../../features/multiagent/specialists/synthesizerSpecialist');
const { fuseResults } = require('../../features/multiagent/specialists/resultFusionSpecialist');
const { normalizeWriteRequest } = require('../../features/multiagent/specialists/coderSpecialist');
const { getFusionSourceMap } = require('./fusedSources');
const { buildRustRuntimeManifest } = require('../../runtime/execution/rustRuntimeManifest');
const { getKairosManifest } = require('../../features/kairos/manifest');
const { getCodexIntegrationStatus } = require('../../platform/integrations/codexIntegration');
const { getCliPlatformManifest } = require('../../platform/cli/manifest');
const { buildPolicyDecision, describeTool } = require('../../runtime/tooling/toolGovernance');

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
  if (/(repositorio|repositório|codigo|código|teste|testes|debug|refator|implemente|corrija|fix)/.test(text)) return 'engineering';
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
    const repositoryAnalysis = analyzeRepository(workspace, { maxFiles: 1500 });
    const repositoryImpactAnalysis = analyzeRepositoryImpact({ repositoryAnalysis, message });
    updateRepositoryAnalysis(workspace, sessionId, repositoryAnalysis);
    const semanticMatches = await findSemanticMatches(workspace, sessionId, message, 3);
    const learningMatches = findLearningMatches(workspace, { message, limit: 3 });
    const strategySuggestions = suggestRankedStrategies(workspace, { message, limit: 3 });
    const verificationPlan = buildVerificationPlan({
      repositoryImpactAnalysis,
      runtimeConfig,
    });
    const memoryHints = enrichWithMemory({
      message,
      memoryLayers,
      runtimeMemory,
      semanticMatches,
      repositoryAnalysis,
    });
    const retrievalContext = memoryHints.retrieval_context || {};
    const mergedMemory = buildMergedMemory(memoryLayers, runtimeMemory);
    const directMemoryResponse = directResponseFromMemory(message, {
      ...mergedMemory,
      ...memoryHints,
    });

    const delegation = buildDelegationPlan({
      intent: intent === 'analysis'
        ? 'analysis'
        : intent === 'memory'
          ? 'memory'
          : intent === 'engineering'
            ? 'engineering'
            : 'execution',
      complexity,
    });
    const plannerResult = planTask({
      message,
      sessionId,
      retrievalContext: {
        ...retrievalContext,
        learning_matches: learningMatches,
        strategy_suggestions: strategySuggestions,
      },
      runtimeConfig,
      repositoryAnalysis,
      repositoryImpactAnalysis,
      verificationPlan,
    });
    const criticPlanReview = reviewPlan({
      steps: plannerResult.steps,
      planGraph: plannerResult.plan_graph,
      complexity,
      intent,
      runtimeConfig,
    });
    const cooperativePlan = buildCooperativePlan({
      message,
      plannerResult,
      delegation,
      strategySuggestions,
    });
    const strategyOptimization = optimizeStrategySelection({
      message,
      rankedStrategies: strategySuggestions,
      plannerResult,
    });
    const dependencyImpactReview = reviewDependencyImpact({
      repositoryImpactAnalysis,
      repositoryAnalysis,
    });
    const verificationSelection = selectVerificationTargets({
      repositoryImpactAnalysis,
      repositoryAnalysis,
    });
    const engineeringReview = reviewEngineeringPlan({
      repositoryAnalysis,
      plannerResult,
      message,
    });

    const simulatedPolicy = plannerResult.steps.map(step => ({
      step_id: step.step_id,
      policy_decision: buildPolicyDecision({
        toolName: step.selected_tool,
        approvalState: step.selected_tool === 'write_file' ? 'pending' : 'approved',
        parallelSafe: Boolean(step.parallel_safe),
        specialist: step.selected_agent,
      }),
    }));
    const simulationSummary = simulatePlan({
      message,
      steps: plannerResult.steps,
      criticReview: criticPlanReview,
      policySummary: simulatedPolicy,
      strategySuggestions,
      runtimeConfig,
    });
    const negotiationSummary = negotiatePlan({
      message,
      plannerResult,
      criticReview: criticPlanReview,
      simulationSummary,
      strategySuggestions,
      maxDepth: runtimeConfig.negotiationMaxDepth,
    });
    const executionTree = buildExecutionTree({
      steps: plannerResult.steps,
      planHierarchy: plannerResult.plan_hierarchy,
      branchPlan: plannerResult.branch_plan,
      milestonePlan: plannerResult.milestone_plan,
    });

    const actions = plannerResult.steps.map((step, index) => {
      const policyDecision = buildPolicyDecision({
        toolName: step.selected_tool,
        approvalState: step.selected_tool === 'write_file' ? 'pending' : 'approved',
        parallelSafe: Boolean(step.parallel_safe),
        specialist: step.selected_agent,
      });
      return buildBrainExecutorAction({
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
        goal_id: step.goal_id || null,
        parent_goal_id: step.parent_goal_id || null,
        branch_id: step.branch_id || null,
        shared_goal_id: step.shared_goal_id || cooperativePlan.shared_goal_id,
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
      audit: {
        ...buildActionAudit(workspace, delegation),
        tool_governance: describeTool(step.selected_tool),
      },
      policyDecision,
    });
    });

    const actionsWithPolicy = actions;

    const allActionsAreDirect = actionsWithPolicy.every(action => action.selected_tool === 'none');
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
        contract: actionsWithPolicy[0] || { version: '1.0.0' },
      });

      appendExecutionAudit(workspace, {
        ...buildRuntimeTrace({
          thought: { intent, complexity },
          plan: {
            strategy: intent === 'memory' ? 'memory_recall' : 'direct_answer',
            delegates: delegation.delegates,
          },
          action: actionsWithPolicy[0],
          provider,
          sessionSnapshot,
        }),
        runtime_mode: 'no-tool-local',
        fallback_mode: null,
        delegated_specialists: delegation.specialists,
        critic_review: criticPlanReview,
        semantic_retrieval: semanticMatches,
        step_results: actionsWithPolicy.map(action => ({
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
          negotiation_summary: negotiationSummary,
          plan_kind: plannerResult.plan_kind || 'linear',
          plan_graph: plannerResult.plan_graph || null,
          execution_tree: executionTree,
          repository_analysis: repositoryAnalysis,
          repo_impact_analysis: repositoryImpactAnalysis,
          branch_plan: plannerResult.branch_plan || null,
          simulation_summary: simulationSummary,
          cooperative_plan: cooperativePlan,
          strategy_suggestions: strategySuggestions,
          strategy_optimization: strategyOptimization,
          dependency_impact_review: dependencyImpactReview,
          verification_plan: verificationPlan,
          verification_selection: verificationSelection,
          engineering_review: engineeringReview,
          engineering_workflow: plannerResult.engineering_workflow || null,
          milestone_plan: plannerResult.milestone_plan || null,
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
            inspect_repository_analysis: { run_id: runId },
            inspect_milestones: { run_id: runId },
            inspect_patch_sets: { run_id: runId },
            inspect_verification: { run_id: runId },
            inspect_pr_summary: { run_id: runId },
            inspect_patch_history: { run_id: runId },
            inspect_debug_iterations: { run_id: runId },
            inspect_workspace_state: { run_id: runId },
            inspect_branches: { run_id: runId },
            inspect_contributions: { run_id: runId },
            inspect_simulation: { run_id: runId },
            inspect_run_intelligence: { run_id: runId },
          },
          actions: actionsWithPolicy,
          plan_hierarchy: plannerResult.plan_hierarchy || null,
          learning_guidance: learningMatches,
          ranked_strategy_memory: strategySuggestions,
          execution_mode: plannerResult.execution_mode || 'flat',
          milestone_plan: plannerResult.milestone_plan || null,
          policy_summary: actionsWithPolicy.map(action => ({
            step_id: action.step_id,
            policy_decision: action.policy_decision,
          })),
        },
        confidence: 0.82,
      };
    }

    const stepResults = [];
    for (const action of actionsWithPolicy) {
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
        goal_id: action.execution_context?.goal_id || null,
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
    const fusion = fuseResults(
      stepResults.map(item => ({
        ...item,
        action: item.action,
      })),
      cooperativePlan,
      null,
    );

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
      contract: actionsWithPolicy[0] || { version: '1.0.0' },
    });

    const trace = buildRuntimeTrace({
      thought: { intent, complexity },
      plan: {
        strategy: intent === 'analysis' ? 'comparative_analysis' : 'real_execution',
        delegates: delegation.delegates,
      },
      action: actionsWithPolicy[0] || {
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
      plan_hierarchy: plannerResult.plan_hierarchy || null,
      critic_review: criticPlanReview,
      negotiation_summary: negotiationSummary,
      cooperative_plan: cooperativePlan,
      execution_tree: executionTree,
      repository_analysis: repositoryAnalysis,
      repo_impact_analysis: repositoryImpactAnalysis,
      branch_plan: plannerResult.branch_plan || null,
      simulation_summary: simulationSummary,
      strategy_suggestions: strategySuggestions,
      strategy_optimization: strategyOptimization,
      dependency_impact_review: dependencyImpactReview,
      verification_plan: verificationPlan,
      verification_selection: verificationSelection,
      engineering_review: engineeringReview,
      engineering_workflow: plannerResult.engineering_workflow || null,
      milestone_plan: plannerResult.milestone_plan || null,
      result_fusion: fusion,
      delegated_specialists: delegation.specialists,
        learning_guidance: learningMatches,
        step_results: stepResults.map(item => ({
          ok: item.ok,
          step_id: item.action?.step_id || null,
          selected_tool: item.action?.selected_tool || null,
          selected_agent: item.action?.selected_agent || null,
          correction_attempts: item.correction_attempts || [],
          goal_id: item.action?.execution_context?.goal_id || null,
          policy_decision: item.action?.policy_decision || null,
        })),
        task_id: taskId,
        run_id: runId,
        semantic_retrieval: semanticMatches,
      });

    if (stepResults.some(item => item.ok)) {
      recordSemanticEntry(workspace, sessionId, {
        path: `run://${runId}`,
        preview: synthesizedResponse,
        source: 'phase6-run-summary',
      });
    }

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
