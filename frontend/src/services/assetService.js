import apiClient from './apiClient';

export const assetService = {
  // Upload metadata
  uploadMetadata: async (data) => {
    const formData = new FormData();
    formData.append('asset_id', data.assetId);
    formData.append('wallet_address', data.walletAddress);
    formData.append('critical_metadata', JSON.stringify(data.criticalMetadata));
    
    if (data.nonCriticalMetadata) {
      formData.append('non_critical_metadata', JSON.stringify(data.nonCriticalMetadata));
    }
    
    try {
      const response = await apiClient.post('/upload/metadata', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Error uploading metadata:', error);
      throw error;
    }
  },

  // Upload JSON files
  uploadJsonFiles: async (files, walletAddress) => {
    const formData = new FormData();
    formData.append('wallet_address', walletAddress);
    
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    
    try {
      const response = await apiClient.post('/upload/json', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Error uploading JSON files:', error);
      throw error;
    }
  },

  // Retrieve asset metadata
  retrieveMetadata: async (assetId, version = null) => {
    try {
      let url = `/retrieve/${assetId}`;
      if (version) {
        url += `?version=${version}`;
      }
      const { data } = await apiClient.get(url);
      return data;
    } catch (error) {
      console.error('Error retrieving metadata:', error);
      throw error;
    }
  },

  // Delete an asset
  deleteAsset: async (assetId, walletAddress, reason = null) => {
    try {
      const { data } = await apiClient.post('/delete', {
        asset_id: assetId,
        wallet_address: walletAddress,
        reason
      });
      return data;
    } catch (error) {
      console.error('Error deleting asset:', error);
      throw error;
    }
  },

  // Get user's assets (this endpoint might need to be added to the backend)
  getUserAssets: async (walletAddress) => {
    try {
      // This endpoint might need to be implemented in the backend
      const { data } = await apiClient.get(`/assets/user/${walletAddress}`);
      return data;
    } catch (error) {
      console.error('Error fetching user assets:', error);
      throw error;
    }
  }
};