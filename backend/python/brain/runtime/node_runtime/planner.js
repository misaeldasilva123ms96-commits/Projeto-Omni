const { strategyForIntent, normalizeStrategyState } = require('./registry');

function normalizeMessage(message) {
  return String(message || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function extractPerspectiveList(normalized) {
  const known = ['economista', 'ecologista', 'ambientalista', 'agricultor', 'agricultor local'];
  return known.filter(item => normalized.includes(item));
}

function detectAnalogyDomain(normalized) {
  if (normalized.includes('cozinha') || normalized.includes('culin')) {
    return 'cozinha';
  }
  if (normalized.includes('livro de contabilidade')) {
    return 'livro de contabilidade';
  }
  if (normalized.includes('biblioteca')) {
    return 'biblioteca';
  }
  return '';
}

function extractConstraints(message) {
  const normalized = normalizeMessage(message);
  const constraints = {
    paragraphCount: null,
    sentenceCount: null,
    singleSentence: false,
    forbiddenLetters: [],
    rhymeRequired: /rima|rimar/.test(normalized),
    maxSentences: null,
    stepCount: null,
    needsAnalogy: /analogia|metafora|explique como se fosse/.test(normalized),
    analogyDomain: detectAnalogyDomain(normalized),
    needsPerspectives: /perspectiva|ponto de vista/.test(normalized) || extractPerspectiveList(normalized).length > 0,
    perspectiveList: extractPerspectiveList(normalized),
    audience: normalized.includes('nunca ouviu falar') ? 'iniciante' : '',
    brevity: /breve|resuma|curto/.test(normalized),
  };

  const paragraphMatch = normalized.match(/(?:exatamente\s+)?(\d+)\s+paragrafos?/);
  if (paragraphMatch) {
    constraints.paragraphCount = Number(paragraphMatch[1]);
  }

  const exactSentenceMatch = normalized.match(/exatamente\s+(\d+)\s+frases?/);
  if (exactSentenceMatch) {
    constraints.sentenceCount = Number(exactSentenceMatch[1]);
  }

  const maxSentencesMatch = normalized.match(/no maximo\s+(\d+)\s+frases?/);
  if (maxSentencesMatch) {
    constraints.maxSentences = Number(maxSentencesMatch[1]);
  }

  const stepMatch = normalized.match(/(\d+)\s+(?:etapas?|passos?)/);
  if (stepMatch) {
    constraints.stepCount = Number(stepMatch[1]);
  }

  if (/uma unica frase|1 frase/.test(normalized)) {
    constraints.singleSentence = true;
    constraints.sentenceCount = 1;
  }

  const forbiddenLetterMatch = normalized.match(/(?:sem usar a letra|nao pode conter a letra)\s+["“']?([a-z])["”']?/);
  if (forbiddenLetterMatch) {
    constraints.forbiddenLetters.push(forbiddenLetterMatch[1]);
  }

  return constraints;
}

function pickCandidates(thought, baseDecision) {
  switch (thought.taskCategory) {
    case 'memory':
      return ['memory_recall', 'direct_answer'];
    case 'theory_of_mind':
    case 'logic':
      return ['logic_solver', 'direct_answer', 'structured_explanation'];
    case 'analogy':
      return ['creative_reasoning', 'structured_explanation', 'direct_answer'];
    case 'creativity':
    case 'constrained_format':
      return ['creative_reasoning', 'structured_explanation', 'direct_answer'];
    case 'multi_perspective':
      return ['comparative_analysis', 'decision_help', 'structured_explanation'];
    case 'structured_planning':
      return ['specific_plan', 'learning_path', 'business_plan'];
    default:
      return Array.isArray(baseDecision.candidates) && baseDecision.candidates.length > 0
        ? baseDecision.candidates
        : [baseDecision.strategy || 'direct_answer'];
  }
}

function chooseAdaptiveStrategy(candidates, strategyState) {
  const normalizedState = normalizeStrategyState(strategyState);
  const entries = normalizedState.strategies || {};
  const prior = 0.65;
  let winner = candidates[0] || 'direct_answer';
  let bestScore = -Infinity;

  for (const candidate of candidates) {
    const entry = entries[candidate] || {};
    const uses = Number(entry.total_uses || 0);
    const average = Number(entry.average_score || prior);
    const failurePenalty = Number(entry.failure_count || 0) >= 3 ? 0.08 : 0;
    const sampleWeight = Math.min(uses / 8, 1);
    const score = prior * (1 - sampleWeight) + average * sampleWeight - failurePenalty;
    if (score > bestScore) {
      bestScore = score;
      winner = candidate;
    }
  }

  return winner;
}

function strategyForTask(thought, baseDecision) {
  const candidates = pickCandidates(thought, baseDecision);
  const strategy = chooseAdaptiveStrategy(candidates, thought.strategyState);
  return {
    strategy,
    confidence: baseDecision.confidence || 0.84,
    adaptive: {
      ...(baseDecision.adaptive || {}),
      candidates,
      selectedFromTaskCategory: thought.taskCategory,
    },
  };
}

function buildTargetOutput(thought, strategy, constraints) {
  switch (thought.taskCategory) {
    case 'theory_of_mind':
      return 'answer hidden-belief question directly';
    case 'constrained_format':
      return 'produce output obeying explicit structural rules';
    case 'multi_perspective':
      return 'separate analysis by requested viewpoint';
    case 'analogy':
      return 'map technical concept into requested analogy domain';
    case 'structured_planning':
      return 'produce a practical plan with the requested number of steps';
    case 'creativity':
      return constraints.singleSentence ? 'produce one creative sentence' : 'produce a creative answer with strong imagery';
    case 'memory':
      return 'answer from stored user facts directly';
    case 'logic':
      return 'solve the reasoning problem directly';
    default:
      return strategy === 'structured_explanation' ? 'explain the topic directly and clearly' : 'deliver the final answer only';
  }
}

function buildSteps(thought, strategy, constraints) {
  const perspectiveList = constraints.perspectiveList || [];

  switch (thought.taskCategory) {
    case 'theory_of_mind':
      return [
        'identify what each character knows or does not know',
        'infer the first place the protagonist will search',
        'answer directly with a brief justification',
      ];
    case 'logic':
      return [
        'identify the contradiction or key logical condition',
        'resolve the question using explicit facts from the prompt',
        'state the conclusion directly',
      ];
    case 'analogy':
      return [
        `map the concept into the requested analogy domain${constraints.analogyDomain ? ` (${constraints.analogyDomain})` : ''}`,
        'keep the analogy consistent from start to finish',
        'deliver the explanation as the analogy itself, not as commentary about the analogy',
      ];
    case 'multi_perspective':
      return [
        `separate the answer by viewpoint${perspectiveList.length > 0 ? `: ${perspectiveList.join(', ')}` : ''}`,
        'analyze trade-offs for each viewpoint clearly',
        'finish with the requested third solution',
      ];
    case 'constrained_format': {
      const steps = ['extract and obey every explicit format rule', 'produce the requested content directly'];
      if (constraints.paragraphCount) {
        steps.push(`deliver exactly ${constraints.paragraphCount} paragraphs`);
      }
      if (constraints.singleSentence) {
        steps.push('deliver exactly one sentence');
      }
      if (constraints.forbiddenLetters.length > 0) {
        steps.push(`avoid the forbidden letters: ${constraints.forbiddenLetters.join(', ')}`);
      }
      if (constraints.rhymeRequired) {
        steps.push('make the final paragraph rhyme');
      }
      return steps;
    }
    case 'structured_planning': {
      const count = constraints.stepCount || 5;
      return [
        'frame the objective with concrete scope and budget',
        `present exactly ${count} actionable steps`,
        'keep each step practical and execution-oriented',
      ];
    }
    case 'creativity':
      return [
        'accept the imaginative premise instead of correcting it',
        'connect the abstract elements with vivid imagery',
        constraints.singleSentence ? 'answer in one sentence' : 'finish with a memorable creative line',
      ];
    case 'memory':
      return [
        'retrieve the relevant user fact from memory',
        'answer directly and briefly',
      ];
    default:
      if (strategy === 'comparative_analysis') {
        return ['identify the comparison criteria', 'separate strengths and weaknesses clearly', 'end with a grounded recommendation'];
      }
      if (strategy === 'specific_plan' || strategy === 'learning_path') {
        return ['identify the concrete goal', 'organize actionable steps', 'deliver the plan in the requested format'];
      }
      return ['identify the exact user ask', 'answer directly with useful detail', 'respect any explicit constraints'];
  }
}

function decide(thought) {
  const baseDecision = strategyForIntent(thought.intent, thought.availableCapabilities, thought.strategyState);
  const strategyDecision = strategyForTask(thought, baseDecision);
  return {
    ...strategyDecision,
    intent: thought.intent,
    taskCategory: thought.taskCategory,
    promptComplexity: thought.promptComplexity,
  };
}

function plan(thought, decision) {
  const constraints = extractConstraints(thought.message);
  const steps = buildSteps(thought, decision.strategy, constraints);
  const targetOutput = buildTargetOutput(thought, decision.strategy, constraints);

  return {
    intent: thought.intent,
    strategy: decision.strategy,
    steps,
    constraints,
    executionPlan: steps,
    target_output: targetOutput,
    complexity: thought.highComplexity ? 'high' : thought.recentHistory.length > 2 ? 'medium' : 'normal',
    taskCategory: thought.taskCategory,
    adaptive: decision.adaptive || {},
  };
}

module.exports = {
  decide,
  plan,
};


