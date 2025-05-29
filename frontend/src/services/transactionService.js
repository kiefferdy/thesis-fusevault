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
      console.log('Recent transactions fetched:', data);
      return data;
    } catch (error) {
      console.error('Error fetching recent transactions:', error);
      // Return empty data structure on error to prevent crashes
      return { transactions: [] };
    }
  },
  
  // Get all transactions for a user
  getAllTransactions: async (walletAddress) => {
    try {
      const { data } = await apiClient.get(`/transactions/all/${walletAddress}`);
      console.log('All transactions fetched:', data);
      return data;
    } catch (error) {
      console.error('Error fetching all transactions:', error);
      // Return empty data structure on error to prevent crashes
      return { transactions: [] };
    }
  }
};