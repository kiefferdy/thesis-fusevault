import apiClient from './apiClient';

export const transactionService = {
  // Get asset history
  getAssetHistory: async (assetId, version = null) => {
    try {
      let url = `/transactions/asset/${assetId}`;
      if (version) {
        url += `?version=${version}`;
      }
      const { data } = await apiClient.get(url);
      return data;
    } catch (error) {
      console.error('Error fetching asset history:', error);
      throw error;
    }
  },

  // Get user's transaction summary
  getTransactionSummary: async (walletAddress) => {
    try {
      const { data } = await apiClient.get(`/transactions/summary/${walletAddress}`);
      return data;
    } catch (error) {
      console.error('Error fetching transaction summary:', error);
      throw error;
    }
  },

  // Get recent transactions for a user
  getRecentTransactions: async (walletAddress, limit = 10) => {
    try {
      const { data } = await apiClient.get(`/transactions/recent/${walletAddress}?limit=${limit}`);
      return data;
    } catch (error) {
      console.error('Error fetching recent transactions:', error);
      throw error;
    }
  }
};