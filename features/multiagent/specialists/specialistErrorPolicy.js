const TRUE_VALUES = new Set(['1', 'true', 'yes', 'on']);
const { OMNI_ERROR_CODE, buildPublicError } = require('../../../runtime/tooling/errorTaxonomy');

function truthyEnv(name) {
  return TRUE_VALUES.has(String(process.env[name] || '').trim().toLowerCase());
}

function isPublicDemoMode() {
  return truthyEnv('OMNI_PUBLIC_DEMO_MODE') || truthyEnv('OMINI_PUBLIC_DEMO_MODE');
}

function isInternalDebugEnabled() {
  if (isPublicDemoMode()) {
    return false;
  }
  return truthyEnv('OMNI_DEBUG_INTERNAL_ERRORS') || truthyEnv('OMINI_DEBUG_INTERNAL_ERRORS');
}

function sanitizeText(value, limit) {
  return String(value || '')
    .replace(/[A-Za-z]:\\[^\s"'`]+/g, '[redacted_location]')
    .replace(/\/(?:[A-Za-z0-9._-]+\/){1,}[A-Za-z0-9._-]+/g, '[redacted_location]')
    .replace(/(?:token|secret|key|authorization|bearer)\s*[:=]\s*[^\s,;}]+/gi, '$1=[redacted]')
    .slice(0, limit);
}

function sanitizeErrorForInternalDebug(err) {
  if (!err || typeof err !== 'object') {
    return { message: sanitizeText(err, 200) };
  }

  return {
    name: sanitizeText(err.name || 'Error', 50),
    message: sanitizeText(err.message || '', 200),
    code: sanitizeText(err.code || '', 50),
  };
}

function buildSpecialistFallback({ specialistId, extra = {}, err = null }) {
  const publicError = buildPublicError(OMNI_ERROR_CODE.SPECIALIST_FAILED);
  const payload = {
    invoked: true,
    degraded: true,
    specialist_id: specialistId,
    fallback: true,
    ...publicError,
    ...extra,
  };
  if (isInternalDebugEnabled()) {
    payload.internal_debug = sanitizeErrorForInternalDebug(err);
  }
  return payload;
}

function logSpecialistFallback({ specialistId, err = null }) {
  const event = {
    event: 'specialist_fallback',
    specialist_id: specialistId,
    degraded: true,
    fallback: true,
    ...buildPublicError(OMNI_ERROR_CODE.SPECIALIST_FAILED),
    internal_error_redacted: true,
  };
  if (isInternalDebugEnabled()) {
    event.internal_debug = sanitizeErrorForInternalDebug(err);
  }
  console.error(event);
}

module.exports = {
  buildSpecialistFallback,
  isInternalDebugEnabled,
  isPublicDemoMode,
  logSpecialistFallback,
  sanitizeErrorForInternalDebug,
};
