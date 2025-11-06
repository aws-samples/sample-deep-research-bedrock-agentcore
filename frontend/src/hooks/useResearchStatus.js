/**
 * Custom hook for polling research status
 * Automatically polls every N seconds until research is complete
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../services/api';
import { getPollingInterval } from '../config/app.config';

export function useResearchStatus(sessionId, options = {}) {
  const {
    pollingInterval = getPollingInterval(),
    autoStart = true,
    onComplete = null,
    onError = null
  } = options;

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const isMountedRef = useRef(true);

  // Use refs for callbacks to avoid recreating fetchStatus on every render
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onComplete, onError]);

  const fetchStatus = useCallback(async () => {
    try {
      console.log(`[useResearchStatus] Fetching status for session: ${sessionId}`);
      const data = await api.getResearchStatus(sessionId);

      // Only update state if component is still mounted
      if (!isMountedRef.current) {
        console.log(`[useResearchStatus] Component unmounted, skipping update`);
        return null;
      }

      console.log(`[useResearchStatus] Received status:`, data?.status);
      setStatus(data);
      setError(null);
      setLoading(false);

      // Check if research is complete or failed - STOP polling
      if (data.status === 'completed' || data.status === 'failed') {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }

        if (data.status === 'completed' && onCompleteRef.current) {
          onCompleteRef.current(data);
        } else if (data.status === 'failed' && onErrorRef.current) {
          onErrorRef.current(new Error(data.error || 'Research failed'));
        }
      }

      return data;
    } catch (err) {
      console.error('Failed to fetch research status:', err);

      if (!isMountedRef.current) return null;

      setError(err.message);
      setLoading(false);

      // Stop polling on error
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }

      if (onErrorRef.current) {
        onErrorRef.current(err);
      }

      return null;
    }
  }, [sessionId]);

  // Initial fetch on mount
  useEffect(() => {
    if (!sessionId || !autoStart) return;
    fetchStatus();
  }, [sessionId, autoStart, fetchStatus]);

  // Start/stop polling based on status
  useEffect(() => {
    if (!sessionId || !status) return;

    console.log(`[useResearchStatus] Status changed to: ${status.status}`);

    // Only poll if status is in progress
    if (status.status === 'processing' || status.status === 'pending') {
      if (!intervalRef.current) {
        console.log(`[useResearchStatus] Starting polling (interval: ${pollingInterval}ms)`);
        intervalRef.current = setInterval(fetchStatus, pollingInterval);
      }
    } else {
      // Stop polling for terminal states (completed, failed)
      if (intervalRef.current) {
        console.log(`[useResearchStatus] Stopping polling (terminal state: ${status.status})`);
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    // Cleanup on unmount or status change
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, status?.status, pollingInterval, fetchStatus]);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      console.log(`[useResearchStatus] Component unmounting, cleaning up`);
      isMountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    if (!intervalRef.current) {
      fetchStatus();
      intervalRef.current = setInterval(fetchStatus, pollingInterval);
    }
  }, [fetchStatus, pollingInterval]);

  return {
    status,
    loading,
    error,
    refetch: fetchStatus,
    stopPolling,
    startPolling
  };
}
