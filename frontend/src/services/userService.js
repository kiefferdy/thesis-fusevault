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

  // Get user by username
  getUserByUsername: async (username) => {
    try {
      const { data } = await apiClient.get(`/users/username/${username}`);
      return data;
    } catch (error) {
      console.error('Error fetching user by username:', error);
      throw error;
    }
  },

  // Check if username is available
  checkUsernameAvailability: async (username) => {
    try {
      const { data } = await apiClient.get(`/users/username/${username}/availability`);
      return data;
    } catch (error) {
      console.error('Error checking username availability:', error);
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
  },

  // Update username specifically (may require additional validation)
  updateUsername: async (walletAddress, newUsername) => {
    try {
      const { data } = await apiClient.put(`/users/${walletAddress}`, {
        username: newUsername
      });
      return data;
    } catch (error) {
      console.error('Error updating username:', error);
      throw error;
    }
  },

  // Onboard user (for authenticated users completing their profile)
  onboardUser: async (userData) => {
    try {
      const { data } = await apiClient.post('/users/onboard', userData);
      return data;
    } catch (error) {
      console.error('Error onboarding user:', error);
      throw error;
    }
  }
};