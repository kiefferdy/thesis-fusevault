import apiClient from './apiClient';

export const assetService = {
  // Upload metadata
  uploadMetadata: async (data) => {
    // Validate input data
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid upload data provided');
    }
    
    if (!data.assetId || typeof data.assetId !== 'string' || !data.assetId.trim()) {
      throw new Error('Asset ID is required and must be a non-empty string');
    }
    
    if (!data.walletAddress || typeof data.walletAddress !== 'string' || !data.walletAddress.trim()) {
      throw new Error('Wallet address is required and must be a non-empty string');
    }
    
    if (!data.criticalMetadata || typeof data.criticalMetadata !== 'object') {
      throw new Error('Critical metadata is required and must be an object');
    }
    
    if (!data.criticalMetadata.name || !data.criticalMetadata.name.trim()) {
      throw new Error('Asset name is required in critical metadata');
    }
    
    const formData = new FormData();
    formData.append('asset_id', data.assetId.trim());
    formData.append('wallet_address', data.walletAddress.trim());
    formData.append('critical_metadata', JSON.stringify(data.criticalMetadata));
    
    if (data.nonCriticalMetadata && typeof data.nonCriticalMetadata === 'object') {
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
      
      // Provide better error messages based on the response
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;
        
        if (status === 400) {
          throw new Error(data?.detail || 'Invalid request - please check your data and try again');
        } else if (status === 401) {
          throw new Error('Authentication failed - please reconnect your wallet');
        } else if (status === 409) {
          throw new Error('Asset ID already exists - please use a different Asset ID');
        } else if (status === 413) {
          throw new Error('Upload too large - please reduce the size of your metadata');
        } else if (status >= 500) {
          throw new Error('Server error - please try again later');
        }
      } else if (error.request) {
        throw new Error('Network error - please check your connection and try again');
      }
      
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
    // Validate input data
    if (!assetId || typeof assetId !== 'string' || !assetId.trim()) {
      throw new Error('Asset ID is required and must be a non-empty string');
    }
    
    try {
      let url = `/retrieve/${encodeURIComponent(assetId.trim())}`;
      if (version !== null && version !== undefined) {
        if (typeof version !== 'number' || version < 0) {
          throw new Error('Version must be a non-negative number');
        }
        url += `?version=${version}`;
      }
      const { data } = await apiClient.get(url);
      return data;
    } catch (error) {
      console.error('Error retrieving metadata:', error);
      
      // Provide better error messages based on the response
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;
        
        if (status === 404) {
          throw new Error('Asset not found - please check the Asset ID and try again');
        } else if (status === 400) {
          throw new Error(data?.detail || 'Invalid request - please check your parameters');
        } else if (status >= 500) {
          throw new Error('Server error - please try again later');
        }
      } else if (error.request) {
        throw new Error('Network error - please check your connection and try again');
      }
      
      throw error;
    }
  },

  // Delete an asset
  deleteAsset: async (assetId, walletAddress, reason = null) => {
    // Validate input data
    if (!assetId || typeof assetId !== 'string' || !assetId.trim()) {
      throw new Error('Asset ID is required and must be a non-empty string');
    }
    
    if (!walletAddress || typeof walletAddress !== 'string' || !walletAddress.trim()) {
      throw new Error('Wallet address is required and must be a non-empty string');
    }
    
    try {
      const { data } = await apiClient.post('/delete', {
        asset_id: assetId.trim(),
        wallet_address: walletAddress.trim(),
        reason: reason ? reason.trim() : null
      });
      return data;
    } catch (error) {
      console.error('Error deleting asset:', error);
      
      // Provide better error messages based on the response
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;
        
        if (status === 400) {
          throw new Error(data?.detail || 'Invalid request - please check your data and try again');
        } else if (status === 401) {
          throw new Error('Authentication failed - please reconnect your wallet');
        } else if (status === 403) {
          throw new Error('Permission denied - you can only delete assets you own');
        } else if (status === 404) {
          throw new Error('Asset not found - it may have already been deleted');
        } else if (status >= 500) {
          throw new Error('Server error - please try again later');
        }
      } else if (error.request) {
        throw new Error('Network error - please check your connection and try again');
      }
      
      throw error;
    }
  },

  // Get user's assets (this endpoint might need to be added to the backend)
  getUserAssets: async (walletAddress) => {
    try {
      const { data } = await apiClient.get(`/assets/user/${walletAddress}`);
      console.log('User assets fetched:', data);
      return data;
    } catch (error) {
      console.error('Error fetching user assets:', error);
      // Return empty data structure on error to prevent crashes
      return { assets: [] };
    }
  }
};