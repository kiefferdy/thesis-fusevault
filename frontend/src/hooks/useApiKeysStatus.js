import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import apiKeyService from '../services/apiKeyService';

/**
 * Hook to manage API keys feature status
 * @param {Object} options - Configuration options
 * @param {number} options.pollingInterval - Polling interval in ms (0 = disabled)
 * @param {boolean} options.refetchOnFocus - Whether to refetch when window regains focus
 * @returns {Object} API keys status and control functions
 */
export const useApiKeysStatus = (options = {}) => {
  const { 
    pollingInterval = 30000, // Poll every 30 seconds by default
    refetchOnFocus = true 
  } = options;
  
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);
  const [previousStatus, setPreviousStatus] = useState(null);

  // Detect status changes and show notifications
  useEffect(() => {
    if (previousStatus !== null && status !== null) {
      const wasEnabled = previousStatus.enabled;
      const isNowEnabled = status.enabled;
      
      if (wasEnabled !== isNowEnabled) {
        if (isNowEnabled) {
          toast.success('🔑 API Keys feature has been enabled!');
        } else {
          toast.error('🚫 API Keys feature has been disabled');
        }
      }
    }
    setPreviousStatus(status);
  }, [status, previousStatus]);

  const checkStatus = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      setError(null);
      
      const apiKeysStatus = await apiKeyService.getStatus();
      setStatus(apiKeysStatus);
      setLastChecked(new Date());
      
      console.log('API Keys status updated:', apiKeysStatus);
    } catch (err) {
      console.error('Error checking API keys status:', err);
      setError(err);
      // Assume disabled if status check fails
      setStatus({ enabled: false });
      setLastChecked(new Date());
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  // Initial status check
  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  // Polling effect
  useEffect(() => {
    if (pollingInterval > 0) {
      const interval = setInterval(() => {
        checkStatus(true); // Silent refresh
      }, pollingInterval);

      return () => clearInterval(interval);
    }
  }, [checkStatus, pollingInterval]);

  // Window focus effect
  useEffect(() => {
    if (refetchOnFocus) {
      const handleFocus = () => {
        // Only refetch if it's been more than 5 seconds since last check
        if (!lastChecked || Date.now() - lastChecked.getTime() > 5000) {
          checkStatus(true);
        }
      };

      window.addEventListener('focus', handleFocus);
      return () => window.removeEventListener('focus', handleFocus);
    }
  }, [refetchOnFocus, checkStatus, lastChecked]);

  const refresh = useCallback(() => {
    return checkStatus(false);
  }, [checkStatus]);

  return {
    status,
    loading,
    error,
    lastChecked,
    isEnabled: status?.enabled === true,
    isDisabled: status?.enabled === false,
    refresh
  };
};

export default useApiKeysStatus;
