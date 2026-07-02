const TOKEN_COMPRESSION_MODES = Object.freeze(['off', 'lite', 'standard', 'aggressive']);
const SAFE_TOKEN_COMPRESSION_PAYLOAD_TYPES = Object.freeze([
  'long_log',
  'test_output',
  'large_diff',
  'repeated_messages',
  'text_history',
]);

const SECRET_PATTERNS = [
  /\bBearer\s+[A-Za-z0-9._=-]{8,}/i,
  /\b(?:sk|ghp|xoxb)-[A-Za-z0-9._=-]{8,}/i,
  /\b(?:OPENAI|ANTHROPIC|GROQ|GEMINI|DEEPSEEK|OPENROUTER|SUPABASE)_[A-Z0-9_]*KEY\s*=/i,
  /\b(?:api[_-]?key|apikey|x-api-key|authorization|cookie|set-cookie)\b\s*[:=]/i,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/i,
];

function normalizeTokenCompressionMode(value) {
  const mode = String(value || '').trim().toLowerCase();
  return TOKEN_COMPRESSION_MODES.includes(mode) ? mode : 'off';
}

function hasSecretIndicator(value) {
  const text = String(value || '');
  return SECRET_PATTERNS.some(pattern => pattern.test(text));
}

function redactSafeCompressionText(value) {
  const text = String(value || '');
  let redacted = text
    .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, '[redacted-email]')
    .replace(/\bC:\\Users\\[^\\\r\n]+/gi, 'C:\\Users\\[redacted]')
    .replace(/\/home\/[^/\s]+\/[^\r\n\s]*/gi, '/home/[redacted]')
    .replace(/\b(?:stack trace|traceback)\b[^\r\n]*/gi, '[redacted-stack]');

  return {
    text: redacted,
    redactionApplied: redacted !== text,
  };
}

function normalizePolicyResult(value) {
  return String(value || '').trim().toLowerCase() === 'allow' ? 'allow' : 'block';
}

function makeTruth({
  mode,
  inputSize,
  outputSize = 0,
  strategyUsed = 'none',
  redactionApplied = false,
  skippedReason = '',
  failClosedReason = '',
}) {
  const normalizedInput = Math.max(0, Number(inputSize) || 0);
  const normalizedOutput = Math.max(0, Number(outputSize) || 0);
  const ratio = normalizedInput > 0
    ? Number((normalizedOutput / normalizedInput).toFixed(4))
    : 1;

  return {
    compression_mode: normalizeTokenCompressionMode(mode),
    input_size: normalizedInput,
    output_size: normalizedOutput,
    compression_ratio: ratio,
    strategy_used: String(strategyUsed || 'none').trim().toLowerCase().replace(/[^a-z0-9_.:-]+/g, '_').slice(0, 64),
    redaction_applied: Boolean(redactionApplied),
    skipped_reason: String(skippedReason || '').trim().toLowerCase().replace(/[^a-z0-9_.:-]+/g, '_').slice(0, 96),
    fail_closed_reason: String(failClosedReason || '').trim().toLowerCase().replace(/[^a-z0-9_.:-]+/g, '_').slice(0, 96),
  };
}

function isSafePayloadType(payloadType) {
  return SAFE_TOKEN_COMPRESSION_PAYLOAD_TYPES.includes(String(payloadType || '').trim().toLowerCase());
}

function collapseBlankLines(text) {
  return text.replace(/\n{3,}/g, '\n\n').trim();
}

function collapseConsecutiveDuplicateLines(text, maxRepeats = 1) {
  const lines = text.split(/\r?\n/);
  const output = [];
  let previous = '';
  let repeats = 0;

  for (const line of lines) {
    if (line === previous) {
      repeats += 1;
      if (repeats <= maxRepeats) {
        output.push(line);
      }
      continue;
    }

    previous = line;
    repeats = 0;
    output.push(line);
  }

  return output.join('\n');
}

function headTail(text, headLines, tailLines) {
  const lines = text.split(/\r?\n/);
  if (lines.length <= headLines + tailLines + 1) {
    return text;
  }

  const omitted = lines.length - headLines - tailLines;
  return [
    ...lines.slice(0, headLines),
    `[omitted ${omitted} lines after governed compression]`,
    ...lines.slice(-tailLines),
  ].join('\n');
}

function applyCompressionStrategy(text, mode) {
  const normalized = collapseBlankLines(text);
  if (mode === 'lite') {
    return {
      text: collapseConsecutiveDuplicateLines(normalized, 2),
      strategy: 'lite_blankline_dedupe',
    };
  }

  if (mode === 'standard') {
    return {
      text: headTail(collapseConsecutiveDuplicateLines(normalized, 1), 24, 16),
      strategy: 'standard_head_tail_dedupe',
    };
  }

  if (mode === 'aggressive') {
    return {
      text: headTail(collapseConsecutiveDuplicateLines(normalized, 0), 12, 8),
      strategy: 'aggressive_head_tail_dedupe',
    };
  }

  return {
    text,
    strategy: 'none',
  };
}

function compressTokenPayload({
  content,
  payloadType,
  mode = 'off',
  policyResult = 'allow',
  preserveAuditability = true,
  redactionRequired = true,
} = {}) {
  const compressionMode = normalizeTokenCompressionMode(mode);
  const input = String(content || '');
  const inputSize = input.length;

  if (compressionMode === 'off') {
    return {
      ok: true,
      compressedText: input,
      runtimeTruth: makeTruth({
        mode: compressionMode,
        inputSize,
        outputSize: inputSize,
        skippedReason: 'mode_off',
      }),
    };
  }

  if (normalizePolicyResult(policyResult) !== 'allow') {
    return failClosed(compressionMode, inputSize, 'policy_blocked');
  }

  if (!isSafePayloadType(payloadType)) {
    return failClosed(compressionMode, inputSize, 'unsafe_payload_type');
  }

  if (!preserveAuditability) {
    return failClosed(compressionMode, inputSize, 'auditability_risk');
  }

  if (hasSecretIndicator(input)) {
    return failClosed(compressionMode, inputSize, 'secret_indicator_detected');
  }

  let redacted = { text: input, redactionApplied: false };
  if (redactionRequired) {
    try {
      redacted = redactSafeCompressionText(input);
    } catch {
      return failClosed(compressionMode, inputSize, 'redaction_failed');
    }
  }

  const compressed = applyCompressionStrategy(redacted.text, compressionMode);
  const outputSize = compressed.text.length;

  return {
    ok: true,
    compressedText: compressed.text,
    runtimeTruth: makeTruth({
      mode: compressionMode,
      inputSize,
      outputSize,
      strategyUsed: compressed.strategy,
      redactionApplied: redacted.redactionApplied,
    }),
  };
}

function failClosed(mode, inputSize, reason) {
  return {
    ok: false,
    compressedText: '',
    runtimeTruth: makeTruth({
      mode,
      inputSize,
      outputSize: 0,
      skippedReason: reason,
      failClosedReason: reason,
    }),
  };
}

module.exports = {
  TOKEN_COMPRESSION_MODES,
  SAFE_TOKEN_COMPRESSION_PAYLOAD_TYPES,
  compressTokenPayload,
  hasSecretIndicator,
  normalizeTokenCompressionMode,
};
