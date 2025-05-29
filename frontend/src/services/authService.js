import apiClient from './apiClient';

export const authService = {
  // Get nonce for authentication
  getNonce: async (walletAddress) => {
    try {
      const { data } = await apiClient.get(`/auth/nonce/${walletAddress}`);
      return data;
    } catch (error) {
      console.error('Error getting nonce:', error);
      throw error;
    }
  },

  // Authenticate with signature
  authenticate: async (walletAddress, signature) => {
    try {
      const { data } = await apiClient.post('/auth/login', {
        wallet_address: walletAddress,
        signature
      });
      return data;
    } catch (error) {
      console.error('Error authenticating:', error);
      throw error;
    }
  },

  // Validate the current session
  validateSession: async () => {
    try {
      const { data } = await apiClient.get('/auth/validate');
      return data;
    } catch (error) {
      console.error('Error validating session:', error);
      throw error;
    }
  },

  // Logout (clear session)
  logout: async () => {
    try {
      const { data } = await apiClient.post('/auth/logout');
      return data;
    } catch (error) {
      console.error('Error during logout:', error);
      throw error;
    }
  }
};