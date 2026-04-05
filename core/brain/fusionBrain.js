const { QueryEngineAuthority } = require('./queryEngineAuthority');

const authority = new QueryEngineAuthority();

async function runQueryEngine(payload) {
  return authority.submitMessage(payload);
}

module.exports = {
  runQueryEngine,
};
