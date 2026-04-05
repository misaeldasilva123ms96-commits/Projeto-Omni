function getCliPlatformManifest() {
  return {
    source: 'openclaude-main.zip',
    retained_capabilities: [
      'provider bootstrap',
      'profile setup',
      'developer-oriented CLI flows',
      'Codex-compatible UX patterns',
      'advanced planning command patterns',
    ],
    deferred_capabilities: [
      'full upstream terminal UI adoption',
      'remote session product UX',
    ],
  };
}

module.exports = {
  getCliPlatformManifest,
};
