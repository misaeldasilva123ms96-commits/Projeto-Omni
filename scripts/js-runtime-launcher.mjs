import { spawnSync } from 'node:child_process';
import path from 'node:path';

function candidateExists(command) {
  if (!command) {
    return false;
  }
  const probe = spawnSync(command, ['--version'], {
    stdio: 'ignore',
    shell: false,
  });
  return probe.status === 0;
}

export function detectJsRuntime(env = process.env) {
  const explicit = String(env.OMINI_JS_RUNTIME_BIN || '').trim();
  if (explicit) {
    return {
      runtimeName: path.basename(explicit).toLowerCase().includes('bun') ? 'bun' : 'node',
      executable: explicit,
      source: 'explicit_env',
      fallbackUsed: !path.basename(explicit).toLowerCase().includes('bun'),
    };
  }

  const bunCandidate = String(env.BUN_BIN || 'bun').trim();
  if (candidateExists(bunCandidate)) {
    return {
      runtimeName: 'bun',
      executable: bunCandidate,
      source: 'bun_detected',
      fallbackUsed: false,
    };
  }

  const nodeCandidate = String(env.NODE_BIN || 'node').trim();
  return {
    runtimeName: 'node',
    executable: nodeCandidate,
    source: 'node_fallback',
    fallbackUsed: true,
  };
}

export function runWithSelectedRuntime(argv = process.argv.slice(2), env = process.env) {
  const selection = detectJsRuntime(env);
  if (argv.length === 1 && argv[0] === '--print-selection') {
    process.stdout.write(JSON.stringify(selection));
    return 0;
  }

  if (argv.length === 0) {
    process.stderr.write('Missing target script for js-runtime-launcher.\n');
    return 1;
  }

  const [script, ...rest] = argv;
  const child = spawnSync(selection.executable, [script, ...rest], {
    stdio: 'inherit',
    env: {
      ...env,
      OMINI_JS_RUNTIME: selection.runtimeName,
      OMINI_JS_RUNTIME_SOURCE: selection.source,
      OMINI_JS_RUNTIME_BIN: selection.executable,
    },
    shell: false,
  });

  if (typeof child.status === 'number') {
    return child.status;
  }
  return 1;
}

if (import.meta.url === `file://${process.argv[1]?.replace(/\\/g, '/')}` || process.argv[1]?.endsWith('js-runtime-launcher.mjs')) {
  process.exit(runWithSelectedRuntime());
}
