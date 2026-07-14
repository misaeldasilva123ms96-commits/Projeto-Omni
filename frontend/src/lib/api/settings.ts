import type { ProviderRecord, ProviderTestResult } from '../../features/settings/types';
import { redactRuntimeDebugText } from '../runtimeDebugSanitizer';
import { requestJsonWithAuth } from './client';

type ProviderPayload = Partial<ProviderRecord> & {
  providers?: ProviderRecord[];
  error?: string;
  success?: boolean;
  cached?: boolean;
};

const healthCacheStatuses = new Set(['missing', 'fresh', 'stale']);
const circuitStates = new Set(['closed', 'open', 'half_open']);

function optionalBoolean(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null;
}

function optionalNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function normalizeProviderRecord(value: Partial<ProviderRecord>, fallbackProvider = ''): ProviderRecord {
  const cacheStatus = String(value.cache_status ?? 'missing');
  const circuitState = String(value.circuit_state ?? 'closed');
  return {
    provider: String(value.provider ?? fallbackProvider).trim().toLowerCase(),
    configured: Boolean(value.configured),
    executable: typeof value.executable === 'boolean' ? value.executable : undefined,
    available: typeof value.available === 'boolean' ? value.available : undefined,
    reachable: optionalBoolean(value.reachable),
    healthy: optionalBoolean(value.healthy),
    health_valid: Boolean(value.health_valid),
    last_checked_at: optionalNumber(value.last_checked_at),
    valid_until: optionalNumber(value.valid_until),
    latency_ms: optionalNumber(value.latency_ms),
    cache_status: healthCacheStatuses.has(cacheStatus)
      ? cacheStatus as ProviderRecord['cache_status']
      : 'missing',
    circuit_state: circuitStates.has(circuitState)
      ? circuitState as ProviderRecord['circuit_state']
      : 'closed',
    consecutive_failures: Math.max(0, optionalNumber(value.consecutive_failures) ?? 0),
    next_probe_at: optionalNumber(value.next_probe_at),
    updated_at: optionalNumber(value.updated_at),
  };
}

async function settingsRequest<T = ProviderPayload>(path: string, init?: RequestInit): Promise<T> {
  try {
    return await requestJsonWithAuth<T>(path, init);
  } catch (error) {
    throw new Error(redactRuntimeDebugText(error instanceof Error ? error.message : 'Settings request failed'));
  }
}

export async function listProviders(): Promise<ProviderRecord[]> {
  const payload = await settingsRequest<ProviderPayload | ProviderRecord[]>('/api/v1/settings/providers');

  const providers: ProviderRecord[] = !Array.isArray(payload) && Array.isArray(payload.providers)
    ? (payload.providers as ProviderRecord[])
    : Array.isArray(payload)
      ? (payload as ProviderRecord[])
      : [];

  return providers.map((item) => normalizeProviderRecord(item)).filter((item) => {
    const provider = String(item.provider ?? '').trim().toLowerCase();
    return !!provider;
  });
}

export async function saveProvider(payload: { provider: string; api_key: string }): Promise<ProviderRecord> {
  if (!payload?.provider || !payload?.api_key) {
    throw new Error('Provider and api_key are required');
  }

  const data = await settingsRequest('/api/v1/settings/providers', {
    method: 'POST',
    body: JSON.stringify({
      provider: String(payload.provider).trim().toLowerCase(),
      api_key: String(payload.api_key),
    }),
  });


  return normalizeProviderRecord(data, payload.provider);
}

export async function updateProvider(provider: string, payload: { api_key: string }): Promise<ProviderRecord> {
  if (!provider || !payload?.api_key) {
    throw new Error('Provider and api_key are required');
  }

  const data = await settingsRequest(
    `/api/v1/settings/providers/${encodeURIComponent(provider.trim().toLowerCase())}`,
    {
      method: 'PUT',
      body: JSON.stringify({ api_key: String(payload.api_key) }),
    },
  );


  return normalizeProviderRecord(data, provider);
}

export async function deleteProvider(provider: string): Promise<ProviderRecord> {
  if (!provider) {
    throw new Error('Provider is required');
  }

  const data = await settingsRequest(
    `/api/v1/settings/providers/${encodeURIComponent(provider.trim().toLowerCase())}`,
    {
      method: 'DELETE',
    },
  );


  return normalizeProviderRecord(data, provider);
}

export async function testProvider(provider: string, apiKey: string): Promise<ProviderTestResult> {
  if (!provider || !apiKey) {
    throw new Error('Provider and api_key are required');
  }

  const data = await settingsRequest(
    `/api/v1/settings/providers/${encodeURIComponent(provider.trim().toLowerCase())}/test`,
    {
      method: 'POST',
      body: JSON.stringify({ api_key: String(apiKey) }),
    },
  );


  return {
    provider: String(data.provider ?? provider).trim().toLowerCase(),
    success: Boolean(data.success),
    error: typeof data.error === 'string' && data.error ? data.error : undefined,
    cached: Boolean(data.cached),
    reachable: optionalBoolean(data.reachable),
    healthy: optionalBoolean(data.healthy),
    health_valid: Boolean(data.health_valid),
    last_checked_at: optionalNumber(data.last_checked_at),
    valid_until: optionalNumber(data.valid_until),
    latency_ms: optionalNumber(data.latency_ms),
    cache_status: healthCacheStatuses.has(String(data.cache_status))
      ? String(data.cache_status) as ProviderTestResult['cache_status']
      : 'missing',
    circuit_state: circuitStates.has(String(data.circuit_state))
      ? String(data.circuit_state) as ProviderTestResult['circuit_state']
      : 'closed',
    consecutive_failures: Math.max(0, optionalNumber(data.consecutive_failures) ?? 0),
    next_probe_at: optionalNumber(data.next_probe_at),
  };
}
