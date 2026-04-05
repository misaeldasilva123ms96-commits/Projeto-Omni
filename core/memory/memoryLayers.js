function buildMemoryLayers({ memoryContext, history, session }) {
  const user = memoryContext?.user && typeof memoryContext.user === 'object'
    ? memoryContext.user
    : {};

  const shortTerm = Array.isArray(history)
    ? history.slice(-8).map(item => ({
        role: item?.role || 'unknown',
        content: item?.content || '',
      }))
    : [];

  const working = {
    session_id: session?.session_id || 'ephemeral-session',
    summary: session?.summary || '',
    active_constraints: session?.active_constraints || [],
  };

  const longTerm = {
    nome: typeof user.nome === 'string' ? user.nome : '',
    trabalho: typeof user.trabalho === 'string' ? user.trabalho : '',
    preferencias: Array.isArray(user.preferencias) ? user.preferencias : [],
    objetivos: Array.isArray(user.objetivos) ? user.objetivos : [],
  };

  return {
    short_term: shortTerm,
    working,
    long_term: longTerm,
  };
}

module.exports = {
  buildMemoryLayers,
};
