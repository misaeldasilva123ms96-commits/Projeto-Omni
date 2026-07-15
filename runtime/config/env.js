function trimmedEnvValue(env, name) {
  const value = env?.[name];
  return value == null ? '' : String(value).trim();
}

function readEnv(name, fallback = '', env = process.env) {
  return trimmedEnvValue(env, name) || String(fallback ?? '').trim();
}

function readEnvBool(name, fallback = false, env = process.env) {
  const raw = readEnv(name, fallback ? 'true' : 'false', env);
  return ['1', 'true', 'yes', 'on'].includes(raw.toLowerCase());
}

module.exports = { readEnv, readEnvBool };
