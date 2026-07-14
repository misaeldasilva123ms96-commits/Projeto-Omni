import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const {
  envAliasUsageSnapshot,
  readEnvAlias,
  readEnvAliasBool,
  resetEnvAliasUsage,
} = require('../../runtime/config/envAlias');

resetEnvAliasUsage();

const canonicalEnv = {
  OMNI_RUNTIME_MODE: 'canonical-value',
  OMINI_RUNTIME_MODE: 'private-legacy-sentinel',
};
assert.equal(
  readEnvAlias('OMNI_RUNTIME_MODE', 'OMINI_RUNTIME_MODE', '', canonicalEnv),
  'canonical-value',
);

const legacyEnv = { OMINI_PUBLIC_DEMO_MODE: 'true' };
assert.equal(
  readEnvAliasBool('OMNI_PUBLIC_DEMO_MODE', 'OMINI_PUBLIC_DEMO_MODE', false, legacyEnv),
  true,
);

const canonicalFalseEnv = {
  OMNI_PUBLIC_DEMO_MODE: 'false',
  OMINI_PUBLIC_DEMO_MODE: 'true',
};
assert.equal(
  readEnvAliasBool(
    'OMNI_PUBLIC_DEMO_MODE',
    'OMINI_PUBLIC_DEMO_MODE',
    false,
    canonicalFalseEnv,
  ),
  false,
);

const snapshot = envAliasUsageSnapshot();
assert.equal(snapshot.schema_version, 1);
assert.equal(snapshot.scope, 'process_local');
assert.equal(snapshot.legacy_reads, 1);
assert.equal(snapshot.canonical_overrides, 2);
assert.equal(JSON.stringify(snapshot).includes('private-legacy-sentinel'), false);
assert.deepEqual(
  snapshot.aliases.map(row => Object.keys(row).sort()),
  snapshot.aliases.map(() => [
    'canonical',
    'canonical_overrides',
    'legacy',
    'legacy_reads',
  ]),
);

console.log('environment alias migration tests: ok');
