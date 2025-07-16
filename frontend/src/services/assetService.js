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
  },

  // Batch delete prepare - prepares batch deletion and returns transaction for signing
  prepareBatchDelete: async (assetIds, walletAddress, reason = null) => {
    // Validate input data
    if (!Array.isArray(assetIds) || assetIds.length === 0) {
      throw new Error('Asset IDs array is required and must not be empty');
    }
    
    if (assetIds.length > 50) {
      throw new Error('Batch size cannot exceed 50 assets');
    }
    
    if (!walletAddress || typeof walletAddress !== 'string' || !walletAddress.trim()) {
      throw new Error('Wallet address is required and must be a non-empty string');
    }
    
    // Validate each asset ID
    for (const assetId of assetIds) {
      if (!assetId || typeof assetId !== 'string' || !assetId.trim()) {
        throw new Error('All asset IDs must be non-empty strings');
      }
    }
    
    try {
      const { data } = await apiClient.post('/delete/batch/prepare', {
        asset_ids: assetIds.map(id => id.trim()),
        wallet_address: walletAddress.trim(),
        reason: reason ? reason.trim() : null
      });
      return data;
    } catch (error) {
      console.error('Error preparing batch delete:', error);
      
      // Provide better error messages based on the response
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;
        
        if (status === 400) {
          throw new Error(data?.detail || 'Invalid request - please check your data and try again');
        } else if (status === 401) {
          throw new Error('Authentication failed - please reconnect your wallet');
        } else if (status === 403) {
          throw new Error('Permission denied - you can only delete assets you own or have delegation for');
        } else if (status === 404) {
          throw new Error('One or more assets not found - they may have already been deleted');
        } else if (status >= 500) {
          throw new Error('Server error - please try again later');
        }
      } else if (error.request) {
        throw new Error('Network error - please check your connection and try again');
      }
      
      throw error;
    }
  },

  // Batch delete complete - completes batch deletion after blockchain confirmation
  completeBatchDelete: async (pendingTxId, blockchainTxHash) => {
    // Validate input data
    if (!pendingTxId || typeof pendingTxId !== 'string' || !pendingTxId.trim()) {
      throw new Error('Pending transaction ID is required and must be a non-empty string');
    }
    
    if (!blockchainTxHash || typeof blockchainTxHash !== 'string' || !blockchainTxHash.trim()) {
      throw new Error('Blockchain transaction hash is required and must be a non-empty string');
    }
    
    try {
      const { data } = await apiClient.post('/delete/batch/complete', {
        pending_tx_id: pendingTxId.trim(),
        blockchain_tx_hash: blockchainTxHash.trim()
      });
      return data;
    } catch (error) {
      console.error('Error completing batch delete:', error);
      
      // Provide better error messages based on the response
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;
        
        if (status === 400) {
          throw new Error(data?.detail || 'Transaction completion failed - please check the transaction hash');
        } else if (status === 401) {
          throw new Error('Authentication failed - please reconnect your wallet');
        } else if (status === 404) {
          throw new Error('Pending transaction not found or expired - please try the operation again');
        } else if (status >= 500) {
          throw new Error('Server error - please try again later');
        }
      } else if (error.request) {
        throw new Error('Network error - please check your connection and try again');
      }
      
      throw error;
    }
  },

  // Legacy batch delete (for backwards compatibility or direct execution)
  batchDeleteAssets: async (assetIds, walletAddress, reason = null) => {
    // Validate input data
    if (!Array.isArray(assetIds) || assetIds.length === 0) {
      throw new Error('Asset IDs array is required and must not be empty');
    }
    
    if (assetIds.length > 50) {
      throw new Error('Batch size cannot exceed 50 assets');
    }
    
    if (!walletAddress || typeof walletAddress !== 'string' || !walletAddress.trim()) {
      throw new Error('Wallet address is required and must be a non-empty string');
    }
    
    // Validate each asset ID
    for (const assetId of assetIds) {
      if (!assetId || typeof assetId !== 'string' || !assetId.trim()) {
        throw new Error('All asset IDs must be non-empty strings');
      }
    }
    
    try {
      const { data } = await apiClient.post('/delete/batch', {
        asset_ids: assetIds.map(id => id.trim()),
        wallet_address: walletAddress.trim(),
        reason: reason ? reason.trim() : null
      });
      return data;
    } catch (error) {
      console.error('Error batch deleting assets:', error);
      
      // Provide better error messages based on the response
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;
        
        if (status === 400) {
          throw new Error(data?.detail || 'Invalid request - please check your data and try again');
        } else if (status === 401) {
          throw new Error('Authentication failed - please reconnect your wallet');
        } else if (status === 403) {
          throw new Error('Permission denied - you can only delete assets you own or have delegation for');
        } else if (status === 404) {
          throw new Error('One or more assets not found - they may have already been deleted');
        } else if (status >= 500) {
          throw new Error('Server error - please try again later');
        }
      } else if (error.request) {
        throw new Error('Network error - please check your connection and try again');
      }
      
      throw error;
    }
  },

  // Stream metadata retrieval with real-time progress updates
  retrieveMetadataStream: (assetId, version = null, onProgress, onComplete, onError) => {
    // Validate input data
    if (!assetId || typeof assetId !== 'string' || !assetId.trim()) {
      const error = new Error('Asset ID is required and must be a non-empty string');
      if (onError) onError(error);
      return null;
    }

    if (typeof onProgress !== 'function') {
      const error = new Error('Progress callback is required and must be a function');
      if (onError) onError(error);
      return null;
    }

    try {
      // Build streaming URL
      let url = `/retrieve/${encodeURIComponent(assetId.trim())}/stream`;
      const params = new URLSearchParams();
      
      if (version !== null && version !== undefined) {
        if (typeof version !== 'number' || version < 0) {
          const error = new Error('Version must be a non-negative number');
          if (onError) onError(error);
          return null;
        }
        params.append('version', version.toString());
      }
      
      // Check for API key authentication
      const apiKey = localStorage.getItem('apiKey');
      if (apiKey) {
        params.append('key', apiKey);
      }
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }

      // Get the base URL and construct full URL for EventSource
      const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const fullUrl = `${baseURL}${url}`;
      
      // EventSource will automatically include cookies for session-based auth
      // API key auth is handled via query parameter for EventSource compatibility
      const eventSource = new EventSource(fullUrl, { withCredentials: true });
      let finalResult = null;
      let progressReceived = false;
      
      // Set up a timeout to detect if streaming is not working
      const streamTimeout = setTimeout(() => {
        if (!progressReceived) {
          console.warn('No progress received within 10 seconds, closing stream');
          eventSource.close();
          if (onError) onError(new Error('Streaming timeout - no progress received'));
        }
      }, 10000); // 10 second timeout
      
      eventSource.onmessage = (event) => {
        progressReceived = true;
        clearTimeout(streamTimeout);
        
        try {
          const data = JSON.parse(event.data);
          
          // Check if this is a progress message or final result
          if (data.step !== undefined && data.totalSteps !== undefined) {
            // This is a progress message
            onProgress(data);
            
            if (data.completed) {
              clearTimeout(streamTimeout);
              if (data.error) {
                // Progress completed with error
                eventSource.close();
                if (onError) onError(new Error(data.error));
              } else if (finalResult) {
                // Progress completed successfully and we have the final result
                eventSource.close();
                if (onComplete) onComplete(finalResult);
              }
            }
          } else if (data.assetId !== undefined) {
            // This is the final result data
            finalResult = data;
            clearTimeout(streamTimeout);
            // If progress is already completed, call onComplete immediately
            if (onComplete) onComplete(finalResult);
            eventSource.close();
          }
        } catch (parseError) {
          console.error('Error parsing SSE data:', parseError, 'Raw data:', event.data);
          // Don't close connection for parsing errors, might be keepalive
        }
      };

      eventSource.onerror = (error) => {
        console.error('EventSource error:', error);
        clearTimeout(streamTimeout);
        eventSource.close();
        
        // Provide user-friendly error message based on readyState
        let errorMessage = 'Connection error during asset retrieval. Please try again.';
        if (eventSource.readyState === EventSource.CONNECTING) {
          errorMessage = 'Unable to connect to server. Please check your connection and try again.';
        } else if (eventSource.readyState === EventSource.CLOSED) {
          errorMessage = 'Connection was closed unexpectedly. Please try again.';
        }
        
        if (onError) onError(new Error(errorMessage));
      };

      eventSource.onopen = () => {
        console.log('EventSource connection opened');
      };

      // Return an object with EventSource and cleanup function
      return {
        eventSource,
        close: () => {
          clearTimeout(streamTimeout);
          eventSource.close();
        }
      };
      
    } catch (error) {
      console.error('Error setting up metadata streaming:', error);
      if (onError) onError(error);
      return null;
    }
  }
};