'use strict';

const usage = new Map();

function trimmedEnvValue(env, name) {
  const value = env?.[name];
  return typeof value === 'string' ? value.trim() : '';
}

function recordUsage(canonical, legacy, event) {
  const key = `${canonical}\u0000${legacy}`;
  const counters = usage.get(key) || {
    canonical,
    legacy,
    legacy_reads: 0,
    canonical_overrides: 0,
  };
  counters[event] += 1;
  usage.set(key, counters);
}

function readEnvAlias(canonical, legacy, fallback = '', env = process.env) {
  const canonicalValue = trimmedEnvValue(env, canonical);
  const legacyValue = trimmedEnvValue(env, legacy);
  if (canonicalValue) {
    if (legacyValue) recordUsage(canonical, legacy, 'canonical_overrides');
    return canonicalValue;
  }
  if (legacyValue) {
    recordUsage(canonical, legacy, 'legacy_reads');
    return legacyValue;
  }
  return String(fallback ?? '').trim();
}

function readEnvAliasBool(canonical, legacy, fallback = false, env = process.env) {
  const raw = readEnvAlias(canonical, legacy, fallback ? 'true' : 'false', env);
  return ['1', 'true', 'yes', 'on'].includes(raw.toLowerCase());
}

function envAliasUsageSnapshot() {
  const aliases = [...usage.values()]
    .map(row => ({ ...row }))
    .sort((left, right) => `${left.canonical}:${left.legacy}`.localeCompare(`${right.canonical}:${right.legacy}`));
  return {
    schema_version: 1,
    scope: 'process_local',
    legacy_reads: aliases.reduce((total, row) => total + row.legacy_reads, 0),
    canonical_overrides: aliases.reduce((total, row) => total + row.canonical_overrides, 0),
    aliases,
  };
}

function resetEnvAliasUsage() {
  usage.clear();
}

module.exports = {
  envAliasUsageSnapshot,
  readEnvAlias,
  readEnvAliasBool,
  resetEnvAliasUsage,
};
