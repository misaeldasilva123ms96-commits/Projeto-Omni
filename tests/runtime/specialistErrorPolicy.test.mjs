import assert from 'node:assert/strict';

import { reviewDependencyImpact } from '../../features/multiagent/specialists/dependencyImpactSpecialist.js';
import {
  buildSpecialistFallback,
  logSpecialistFallback,
  sanitizeErrorForInternalDebug,
} from '../../features/multiagent/specialists/specialistErrorPolicy.js';

const ENV_KEYS = [
  'OMNI_DEBUG_INTERNAL_ERRORS',
  'OMINI_DEBUG_INTERNAL_ERRORS',
  'OMNI_PUBLIC_DEMO_MODE',
  'OMINI_PUBLIC_DEMO_MODE',
  'OMINI_FORCE_SPECIALIST_FAILURE',
];

function clearPolicyEnv() {
  for (const key of ENV_KEYS) {
    delete process.env[key];
  }
}

function captureConsoleError(fn) {
  const original = console.error;
  const logs = [];
  console.error = (...args) => logs.push(args);
  try {
    return { result: fn(), logs };
  } finally {
    console.error = original;
  }
}

function serialized(value) {
  return JSON.stringify(value);
}

function sensitiveError() {
  const error = new Error(
    'forced failure at /home/render/project/.env and C:\\Users\\Misael\\secret.txt token=abc123 SECRET=hidden',
  );
  error.name = 'RuntimeSpecialistError';
  error.code = 'EACCES';
  error.stack = 'STACK /home/render/project/core/brain/queryEngineAuthority.js';
  error.cause = new Error('nested secret');
  error.path = '/home/render/private/secrets.env';
  error.env = { OPENAI_API_KEY: 'sk-test' };
  error.syscall = 'open';
  error.stdout = 'raw stdout';
  error.stderr = 'raw stderr';
  return error;
}

clearPolicyEnv();
process.env.OMINI_FORCE_SPECIALIST_FAILURE = 'dependency_impact_specialist';
const normal = captureConsoleError(() =>
  reviewDependencyImpact({
    repositoryImpactAnalysis: { module_change_candidates: [{ path: 'src/a.ts' }] },
    repositoryAnalysis: { repository_map: { frameworks: ['react-vite'] } },
  }),
);
const normalPayload = serialized({ result: normal.result, logs: normal.logs });
assert.equal(normal.result.degraded, true);
assert.equal(normal.result.fallback, true);
assert.equal(normal.result.error_public_code, 'SPECIALIST_FAILED');
assert.equal(normal.result.error_public_message, 'Specialist execution failed. Using fallback.');
assert.equal(normal.result.internal_error_redacted, true);
assert.equal(normal.result.specialist_id, 'dependency_impact_specialist');
assert.equal(normal.result.internal_debug, undefined);
assert.equal(normalPayload.includes('forced specialist failure'), false);
assert.equal(normalPayload.includes('stack'), false);

clearPolicyEnv();
const unsafe = sensitiveError();
const unsafeLog = captureConsoleError(() =>
  logSpecialistFallback({ specialistId: 'dependency_impact_specialist', err: unsafe }),
);
const unsafeLogPayload = serialized(unsafeLog.logs);
assert.equal(unsafeLogPayload.includes('/home/render/project'), false);
assert.equal(unsafeLogPayload.includes('C:\\\\Users\\\\Misael'), false);
assert.equal(unsafeLogPayload.includes('abc123'), false);
assert.equal(unsafeLogPayload.includes('hidden'), false);
assert.equal(unsafeLogPayload.includes('sk-test'), false);
assert.equal(unsafeLogPayload.includes('raw stdout'), false);
assert.equal(unsafeLogPayload.includes('raw stderr'), false);

clearPolicyEnv();
process.env.OMNI_PUBLIC_DEMO_MODE = 'true';
process.env.OMNI_DEBUG_INTERNAL_ERRORS = 'true';
const demoFallback = buildSpecialistFallback({
  specialistId: 'dependency_impact_specialist',
  err: unsafe,
});
assert.equal(demoFallback.error_public_code, 'SPECIALIST_FAILED');
assert.equal(demoFallback.internal_error_redacted, true);
assert.equal(demoFallback.internal_debug, undefined);

clearPolicyEnv();
process.env.OMNI_DEBUG_INTERNAL_ERRORS = 'true';
const debugFallback = buildSpecialistFallback({
  specialistId: 'dependency_impact_specialist',
  err: unsafe,
});
assert.equal(debugFallback.error_public_code, 'SPECIALIST_FAILED');
assert.equal(debugFallback.internal_error_redacted, true);
assert.equal(typeof debugFallback.internal_debug, 'object');
assert.deepEqual(Object.keys(debugFallback.internal_debug).sort(), ['code', 'message', 'name']);
const debugPayload = serialized(debugFallback.internal_debug);
assert.equal(debugPayload.includes('stack'), false);
assert.equal(debugPayload.includes('cause'), false);
assert.equal(debugPayload.includes('path'), false);
assert.equal(debugPayload.includes('env'), false);
assert.equal(debugPayload.includes('syscall'), false);
assert.equal(debugPayload.includes('/home/render/project'), false);
assert.equal(debugPayload.includes('C:\\\\Users\\\\Misael'), false);
assert.equal(debugPayload.includes('abc123'), false);

const sanitizedPrimitive = sanitizeErrorForInternalDebug('primitive failure /tmp/secret token=abc123');
assert.deepEqual(Object.keys(sanitizedPrimitive), ['message']);
assert.equal(serialized(sanitizedPrimitive).includes('/tmp/secret'), false);
assert.equal(serialized(sanitizedPrimitive).includes('abc123'), false);

clearPolicyEnv();

console.log('specialist error policy tests: ok');
