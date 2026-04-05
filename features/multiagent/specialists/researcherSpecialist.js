function summarizeExecutionResult(result) {
  if (!result?.ok) {
    return `Falha na execução: ${result?.error_payload?.message || result?.error?.message || 'erro desconhecido'}`;
  }

  const payload = result.result_payload || {};

  if (payload.file?.content) {
    return payload.file.content;
  }

  if (Array.isArray(payload.filenames)) {
    return payload.filenames.slice(0, 20).join('\n');
  }

  if (payload.content) {
    return payload.content;
  }

  return JSON.stringify(payload);
}

function extractArtifacts(result) {
  const payload = result?.result_payload || {};
  const artifacts = [];

  if (payload.file?.filePath) {
    artifacts.push({
      kind: 'file',
      path: payload.file.filePath,
      preview: typeof payload.file.content === 'string' ? payload.file.content.slice(0, 200) : '',
    });
  }

  if (Array.isArray(payload.filenames)) {
    for (const item of payload.filenames.slice(0, 10)) {
      artifacts.push({
        kind: 'workspace-entry',
        path: item,
        preview: '',
      });
    }
  }

  return artifacts;
}

module.exports = {
  extractArtifacts,
  summarizeExecutionResult,
};
