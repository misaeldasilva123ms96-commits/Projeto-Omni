import assert from 'node:assert/strict';

import { runQueryEngine } from '../../core/brain/fusionBrain.js';
import { reviewDependencyImpact } from '../../features/multiagent/specialists/dependencyImpactSpecialist.js';
import { selectVerificationTargets } from '../../features/multiagent/specialists/testSelectionSpecialist.js';

process.env.OMINI_FORCE_SPECIALIST_FAILURE = 'dependency_impact_specialist';
const degradedDependency = reviewDependencyImpact({
  repositoryImpactAnalysis: { module_change_candidates: [{ path: 'src/a.ts' }] },
  repositoryAnalysis: { repository_map: { frameworks: ['react-vite'] } },
});
assert.equal(degradedDependency.degraded, true);
assert.equal(degradedDependency.specialist_id, 'dependency_impact_specialist');

process.env.OMINI_FORCE_SPECIALIST_FAILURE = 'test_selection_specialist';
const degradedSelection = selectVerificationTargets({
  repositoryImpactAnalysis: { test_selection_candidates: [{ path: 'tests/a.test.js' }] },
  repositoryAnalysis: { repository_map: { frameworks: ['react-vite'] } },
});
assert.equal(degradedSelection.degraded, true);
assert.equal(degradedSelection.specialist_id, 'test_selection_specialist');

process.env.OMINI_FORCE_SPECIALIST_FAILURE = 'dependency_impact_specialist';
const engineered = await runQueryEngine({
  message: 'analise o repositorio e corrija os testes com seguranca',
  memoryContext: { user: {} },
  history: [],
  summary: '',
  capabilities: [],
  session: { session_id: 'fase3-specialist', runtime_mode: 'python-rust-cargo' },
  cwd: process.cwd(),
});
assert.equal(typeof engineered.execution_request, 'object');
assert.equal(typeof engineered.execution_request.repository_analysis, 'object');
assert.equal(typeof engineered.execution_request.repo_impact_analysis, 'object');

delete process.env.OMINI_FORCE_SPECIALIST_FAILURE;

console.log('specialist hardening tests: ok');
