const path = require('path');

function getFusionSourceMap(cwd) {
  return {
    main_brain: {
      source_repo: 'src.zip',
      authority: 'typescript-query-engine',
      upstream_entry: path.resolve(cwd, 'vendor', 'src-brain-upstream', 'QueryEngine.ts'),
      adoption_status: 'keep-and-adapt',
    },
    execution_runtime: {
      source_repo: 'claw-code-main.zip',
      authority: 'rust-runtime',
      upstream_entry: path.resolve(cwd, 'vendor', 'claw-runtime-upstream', 'conversation.rs'),
      adoption_status: 'keep-and-wrap',
    },
    provider_layer: {
      source_repo: 'openclaude-main.zip',
      authority: 'provider-routing-and-cli',
      upstream_entry: path.resolve(cwd, 'vendor', 'openclaude-upstream', 'scripts', 'provider-bootstrap.ts'),
      adoption_status: 'keep-and-wrap',
    },
    kairos: {
      source_repo: 'openclaude-main.zip',
      authority: 'optional-future-layer',
      upstream_entry: path.resolve(cwd, 'vendor', 'openclaude-upstream', 'src', 'main.tsx'),
      adoption_status: 'defer',
    },
  };
}

module.exports = {
  getFusionSourceMap,
};
