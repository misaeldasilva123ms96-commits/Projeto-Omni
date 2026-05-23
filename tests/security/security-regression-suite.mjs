import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
function frontendVitestEntrypoint() {
  return path.join(projectRoot, 'frontend', 'node_modules', 'vitest', 'vitest.mjs');
}

const commands = [
  {
    label: 'phase-1a shell hardening',
    command: 'python',
    args: ['-m', 'pytest', '-q', 'tests/runtime/test_shell_policy_hardening.py'],
  },
  {
    label: 'phase-1b specialist logging hardening',
    command: 'node',
    args: ['tests/runtime/specialistErrorPolicy.test.mjs'],
  },
  {
    label: 'phase-1c backend public payload sanitization',
    command: 'python',
    args: ['-m', 'pytest', '-q', 'tests/runtime/observability/test_public_runtime_payload.py'],
  },
  {
    label: 'phase-1d frontend debug sanitization',
    command: 'node',
    args: [
      frontendVitestEntrypoint(),
      'run',
      'src/lib/runtimeDebugSanitizer.test.ts',
      'src/components/status/RuntimeDebugSection.test.tsx',
      'src/components/status/RuntimePanel.test.tsx',
      '--reporter=dot',
    ],
    cwd: path.join(projectRoot, 'frontend'),
  },
  {
    label: 'phase-1e learning/log redaction',
    command: 'python',
    args: ['-m', 'pytest', '-q', 'tests/runtime/learning/test_learning_redaction.py'],
  },
  {
    label: 'phase-2 runtime truth contract',
    command: 'python',
    args: ['-m', 'pytest', '-q', 'tests/runtime/observability/test_runtime_truth_contract.py'],
  },
  {
    label: 'phase-2 runtime truth js contract',
    command: 'node',
    args: ['tests/runtime/runtimeTruthContract.test.mjs'],
  },
  {
    label: 'phase-3 tool governance enforcement python',
    command: 'python',
    args: ['-m', 'pytest', '-q', 'tests/runtime/test_tool_governance_enforcement.py'],
  },
  {
    label: 'phase-3 tool governance enforcement js',
    command: 'node',
    args: ['tests/runtime/toolGovernanceEnforcement.test.mjs'],
  },
  {
    label: 'phase-4 secrets config hardening js',
    command: 'node',
    args: ['tests/runtime/secretsConfigHardening.test.mjs'],
  },
  {
    label: 'phase-4 secrets config hardening python',
    command: 'python',
    args: ['-m', 'pytest', '-q', 'tests/runtime/test_secrets_config_hardening.py', 'tests/config/test_secrets_manager.py'],
  },
  {
    label: 'phase-5 api validation and rate limit rust chat routes',
    command: 'cargo',
    args: ['test', 'chat_route_', '--', '--nocapture'],
    cwd: path.join(projectRoot, 'backend', 'rust'),
  },
  {
    label: 'phase-5 api validation env aliases',
    command: 'cargo',
    args: ['test', 'chat_security_env_aliases_work', '--', '--nocapture'],
    cwd: path.join(projectRoot, 'backend', 'rust'),
  },
  {
    label: 'phase-6 public demo container static validation',
    command: 'node',
    args: ['tests/runtime/containerPublicDemo.validation.mjs'],
  },
  {
    label: 'phase-8 error taxonomy python',
    command: 'python',
    args: ['-m', 'pytest', '-q', 'tests/runtime/test_error_taxonomy.py'],
  },
  {
    label: 'phase-8 error taxonomy js',
    command: 'node',
    args: ['tests/runtime/errorTaxonomy.test.mjs'],
  },
];

if (!fs.existsSync(frontendVitestEntrypoint())) {
  console.error(`missing frontend vitest entrypoint: ${frontendVitestEntrypoint()}`);
  process.exit(1);
}

for (const item of commands) {
  const cwd = item.cwd || projectRoot;
  console.log(`\n[security-regression] ${item.label}`);
  const result = spawnSync(item.command, item.args, {
    cwd,
    stdio: 'inherit',
    shell: false,
    env: {
      ...process.env,
      OMNI_PUBLIC_DEMO_MODE: '',
      OMINI_PUBLIC_DEMO_MODE: '',
      OMNI_ALLOW_SHELL_TOOLS: '',
      OMINI_ALLOW_SHELL_TOOLS: '',
      ALLOW_SHELL: '',
      OMNI_DEBUG_INTERNAL_ERRORS: '',
      OMINI_DEBUG_INTERNAL_ERRORS: '',
    },
  });
  if (result.status !== 0) {
    console.error(`[security-regression] failed: ${item.label}`);
    process.exit(result.status || 1);
  }
}

console.log('\nsecurity regression suite: ok');
