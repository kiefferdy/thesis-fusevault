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
      case 401:
        // For validation endpoints, we don't need to show errors for 401
        // as it's expected behavior when not logged in
        if (error.config.url === '/auth/validate') {
          console.log('Session validation failed - not logged in');
        } else {
          console.error('Authentication error: Not authenticated or session expired');
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        }
        break;
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