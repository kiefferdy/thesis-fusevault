// Utility functions for debugging

/**
 * Logs current cookies for debugging purposes
 */
export const logCookies = () => {
  console.log('Current cookies:', document.cookie);
  return document.cookie.split(';').reduce((cookies, cookie) => {
    const [name, value] = cookie.trim().split('=');
    cookies[name] = value;
    return cookies;
  }, {});
};

/**
 * Tests CORS configuration by making a simple request
 * @param {string} url - The URL to test
 * @returns {Promise<object>} - Result object
 */
export const testCORS = async (url) => {
  console.log(`Testing CORS for ${url}...`);
  try {
    const start = performance.now();
    const response = await fetch(url, {
      method: 'OPTIONS',
      credentials: 'include',
    });
    const end = performance.now();
    
    const result = {
      success: response.ok,
      status: response.status,
      corsHeaders: {
        'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
        'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials'),
        'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
        'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
      },
      timeMs: Math.round(end - start),
    };
    
    console.log('CORS test result:', result);
    return result;
  } catch (error) {
    console.error('CORS test error:', error);
    return {
      success: false,
      error: error.message,
    };
  }
};

/**
 * Adds a browser console utility to test backend connection
 * Can be called from browser console: window.testBackend()
 */
export const setupDebugHelpers = () => {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  
  window.testBackend = async () => {
    console.log('Testing backend connection...');
    try {
      const response = await fetch(`${API_URL}/auth/nonce/0x0000000000000000000000000000000000000000`, {
        credentials: 'include',
      });
      console.log('Response status:', response.status);
      const data = await response.json();
      console.log('Response data:', data);
      return { success: true, status: response.status, data };
    } catch (error) {
      console.error('Connection error:', error);
      return { success: false, error: error.message };
    }
  };
  
  window.logCookies = logCookies;
  window.testCORS = () => testCORS(`${API_URL}/auth/nonce/0x0000000000000000000000000000000000000000`);
  
  console.log('Debug helpers installed. Use window.testBackend(), window.logCookies(), or window.testCORS() to debug.');
};