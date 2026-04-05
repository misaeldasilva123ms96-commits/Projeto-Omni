function classifyFailure(result) {
  const errorPayload = result?.error_payload || {};
  const kind = String(errorPayload.kind || result?.error?.kind || '');
  if (kind === 'permission_denied') return 'stop_blocked';
  if (kind.includes('parse')) return 'retry_same_step';
  if (kind.includes('path') || /cannot find|nao pode encontrar/i.test(String(errorPayload.message || ''))) {
    return 'revise_plan';
  }
  return 'retry_same_step';
}

function evaluateStepResult({ action, result, attempt, maxAttempts }) {
  if (result?.ok) {
    const payload = result.result_payload || {};
    const hasMeaningfulPayload = Boolean(
      payload.file?.content ||
      payload.content ||
      (Array.isArray(payload.filenames) && payload.filenames.length > 0),
    );
    return {
      decision: hasMeaningfulPayload ? 'continue' : 'stop_blocked',
      reason_code: hasMeaningfulPayload ? 'step_succeeded' : 'empty_success_payload',
      confidence: hasMeaningfulPayload ? 0.92 : 0.35,
    };
  }

  const baseDecision = classifyFailure(result);
  if (baseDecision === 'retry_same_step' && attempt < maxAttempts) {
    return {
      decision: 'retry_same_step',
      reason_code: 'transient_failure',
      confidence: 0.42,
    };
  }

  return {
    decision: baseDecision === 'retry_same_step' ? 'stop_blocked' : baseDecision,
    reason_code: baseDecision,
    confidence: 0.2,
  };
}

module.exports = {
  evaluateStepResult,
};
