const fs = require('fs');
const path = require('path');

function ensureAuditDir(cwd) {
  const auditDir = path.join(cwd, '.logs', 'fusion-runtime');
  fs.mkdirSync(auditDir, { recursive: true });
  return auditDir;
}

function appendExecutionAudit(cwd, entry) {
  const auditDir = ensureAuditDir(cwd);
  const logPath = path.join(auditDir, 'execution-audit.jsonl');
  fs.appendFileSync(logPath, `${JSON.stringify(entry)}\n`, 'utf8');
  return logPath;
}

function appendRuntimeTranscript(cwd, entry) {
  const auditDir = ensureAuditDir(cwd);
  const logPath = path.join(auditDir, 'runtime-transcript.jsonl');
  fs.appendFileSync(logPath, `${JSON.stringify(entry)}\n`, 'utf8');
  return logPath;
}

module.exports = {
  appendExecutionAudit,
  appendRuntimeTranscript,
};
