const { getKairosContract } = require('./contract');

function getKairosManifest(cwd) {
  const contract = getKairosContract();
  return {
    enabled: contract.enabled,
    role: 'optional-future-layer',
    contract,
    source_candidates: [
      `${cwd}\\vendor\\openclaude-upstream\\src\\main.tsx`,
      `${cwd}\\vendor\\openclaude-upstream\\src\\bootstrap\\state.ts`,
    ],
    responsibilities: [
      'scheduled follow-ups',
      'proactive assistance',
      'persistent workflows',
      'notifications',
    ],
    integration_policy: 'Do not enable until brain/executor/provider boundaries are stable.',
  };
}

module.exports = {
  getKairosManifest,
};
