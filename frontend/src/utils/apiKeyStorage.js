/**
 * Utility for managing API key storage in the browser
 * This allows users to test API key authentication without wallet connection
 */

const API_KEY_STORAGE_KEY = 'fusevault_api_key';

/**
 * Store API key in browser storage
 * @param {string} apiKey - The API key to store
 * @param {boolean} persist - Whether to persist across browser sessions (localStorage vs sessionStorage)
 */
export const storeApiKey = (apiKey, persist = false) => {
  if (persist) {
    localStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
    sessionStorage.removeItem(API_KEY_STORAGE_KEY);
  } else {
    sessionStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
    localStorage.removeItem(API_KEY_STORAGE_KEY);
  }
};

/**
 * Retrieve stored API key
 * @returns {string|null} The stored API key or null if not found
 */
export const getStoredApiKey = () => {
  return sessionStorage.getItem(API_KEY_STORAGE_KEY) || localStorage.getItem(API_KEY_STORAGE_KEY);
};

/**
 * Remove stored API key
 */
export const removeApiKey = () => {
  sessionStorage.removeItem(API_KEY_STORAGE_KEY);
  localStorage.removeItem(API_KEY_STORAGE_KEY);
};

/**
 * Check if an API key is stored
 * @returns {boolean} Whether an API key is stored
 */
export const hasStoredApiKey = () => {
  return getStoredApiKey() !== null;
};

/**
 * Utility to test API key authentication
 * This can be used in development console for testing
 */
export const testApiKeyAuth = async (apiKey) => {
  // Store the API key temporarily
  const previousKey = getStoredApiKey();
  storeApiKey(apiKey, false);
  
  try {
    // Make a test request to verify the API key works
    const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/assets/user/test`, {
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      console.log('✅ API key is valid');
      return true;
    } else {
      console.error('❌ API key is invalid or expired');
      return false;
    }
  } catch (error) {
    console.error('❌ Failed to test API key:', error);
    return false;
  } finally {
    // Restore previous key if any
    if (previousKey) {
      storeApiKey(previousKey, localStorage.getItem(API_KEY_STORAGE_KEY) !== null);
    } else {
      removeApiKey();
    }
  }
};

/**
 * Testing helper to use API key authentication instead of wallet
 * This is useful for development and testing
 */
export const useApiKeyAuth = (apiKey, persist = false) => {
  if (!apiKey) {
    console.error('No API key provided');
    return false;
  }
  
  storeApiKey(apiKey, persist);
  console.log(`🔑 API key stored ${persist ? 'persistently' : 'for this session'}`);
  console.log('You can now make API requests using this key');
  
  // Reload the page to apply the new authentication method
  if (confirm('Reload page to apply API key authentication?')) {
    window.location.reload();
  }
  
  return true;
};

/**
 * Clear API key authentication and return to wallet auth
 */
export const clearApiKeyAuth = () => {
  removeApiKey();
  console.log('🔓 API key removed. Returning to wallet authentication.');
  
  // Reload the page to apply the change
  if (confirm('Reload page to return to wallet authentication?')) {
    window.location.reload();
  }
};

// Export helper for browser console
if (typeof window !== 'undefined' && import.meta.env.DEV) {
  window.fuseVaultApiKey = {
    set: useApiKeyAuth,
    clear: clearApiKeyAuth,
    test: testApiKeyAuth,
    get: getStoredApiKey,
    has: hasStoredApiKey
  };
  
  console.log('🔧 FuseVault API Key helpers loaded. Use window.fuseVaultApiKey to manage API keys.');
}