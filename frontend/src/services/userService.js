import apiClient from './apiClient';

export const userService = {
  // Register user
  registerUser: async (userData) => {
    try {
      const { data } = await apiClient.post('/users/register', userData);
      return data;
    } catch (error) {
      console.error('Error registering user:', error);
      if (error.response && error.response.status === 409) {
        // If the user already exists, just return the user
        console.log('User already exists, fetching profile instead');
        return userService.getUser(userData.wallet_address);
      }
      throw error;
    }
  },

  // Get user by wallet address
  getUser: async (walletAddress) => {
    try {
      const { data } = await apiClient.get(`/users/${walletAddress}`);
      return data;
    } catch (error) {
      console.error('Error fetching user:', error);
      // If the user doesn't exist, return a default object
      // with enough information for the UI to work with
      if (error.response && error.response.status === 404) {
        console.log('User not found, returning default profile');
        return {
          status: "error",
          message: "User not found",
          user: {
            id: null,
            wallet_address: walletAddress,
            email: null,
            role: "user"
          }
        };
      }
      throw error;
    }
  },

  // Update user
  updateUser: async (walletAddress, updateData) => {
    try {
      const { data } = await apiClient.put(`/users/${walletAddress}`, updateData);
      return data;
    } catch (error) {
      console.error('Error updating user:', error);
      throw error;
    }
  }
};