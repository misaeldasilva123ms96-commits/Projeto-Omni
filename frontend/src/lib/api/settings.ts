import type { ProviderRecord, ProviderTestResult } from '../../features/settings/types';
import { redactRuntimeDebugText } from '../runtimeDebugSanitizer';
import { requestJsonWithAuth } from './client';

type ProviderPayload = Partial<ProviderRecord> & { providers?: ProviderRecord[]; error?: string; success?: boolean };

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

  return providers.filter((item) => {
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


  return {
    provider: String(data.provider ?? payload.provider).trim().toLowerCase(),
    configured: Boolean(data.configured),
    updated_at: typeof data.updated_at === 'number' ? data.updated_at : null,
  };
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


  return {
    provider: String(data.provider ?? provider).trim().toLowerCase(),
    configured: Boolean(data.configured),
    updated_at: typeof data.updated_at === 'number' ? data.updated_at : null,
  };
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


  return {
    provider: String(data.provider ?? provider).trim().toLowerCase(),
    configured: Boolean(data.configured),
    updated_at: typeof data.updated_at === 'number' ? data.updated_at : null,
  };
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
  };
}
