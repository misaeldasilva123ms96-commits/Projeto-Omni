const { buildHierarchicalPlan, buildPlanGraph } = require('../../../core/planning/planGraph');

function detectConstraints(message) {
  const text = String(message || '').toLowerCase();
  return {
    wantsRead: text.includes('leia') || text.includes('abra') || text.includes('readme'),
    wantsReadAgain: text.includes('leia de novo') || text.includes('leia novamente') || text.includes('abra novamente'),
    wantsList: text.includes('liste') || text.includes('arquivos') || text.includes('pastas'),
    wantsSearch: text.includes('busque') || text.includes('procure') || text.includes('grep'),
    wantsWrite: text.includes('crie o arquivo') || text.includes('salve') || text.includes('escreva no arquivo'),
    wantsAnalysis: text.includes('analise') || text.includes('resuma'),
    wantsGraphPlan: text.includes('depois') || text.includes('entao') || text.includes('então') || text.includes('analise'),
    wantsParallelRead: (text.includes('liste') || text.includes('arquivos')) && (text.includes('busque') || text.includes('procure') || text.includes('grep')),
    wantsMultiStep: /\b(e|depois|entao|então)\b/.test(text),
    wantsHierarchy:
      /(depois|entao|então|por partes|primeiro|segundo)/.test(text)
      && ((text.includes('analise') && text.includes('leia')) || (text.includes('liste') && text.includes('analise'))),
    wantsCooperation:
      /(compare|comparar|analise|revis|critique|critica)/.test(text)
      || ((text.includes('liste') || text.includes('busque')) && text.includes('leia')),
    wantsBranching:
      /(compare|comparar|duas abordagens|duas estrategias|duas estratégias)/.test(text)
      || ((text.includes('liste') || text.includes('busque')) && text.includes('compare')),
    wantsSimulation:
      /(arriscado|seguro|simule|antes de executar|compare)/.test(text)
      || text.includes('escreva'),
  };
}

function detectReferencedFile(message, retrievalContext) {
  const explicitMatch = String(message).match(/([A-Za-z0-9_./\\-]+\.(md|txt|json|js|ts|py|rs))/i);
  if (explicitMatch) {
    return explicitMatch[1];
  }
  if (retrievalContext?.recalled_artifact_path) return retrievalContext.recalled_artifact_path;
  if (retrievalContext?.semantic_match?.path) return retrievalContext.semantic_match.path;
  if (retrievalContext?.last_artifact?.path) return retrievalContext.last_artifact.path;
  return '';
}

function buildStep(sessionId, suffix, tool, agent, toolArguments, goal, extra = {}) {
  return {
    step_id: `${sessionId}:step:${suffix}`,
    selected_tool: tool,
    selected_agent: agent,
    tool_arguments: toolArguments,
    goal,
    shared_goal_id: extra.shared_goal_id || 'shared-goal:root',
    ...extra,
  };
}

function assignHierarchy(constraints, steps) {
  if (!constraints.wantsHierarchy) return steps;
  return steps.map(step => {
    if (['glob_search', 'grep_search'].includes(step.selected_tool)) {
      return { ...step, goal_id: 'goal:inspect', parent_goal_id: 'goal:root' };
    }
    if (step.selected_tool === 'read_file' && constraints.wantsAnalysis) {
      return { ...step, goal_id: 'goal:synthesize', parent_goal_id: 'goal:root' };
    }
    if (step.selected_tool === 'read_file') {
      return { ...step, goal_id: 'goal:read', parent_goal_id: 'goal:root' };
    }
    return { ...step, goal_id: 'goal:root', parent_goal_id: null };
  });
}

function buildPlanMetadata(constraints, steps, runtimeConfig) {
  const planKind = constraints.wantsHierarchy
    ? 'hierarchical'
    : constraints.wantsParallelRead || constraints.wantsGraphPlan || steps.some(step => Array.isArray(step.depends_on) && step.depends_on.length > 0)
      ? 'graph'
      : 'linear';
  const rootGoal = {
    goal_id: 'goal:root',
    label: 'Resolver a solicitacao principal',
    state: 'pending',
  };
  const subgoals = planKind === 'hierarchical'
    ? [
        {
          goal_id: 'goal:inspect',
          parent_goal_id: rootGoal.goal_id,
          label: 'Inspecionar o workspace e reunir evidencias',
          state: 'pending',
          step_ids: steps.filter(step => ['glob_search', 'grep_search'].includes(step.selected_tool)).map(step => step.step_id),
        },
        {
          goal_id: 'goal:read',
          parent_goal_id: rootGoal.goal_id,
          label: 'Ler os artefatos principais',
          state: 'pending',
          step_ids: steps.filter(step => step.selected_tool === 'read_file').map(step => step.step_id),
        },
        {
          goal_id: 'goal:synthesize',
          parent_goal_id: rootGoal.goal_id,
          label: 'Sintetizar os achados por subobjetivo',
          state: 'pending',
          step_ids: steps.filter(step => step.selected_tool === 'read_file').map(step => step.step_id),
        },
      ].filter(item => item.step_ids.length > 0)
    : [];

  return {
    plan_kind: planKind,
    plan_graph: planKind === 'linear'
      ? null
      : buildPlanGraph({
          steps,
          mode: planKind === 'hierarchical'
            ? (constraints.wantsParallelRead ? 'hierarchical-parallel-read' : 'hierarchical')
            : (constraints.wantsParallelRead ? 'parallel-read' : 'dependency-aware'),
        }),
    plan_hierarchy: planKind === 'hierarchical'
      ? buildHierarchicalPlan({
          rootGoal,
          subgoals,
        })
      : null,
    max_steps: Math.min(runtimeConfig.maxSteps || 6, steps.length || 1),
  };
}

function planTask({ message, sessionId, retrievalContext = {}, runtimeConfig = {} }) {
  const constraints = detectConstraints(message);
  const steps = [];
  const referencedFile = detectReferencedFile(message, retrievalContext);
  const learningMatches = Array.isArray(retrievalContext.learning_matches) ? retrievalContext.learning_matches : [];
  const prefersInspectionFirst = learningMatches.some(item => String(item.lesson || '').toLowerCase().includes('read-only') || String(item.lesson || '').toLowerCase().includes('parallel'));

  if (constraints.wantsList || (prefersInspectionFirst && (constraints.wantsRead || constraints.wantsAnalysis))) {
    steps.push(buildStep(
      sessionId,
      'list',
      'glob_search',
      'researcher_agent',
      { pattern: '**/*', path: '.' },
      'inspect workspace structure',
      { parallel_safe: constraints.wantsParallelRead, branch_id: constraints.wantsBranching ? 'branch:list-first' : null },
    ));
  }

  if (constraints.wantsSearch) {
    const patternMatch = String(message).match(/["'`](.+?)["'`]/);
    steps.push(buildStep(
      sessionId,
      'grep',
      'grep_search',
      'researcher_agent',
      {
        pattern: patternMatch ? patternMatch[1] : 'TODO',
        path: '.',
        output_mode: 'content',
        head_limit: 20,
      },
      'search workspace content for requested pattern',
      { parallel_safe: constraints.wantsParallelRead, branch_id: constraints.wantsBranching ? 'branch:search-first' : null },
    ));
  }

  if (constraints.wantsRead || constraints.wantsReadAgain || constraints.wantsAnalysis) {
    const chosenPath = referencedFile || 'README.md';
    steps.push(buildStep(
      sessionId,
      constraints.wantsAnalysis ? 'analysis-read' : 'read',
      'read_file',
      'researcher_agent',
      {
        path: chosenPath,
        limit: constraints.wantsAnalysis ? 160 : 120,
      },
      constraints.wantsAnalysis ? 'retrieve source material for hierarchical analysis' : 'retrieve target file contents',
      {
        depends_on: constraints.wantsList ? [`${sessionId}:step:list`] : [],
        branch_id: constraints.wantsBranching ? 'branch:list-first' : null,
      },
    ));
  }

  if (constraints.wantsBranching && constraints.wantsAnalysis) {
    steps.push(buildStep(
      sessionId,
      'analysis-branch-read',
      'read_file',
      'researcher_agent',
      {
        path: referencedFile || 'package.json',
        limit: 80,
      },
      'compare alternate analysis branch before synthesis',
      {
        branch_id: 'branch:search-first',
        depends_on: constraints.wantsSearch ? [`${sessionId}:step:grep`] : [],
      },
    ));
  }

  if (constraints.wantsWrite) {
    const targetPath = referencedFile || 'output.txt';
    steps.push(buildStep(
      sessionId,
      'write',
      'write_file',
      'coder_agent',
      {
        path: targetPath,
        content: 'Generated by Omini Phase 6 runtime.\n',
      },
      'persist requested content',
    ));
  }

  if (steps.length === 0) {
    steps.push(buildStep(
      sessionId,
      'respond',
      'none',
      'master_orchestrator',
      {},
      'respond directly without tool use',
    ));
  }

  const hierarchicalSteps = assignHierarchy(constraints, steps);
  const planMetadata = buildPlanMetadata(constraints, hierarchicalSteps, runtimeConfig);
  const branchPlan = constraints.wantsBranching
    ? {
        enabled: true,
        strategy: 'bounded-safe-read-branches',
        max_branches: 2,
        merge_mode: 'winner-selection',
        branches: [
          {
            branch_id: 'branch:list-first',
            label: 'Inspecionar estrutura antes da leitura',
            safe: true,
            step_ids: hierarchicalSteps.filter(step => step.branch_id === 'branch:list-first' || !step.branch_id).map(step => step.step_id),
          },
          {
            branch_id: 'branch:search-first',
            label: 'Buscar evidências antes da leitura comparativa',
            safe: true,
            step_ids: hierarchicalSteps.filter(step => step.branch_id === 'branch:search-first').map(step => step.step_id),
          },
        ].filter(branch => branch.step_ids.length > 0),
      }
    : null;
  return {
    constraints,
    ...planMetadata,
    branch_plan: branchPlan,
    stop_on_error: true,
    retry_policy: {
      max_attempts: runtimeConfig.maxRetries || 1,
      backoff_ms: 0,
    },
    requires_review: hierarchicalSteps.some(step => step.selected_tool !== 'none'),
    steps: hierarchicalSteps,
  };
}

module.exports = {
  planTask,
};

