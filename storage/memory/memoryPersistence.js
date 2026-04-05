function buildMemorySnapshot({ layers, strategy, provider }) {
  return {
    strategy,
    provider: provider?.name || 'local-heuristic',
    short_term_messages: Array.isArray(layers?.short_term) ? layers.short_term.length : 0,
    working_session: layers?.working || {},
    long_term_keys: Object.keys(layers?.long_term || {}).filter(key => {
      const value = layers.long_term[key];
      return Array.isArray(value) ? value.length > 0 : Boolean(value);
    }),
    layer_summary: {
      session_memory: Array.isArray(layers?.short_term) ? layers.short_term.length : 0,
      working_memory_keys: Object.keys(layers?.working || {}).length,
      persistent_memory_keys: Object.keys(layers?.long_term || {}).length,
    },
  };
}

module.exports = {
  buildMemorySnapshot,
};
