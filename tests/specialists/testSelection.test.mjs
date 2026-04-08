import assert from 'node:assert/strict';

import { resolveSpecialistsForIntent } from '../../core/agents/specialistRegistry.js';
import { selectVerificationTargets } from '../../features/multiagent/specialists/testSelectionSpecialist.js';

const result = selectVerificationTargets({
  repositoryImpactAnalysis: {
    test_selection_candidates: [
      { path: 'tests/unit/test_a.py' },
      { path: 'tests/integration/test_b.py' },
    ],
  },
  repositoryAnalysis: {
    repository_map: { frameworks: ['react-vite'] },
  },
});

assert.equal(result.invoked, true);
assert.equal(result.specialist_id, 'test_selection_specialist');
assert.deepEqual(result.targeted_tests, ['tests/unit/test_a.py', 'tests/integration/test_b.py']);
assert.ok(result.verification_modes.includes('targeted-tests'));
assert.ok(result.verification_modes.includes('full-tests'));
assert.ok(result.verification_modes.includes('dependency-health'));

const empty = selectVerificationTargets({});
assert.equal(empty.invoked, true);
assert.deepEqual(empty.targeted_tests, []);
assert.equal(empty.rationale.includes('Falling back'), true);

const engineeringSpecialists = resolveSpecialistsForIntent('engineering');
assert.ok(engineeringSpecialists.includes('test_selection_specialist'));

console.log('test selection specialist tests: ok');
