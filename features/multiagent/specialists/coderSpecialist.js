function normalizeWriteRequest({ toolArguments, goal }) {
  return {
    path: toolArguments?.path || 'output.txt',
    content: toolArguments?.content || `Generated content for goal: ${goal || 'unspecified'}.\n`,
  };
}

module.exports = {
  normalizeWriteRequest,
};
