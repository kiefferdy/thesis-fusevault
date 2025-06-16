import apiClient from './apiClient';

export const blockchainService = {
  // Estimate gas for a transaction
  estimateGas: async (action, assetId, cid = null, ownerAddress = null) => {
    try {
      const params = new URLSearchParams({
        action,
        asset_id: assetId
      });
      
      if (cid) params.append('cid', cid);
      if (ownerAddress) params.append('owner_address', ownerAddress);
      
      const response = await apiClient.get(`/blockchain/estimate-gas?${params}`);
      return response.data;
    } catch (error) {
      console.error('Error estimating gas:', error);
      throw error;
    }
  },

  // Prepare transaction for signing
  prepareTransaction: async (action, assetId, cid = null, ownerAddress = null, gasLimit = null) => {
    try {
      const payload = {
        action,
        asset_id: assetId
      };
      
      if (cid) payload.cid = cid;
      if (ownerAddress) payload.owner_address = ownerAddress;
      if (gasLimit) payload.gas_limit = gasLimit;
      
      const response = await apiClient.post('/blockchain/prepare-transaction', payload);
      return response.data;
    } catch (error) {
      console.error('Error preparing transaction:', error);
      throw error;
    }
  },

  // Broadcast signed transaction
  broadcastTransaction: async (signedTransaction, action, assetId, cid = null, ownerAddress = null, metadata = {}) => {
    try {
      const payload = {
        signed_transaction: signedTransaction,
        action,
        asset_id: assetId,
        metadata
      };
      
      if (cid) payload.cid = cid;
      if (ownerAddress) payload.owner_address = ownerAddress;
      
      const response = await apiClient.post('/blockchain/broadcast-transaction', payload);
      return response.data;
    } catch (error) {
      console.error('Error broadcasting transaction:', error);
      throw error;
    }
  },

  // Verify transaction status
  verifyTransaction: async (txHash) => {
    try {
      const response = await apiClient.get(`/blockchain/verify-transaction/${txHash}`);
      return response.data;
    } catch (error) {
      console.error('Error verifying transaction:', error);
      throw error;
    }
  },

  // Get transaction status (pending, confirmed, failed)
  getTransactionStatus: async (txHash) => {
    try {
      const response = await apiClient.get(`/blockchain/transaction-status/${txHash}`);
      return response.data;
    } catch (error) {
      console.error('Error getting transaction status:', error);
      throw error;
    }
  }
};

// Utility functions for working with MetaMask
export const metamaskUtils = {
  // Check if MetaMask is available
  isMetaMaskAvailable: () => {
    return typeof window !== 'undefined' && typeof window.ethereum !== 'undefined';
  },

  // Get current account
  getCurrentAccount: async () => {
    if (!metamaskUtils.isMetaMaskAvailable()) {
      throw new Error('MetaMask not available');
    }
    
    const accounts = await window.ethereum.request({ method: 'eth_accounts' });
    return accounts[0] || null;
  },

  // Sign transaction with MetaMask
  signTransaction: async (transaction) => {
    if (!metamaskUtils.isMetaMaskAvailable()) {
      throw new Error('MetaMask not detected. Please install MetaMask extension.');
    }

    try {
      // Validate transaction data
      if (!transaction || !transaction.to || !transaction.data) {
        throw new Error('Invalid transaction data');
      }
      
      const accounts = await window.ethereum.request({ method: 'eth_accounts' });
      if (!accounts || accounts.length === 0) {
        // Try to request account access
        try {
          await window.ethereum.request({ method: 'eth_requestAccounts' });
          const newAccounts = await window.ethereum.request({ method: 'eth_accounts' });
          if (!newAccounts || newAccounts.length === 0) {
            throw new Error('No wallet connected after permission request');
          }
        } catch (accessError) {
          throw new Error('Please connect your MetaMask wallet and try again');
        }
      }

      // Verify the transaction is from the connected account
      const currentAccount = accounts[0].toLowerCase();
      if (transaction.from && transaction.from.toLowerCase() !== currentAccount) {
        throw new Error('Transaction sender does not match connected wallet');
      }

      // Send the transaction using MetaMask
      const txHash = await window.ethereum.request({
        method: 'eth_sendTransaction',
        params: [{
          ...transaction,
          from: currentAccount // Ensure from address matches connected account
        }],
      });

      if (!txHash) {
        throw new Error('Transaction signing failed - no transaction hash received');
      }

      return txHash;
    } catch (error) {
      console.error('Error signing transaction:', error);
      
      // Handle specific MetaMask errors
      if (error.code === 4001) {
        throw new Error('Transaction cancelled by user');
      } else if (error.code === -32603) {
        throw new Error('Internal MetaMask error - please try again');
      } else if (error.code === -32002) {
        throw new Error('MetaMask is busy - please check your wallet and try again');
      }
      
      throw error;
    }
  },

  // Get network info
  getNetworkInfo: async () => {
    if (!metamaskUtils.isMetaMaskAvailable()) {
      throw new Error('MetaMask not available');
    }

    try {
      const chainId = await window.ethereum.request({ method: 'eth_chainId' });
      return { chainId };
    } catch (error) {
      console.error('Error getting network info:', error);
      throw new Error('Failed to get network information from MetaMask');
    }
  },

  // Check if user is on the correct network (Sepolia testnet)
  checkNetwork: async () => {
    try {
      const { chainId } = await metamaskUtils.getNetworkInfo();
      const sepoliaChainId = '0xaa36a7'; // Sepolia testnet chain ID
      
      if (chainId !== sepoliaChainId) {
        return {
          isCorrectNetwork: false,
          currentChainId: chainId,
          expectedChainId: sepoliaChainId,
          networkName: metamaskUtils.getNetworkName(chainId)
        };
      }
      
      return { isCorrectNetwork: true, currentChainId: chainId };
    } catch (error) {
      throw new Error('Failed to check network - please ensure MetaMask is connected');
    }
  },
  
  // Get human-readable network name
  getNetworkName: (chainId) => {
    const networks = {
      '0x1': 'Ethereum Mainnet',
      '0x3': 'Ropsten Testnet',
      '0x4': 'Rinkeby Testnet',
      '0x5': 'Goerli Testnet',
      '0xaa36a7': 'Sepolia Testnet',
      '0x89': 'Polygon Mainnet',
      '0x13881': 'Polygon Mumbai Testnet'
    };
    
    return networks[chainId] || `Unknown Network (${chainId})`;
  },
  
  // Switch to Sepolia network
  switchToSepolia: async () => {
    if (!metamaskUtils.isMetaMaskAvailable()) {
      throw new Error('MetaMask not available');
    }
    
    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: '0xaa36a7' }], // Sepolia testnet
      });
    } catch (switchError) {
      // This error code indicates that the chain has not been added to MetaMask
      if (switchError.code === 4902) {
        try {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [{
              chainId: '0xaa36a7',
              chainName: 'Sepolia Testnet',
              nativeCurrency: {
                name: 'Sepolia ETH',
                symbol: 'SepoliaETH',
                decimals: 18
              },
              rpcUrls: ['https://sepolia.infura.io/v3/'],
              blockExplorerUrls: ['https://sepolia.etherscan.io/']
            }]
          });
        } catch (addError) {
          throw new Error('Failed to add Sepolia network to MetaMask');
        }
      } else {
        throw new Error('Failed to switch to Sepolia network');
      }
    }
  },

  // Format transaction for MetaMask
  formatTransactionForMetaMask: (transaction) => {
    return {
      from: transaction.from,
      to: transaction.to,
      gas: `0x${transaction.gas.toString(16)}`,
      gasPrice: `0x${transaction.gasPrice.toString(16)}`,
      value: transaction.value || '0x0',
      data: transaction.data,
      nonce: `0x${transaction.nonce.toString(16)}`
    };
  }
};

// Main transaction flow orchestrator
export const transactionFlow = {
  // Complete upload flow with user signing
  uploadWithSigning: async (assetData, onProgress = () => {}) => {
    try {
      onProgress('Preparing upload...', 10);
      
      // Validate input data
      if (!assetData?.assetId || !assetData?.walletAddress) {
        throw new Error('Asset ID and wallet address are required');
      }
      
      // Check network before starting transaction
      if (metamaskUtils.isMetaMaskAvailable()) {
        const networkCheck = await metamaskUtils.checkNetwork();
        if (!networkCheck.isCorrectNetwork) {
          throw new Error(
            `Wrong network detected. Please switch to Sepolia Testnet in MetaMask. ` +
            `Currently on: ${networkCheck.networkName}`
          );
        }
        console.log(`✅ Network verified: Connected to Sepolia (${networkCheck.currentChainId})`);
      }
      
      // Step 1: Initial upload request (will return pending_signature status for wallet users)
      const { assetService } = await import('./assetService');
      const uploadResult = await assetService.uploadMetadata(assetData);
      
      // Check if we need to sign a transaction
      if (uploadResult.status === 'pending_signature') {
        if (!uploadResult.transaction) {
          throw new Error('No transaction data received from server');
        }
        
        onProgress('Waiting for transaction signature...', 30);
        
        // Step 2: Sign transaction with MetaMask
        const formattedTx = metamaskUtils.formatTransactionForMetaMask(uploadResult.transaction);
        const txHash = await metamaskUtils.signTransaction(formattedTx);
        
        if (!txHash) {
          throw new Error('Transaction was not signed');
        }
        
        // Verify we're still on correct network after signing
        const postSignNetworkCheck = await metamaskUtils.checkNetwork();
        if (!postSignNetworkCheck.isCorrectNetwork) {
          throw new Error(
            `Network changed during signing! Transaction sent to ${postSignNetworkCheck.networkName} ` +
            `but expected Sepolia. Transaction hash: ${txHash}`
          );
        }
        
        console.log(`✅ Transaction sent to Sepolia: ${txHash}`);
        onProgress('Transaction sent, waiting for confirmation...', 60);
        
        // Step 3: Wait for transaction confirmation
        await transactionFlow.waitForConfirmation(txHash, onProgress);
        
        onProgress('Completing upload...', 90);
        
        // Step 4: Complete the upload
        if (!uploadResult.pending_tx_id) {
          console.error('Upload result missing pending_tx_id:', uploadResult);
          throw new Error('Server response missing pending transaction ID');
        }
        
        const completionPayload = {
          pending_tx_id: uploadResult.pending_tx_id,
          blockchain_tx_hash: txHash
        };
        console.log('🔍 Completion payload:', JSON.stringify(completionPayload, null, 2));
        
        const completionResult = await apiClient.post('/upload/complete', completionPayload);
        
        if (!completionResult?.data?.success) {
          throw new Error('Upload completion failed on server');
        }
        
        onProgress('Upload completed!', 100);
        return completionResult.data;
      } else {
        // For API key users, the upload is already complete
        onProgress('Upload completed!', 100);
        return uploadResult;
      }
    } catch (error) {
      const friendlyError = transactionFlow.handleTransactionError(error);
      console.error('Error in upload flow:', friendlyError);
      throw friendlyError;
    }
  },

  // Complete delete flow with user signing
  deleteWithSigning: async (assetId, walletAddress, reason = null, onProgress = () => {}) => {
    try {
      onProgress('Preparing deletion...', 10);
      
      // Validate input data
      if (!assetId || !walletAddress) {
        throw new Error('Asset ID and wallet address are required');
      }
      
      // Check network before starting transaction
      if (metamaskUtils.isMetaMaskAvailable()) {
        const networkCheck = await metamaskUtils.checkNetwork();
        if (!networkCheck.isCorrectNetwork) {
          throw new Error(
            `Wrong network detected. Please switch to Sepolia Testnet in MetaMask. ` +
            `Currently on: ${networkCheck.networkName}`
          );
        }
        console.log(`✅ Network verified: Connected to Sepolia (${networkCheck.currentChainId})`);
      }
      
      // Step 1: Initial delete request
      const { assetService } = await import('./assetService');
      const deleteResult = await assetService.deleteAsset(assetId, walletAddress, reason);
      
      // Check if we need to sign a transaction
      if (deleteResult.status === 'pending_signature') {
        if (!deleteResult.transaction) {
          throw new Error('No transaction data received from server');
        }
        
        onProgress('Waiting for transaction signature...', 30);
        
        // Step 2: Sign transaction with MetaMask
        const formattedTx = metamaskUtils.formatTransactionForMetaMask(deleteResult.transaction);
        const txHash = await metamaskUtils.signTransaction(formattedTx);
        
        if (!txHash) {
          throw new Error('Transaction was not signed');
        }
        
        // Verify we're still on correct network after signing
        const postSignNetworkCheck = await metamaskUtils.checkNetwork();
        if (!postSignNetworkCheck.isCorrectNetwork) {
          throw new Error(
            `Network changed during signing! Transaction sent to ${postSignNetworkCheck.networkName} ` +
            `but expected Sepolia. Transaction hash: ${txHash}`
          );
        }
        
        console.log(`✅ Transaction sent to Sepolia: ${txHash}`);
        onProgress('Transaction sent, waiting for confirmation...', 60);
        
        // Step 3: Wait for transaction confirmation
        await transactionFlow.waitForConfirmation(txHash, onProgress);
        
        onProgress('Completing deletion...', 90);
        
        // Step 4: Complete the deletion
        if (!deleteResult.pending_tx_id) {
          console.error('Delete result missing pending_tx_id:', deleteResult);
          throw new Error('Server response missing pending transaction ID');
        }
        
        const completionResult = await apiClient.post('/delete/complete', {
          pending_tx_id: deleteResult.pending_tx_id,
          blockchain_tx_hash: txHash
        });
        
        if (!completionResult?.data?.success) {
          throw new Error('Deletion completion failed on server');
        }
        
        onProgress('Deletion completed!', 100);
        return completionResult.data;
      } else {
        // For API key users, the deletion is already complete
        onProgress('Deletion completed!', 100);
        return deleteResult;
      }
    } catch (error) {
      const friendlyError = transactionFlow.handleTransactionError(error);
      console.error('Error in delete flow:', friendlyError);
      throw friendlyError;
    }
  },

  // Wait for transaction confirmation
  waitForConfirmation: async (txHash, onProgress = () => {}) => {
    if (!txHash) {
      throw new Error('Transaction hash is required for confirmation');
    }
    
    const maxAttempts = 30; // 5 minutes with 10-second intervals
    let attempts = 0;
    let lastError = null;
    
    while (attempts < maxAttempts) {
      try {
        const status = await blockchainService.getTransactionStatus(txHash);
        
        if (status.status === 'confirmed') {
          if (status.details && status.details.success) {
            return status.details;
          } else {
            throw new Error(
              status.details?.error || 
              'Transaction failed on blockchain - check your wallet for details'
            );
          }
        } else if (status.status === 'failed') {
          throw new Error(
            status.details?.error || 
            'Transaction failed on blockchain - insufficient gas or other error'
          );
        } else if (status.status === 'not_found' && attempts > 5) {
          // Only throw not_found after several attempts to account for network delays
          throw new Error('Transaction not found on blockchain - it may have been dropped');
        }
        
        // Transaction is still pending, wait and retry
        await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds
        attempts++;
        
        const progress = 60 + (attempts / maxAttempts) * 20; // Progress from 60% to 80%
        onProgress(`Waiting for confirmation... (${attempts}/${maxAttempts})`, progress);
      } catch (error) {
        lastError = error;
        
        // If it's a non-network error, throw immediately
        if (error.message.includes('failed') || error.message.includes('not found')) {
          throw error;
        }
        
        // For network errors, retry up to max attempts
        if (attempts === maxAttempts - 1) {
          throw new Error(
            `Transaction confirmation timeout after ${maxAttempts} attempts. ` +
            `Last error: ${lastError?.message || 'Unknown error'}`
          );
        }
        
        await new Promise(resolve => setTimeout(resolve, 10000));
        attempts++;
      }
    }
    
    throw new Error('Transaction confirmation timeout - check your wallet and try again');
  },

  // Handle and categorize transaction errors
  handleTransactionError: (error) => {
    const errorMessage = error?.message || error?.toString() || 'Unknown error';
    
    // MetaMask specific errors
    if (errorMessage.includes('User denied') || errorMessage.includes('user rejected')) {
      return new Error('Transaction was cancelled by user');
    }
    
    if (errorMessage.includes('insufficient funds')) {
      return new Error('Insufficient funds to complete transaction - check your ETH balance');
    }
    
    if (errorMessage.includes('gas too low') || errorMessage.includes('intrinsic gas too low')) {
      return new Error('Gas limit too low - please try again with higher gas settings');
    }
    
    if (errorMessage.includes('nonce too low')) {
      return new Error('Transaction nonce error - please refresh and try again');
    }
    
    if (errorMessage.includes('network') || errorMessage.includes('connection')) {
      return new Error('Network connection error - please check your internet and try again');
    }
    
    if (errorMessage.includes('MetaMask not')) {
      return new Error('MetaMask not detected - please install and setup MetaMask');
    }
    
    if (errorMessage.includes('No MetaMask account')) {
      return new Error('No wallet connected - please connect your MetaMask wallet');
    }
    
    // Server/API errors
    if (errorMessage.includes('401') || errorMessage.includes('unauthorized')) {
      return new Error('Authentication failed - please reconnect your wallet');
    }
    
    if (errorMessage.includes('400') || errorMessage.includes('validation')) {
      return new Error('Invalid request data - please check your inputs and try again');
    }
    
    if (errorMessage.includes('500') || errorMessage.includes('server')) {
      return new Error('Server error - please try again later');
    }
    
    // Return original error with some context if we can't categorize it
    return new Error(`Transaction failed: ${errorMessage}`);
  }
};