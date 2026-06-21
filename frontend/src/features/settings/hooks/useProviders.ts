import { useEffect, useState } from 'react';
import type { ProviderRecord, ProviderTestResult } from '../types';
import {
  deleteProvider,
  listProviders,
  saveProvider,
  testProvider,
  updateProvider,
} from '../../../lib/api/settings';
import { redactRuntimeDebugText } from '../../../lib/runtimeDebugSanitizer';

export function useProviders() {
  const [providers, setProviders] = useState<ProviderRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [lastTestResult, setLastTestResult] = useState<ProviderTestResult | null>(null);

  const loadProviders = async () => {
    setLoading(true);
    setError(null);
    try {
      const records = await listProviders();
      setProviders(records);
    } catch (err) {
      const message = err instanceof Error ? redactRuntimeDebugText(err.message) : 'Unable to load providers';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadProviders();
  }, []);

  const createProvider = async (provider: string, apiKey: string) => {
    setSubmitting(true);
    setActionError(null);
    setLastTestResult(null);
    try {
      const record = await saveProvider({ provider, api_key: apiKey });
      setProviders((current) => {
        const filtered = current.filter((item) => item.provider !== provider);
        return [...filtered, record];
      });
    } catch (err) {
      const message = err instanceof Error ? redactRuntimeDebugText(err.message) : 'Unable to save provider';
      setActionError(message);
      throw err;
    } finally {
      setSubmitting(false);
    }
  };

  const editProvider = async (provider: string, apiKey: string) => {
    setSubmitting(true);
    setActionError(null);
    setLastTestResult(null);
    try {
      const record = await updateProvider(provider, { api_key: apiKey });
      setProviders((current) => {
        const filtered = current.filter((item) => item.provider !== provider);
        return [...filtered, record];
      });
    } catch (err) {
      const message = err instanceof Error ? redactRuntimeDebugText(err.message) : 'Unable to update provider';
      setActionError(message);
      throw err;
    } finally {
      setSubmitting(false);
    }
  };

  const removeProvider = async (provider: string) => {
    setSubmitting(true);
    setActionError(null);
    setLastTestResult(null);
    try {
      const record = await deleteProvider(provider);
      setProviders((current) => {
        const filtered = current.filter((item) => item.provider !== provider);
        if (record.configured) {
          return [...filtered, record];
        }
        return filtered;
      });
    } catch (err) {
      const message = err instanceof Error ? redactRuntimeDebugText(err.message) : 'Unable to remove provider';
      setActionError(message);
      throw err;
    } finally {
      setSubmitting(false);
    }
  };

  const runConnectionTest = async (provider: string, apiKey: string) => {
    setTestingProvider(provider);
    setActionError(null);
    setLastTestResult(null);
    try {
      const result = await testProvider(provider, apiKey);
      setLastTestResult(result);
      setProviders((current) => {
        const existingIndex = current.findIndex((item) => item.provider === provider);
        const record: ProviderRecord = {
          provider,
          configured: result.success,
          updated_at: result.success
            ? current[existingIndex]?.updated_at ?? Date.now()
            : existingIndex >= 0
              ? current[existingIndex].updated_at
              : Date.now(),
        };
        const next = [...current];
        if (existingIndex >= 0) {
          next[existingIndex] = record;
        } else {
          next.push(record);
        }
        return next;
      });
    } catch (err) {
      const fallbackResult: ProviderTestResult = {
        provider,
        success: false,
        error: err instanceof Error ? redactRuntimeDebugText(err.message) : 'Unable to test provider',
      };
      setLastTestResult(fallbackResult);
      const message = fallbackResult.error ?? 'Unable to test provider';
      setActionError(message);
    } finally {
      setTestingProvider(null);
    }
  };

  const clearActionError = () => setActionError(null);

  return {
    actionError,
    clearActionError,
    createProvider,
    editProvider,
    lastTestResult,
    loading,
    providers,
    removeProvider,
    runConnectionTest,
    setActionError,
    submitting,
    testingProvider,
  };
}
