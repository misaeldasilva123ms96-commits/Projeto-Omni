export type ProviderStatus = 'connected' | 'invalid_credentials' | 'connection_failed' | 'not_configured';

export type ProviderRecord = {
  provider: string;
  configured: boolean;
  executable?: boolean;
  available?: boolean;
  reachable?: boolean | null;
  healthy?: boolean | null;
  health_valid?: boolean;
  last_checked_at?: number | null;
  valid_until?: number | null;
  latency_ms?: number | null;
  cache_status?: 'missing' | 'fresh' | 'stale';
  circuit_state?: 'closed' | 'open' | 'half_open';
  consecutive_failures?: number;
  next_probe_at?: number | null;
  updated_at: number | null;
};

export type ProviderTestResult = {
  provider: string;
  success: boolean;
  error?: string;
  cached?: boolean;
  reachable?: boolean | null;
  healthy?: boolean | null;
  health_valid?: boolean;
  last_checked_at?: number | null;
  valid_until?: number | null;
  latency_ms?: number | null;
  cache_status?: 'missing' | 'fresh' | 'stale';
  circuit_state?: 'closed' | 'open' | 'half_open';
  consecutive_failures?: number;
  next_probe_at?: number | null;
};

export type SaveProviderPayload = {
  provider: string;
  api_key: string;
};

export type UpdateProviderPayload = {
  api_key: string;
};

export type TestProviderPayload = {
  api_key: string;
};
