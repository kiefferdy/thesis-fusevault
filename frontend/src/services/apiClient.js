import axios from 'axios';

// Get the API URL from environment variable or fallback to localhost
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create an axios instance
const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true, // Important for session cookie handling
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  // Extended timeout for longer backend operations (blockchain/IPFS)
  timeout: 300000, // 5 minutes to allow for blockchain and IPFS operations
  // Retry on failure - helpful for intermittent network issues
  retries: 3,
  retryDelay: 2000
});

// Add request interceptor to include API key if available
apiClient.interceptors.request.use(
  (config) => {
    // Check if there's an API key in sessionStorage or localStorage
    const apiKey = sessionStorage.getItem('fusevault_api_key') || localStorage.getItem('fusevault_api_key');
    
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response, 
  async (error) => {
    // Connection or network errors
    if (!error.response) {
      console.error('Network Error: The backend server appears to be offline or unreachable.');
      if (error.code === 'ECONNABORTED') {
        console.error('Request timeout. The server did not respond in time.');
      }
      return Promise.reject(new Error('Backend server is not responding. Please ensure it is running.'));
    }
    
    // Handle specific status codes
    switch (error.response.status) {
      case 401: {
        // Skip event for validation endpoints and nonce endpoints
        const isValidationEndpoint = error.config.url === '/auth/validate';
        const isNonceEndpoint = error.config.url?.includes('/auth/nonce/');
        
        if (isValidationEndpoint) {
          console.log('Session validation failed - not logged in');
        } else if (isNonceEndpoint) {
          console.log('Nonce request failed - expected during initial auth');
        } else {
          console.error('Authentication error: Session expired or invalid');
          window.dispatchEvent(new CustomEvent('auth:unauthorized', {
            detail: { 
              url: error.config.url,
              message: 'Your session has expired. Please sign in again.'
            }
          }));
        }
        break;
      }
      case 403:
        console.error('Authorization error: Insufficient permissions');
        break;
      case 404:
        console.error(`API endpoint not found: ${error.config.url}`);
        return Promise.reject(new Error(`API endpoint not found: ${error.config.url}. Make sure the backend server is running.`));
      case 500:
        console.error('Server error:', error.response.data);
        break;
      default:
        console.error(`Error ${error.response.status}:`, error.response.data);
        break;
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;