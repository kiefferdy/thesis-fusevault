import apiClient from './apiClient';

export const userService = {
  // Register user
  registerUser: async (userData) => {
    try {
      const { data } = await apiClient.post('/users/register', userData);
      return data;
    } catch (error) {
      console.error('Error registering user:', error);
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