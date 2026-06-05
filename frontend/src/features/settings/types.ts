export type ProviderStatus = 'connected' | 'invalid_credentials' | 'connection_failed' | 'not_configured';

export type ProviderRecord = {
  provider: string;
  configured: boolean;
  updated_at: number | null;
};

export type ProviderTestResult = {
  provider: string;
  success: boolean;
  error?: string;
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
