import assert from 'node:assert/strict';

import { reviewDependencyImpact } from '../../features/multiagent/specialists/dependencyImpactSpecialist.js';
import { resolveSpecialistsForIntent } from '../../core/agents/specialistRegistry.js';

const result = reviewDependencyImpact({
  repositoryImpactAnalysis: {
    module_change_candidates: [
      { path: 'src/a.ts' },
      { path: 'src/b.ts' },
    ],
    impact_map: { hotspot_files: ['src/a.ts'] },
  },
  repositoryAnalysis: {
    repository_map: { frameworks: ['react-vite', 'python-runtime'] },
  },
});

assert.equal(result.invoked, true);
assert.equal(result.specialist_id, 'dependency_impact_specialist');
assert.deepEqual(result.focus_modules, ['src/a.ts', 'src/b.ts']);
assert.equal(result.recommended_scope, 'targeted-change');
assert.ok(result.dependency_notes[0].includes('multiple frameworks'));

const empty = reviewDependencyImpact({});
assert.equal(empty.invoked, true);
assert.deepEqual(empty.focus_modules, []);
assert.deepEqual(empty.architectural_hotspots, []);
assert.equal(empty.recommended_scope, 'targeted-change');

const engineeringSpecialists = resolveSpecialistsForIntent('engineering');
assert.ok(engineeringSpecialists.includes('dependency_impact_specialist'));

console.log('dependency impact specialist tests: ok');
