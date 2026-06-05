import type { ProviderRecord, ProviderTestResult } from '../types';

import { API_BASE_URL, fetchWithTimeout, getSupabaseAuthHeaders } from './client';

export async function listProviders(): Promise<ProviderRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/settings/providers`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'same-origin',
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.error ?? 'Unable to load providers');
  }

  const providers: ProviderRecord[] = Array.isArray(payload?.providers)
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

  const response = await fetch(`${API_BASE_URL}/api/v1/settings/providers`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'same-origin',
    body: JSON.stringify({
      provider: String(payload.provider).trim().toLowerCase(),
      api_key: String(payload.api_key),
    }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.error ?? 'Unable to save provider');
  }

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

  const response = await fetch(
    `${API_BASE_URL}/api/v1/settings/providers/${encodeURIComponent(provider.trim().toLowerCase())}`,
    {
      method: 'PUT',
      headers: buildHeaders(),
      credentials: 'same-origin',
      body: JSON.stringify({
        api_key: String(payload.api_key),
      }),
    },
  );

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.error ?? 'Unable to update provider');
  }

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

  const response = await fetch(
    `${API_BASE_URL}/api/v1/settings/providers/${encodeURIComponent(provider.trim().toLowerCase())}`,
    {
      method: 'DELETE',
      headers: buildHeaders(),
      credentials: 'same-origin',
    },
  );

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.error ?? 'Unable to remove provider');
  }

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

  const response = await fetch(
    `${API_BASE_URL}/api/v1/settings/providers/${encodeURIComponent(provider.trim().toLowerCase())}/test`,
    {
      method: 'POST',
      headers: buildHeaders(),
      credentials: 'same-origin',
      body: JSON.stringify({ api_key: String(apiKey) }),
    },
  );

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.error ?? 'Unable to test provider');
  }

  return {
    provider: String(data.provider ?? provider).trim().toLowerCase(),
    success: Boolean(data.success),
    error: typeof data.error === 'string' && data.error ? data.error : undefined,
  };
}
