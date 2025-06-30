import apiClient from './apiClient';
import { ethers } from 'ethers';

const DELEGATION_BASE_URL = '/delegation';

/**
 * Delegation Service - handles all delegation related operations
 */
const delegationService = {
  /**
   * Get server information including server wallet address
   * This is a public endpoint that doesn't require authentication
   * @returns {Promise<Object>} Server info including wallet address and features
   */
  getServerInfo: async () => {
    try {
      const response = await apiClient.get(`${DELEGATION_BASE_URL}/server-info`);
      return response.data;
    } catch (error) {
      console.error('Error getting server info:', error);
      throw error;
    }
  },

  /**
   * Check current user's delegation status
   * @returns {Promise<Object>} Delegation status for the current user
   */
  checkDelegationStatus: async () => {
    try {
      const response = await apiClient.get(`${DELEGATION_BASE_URL}/status`);
      return response.data;
    } catch (error) {
      console.error('Error checking delegation status:', error);
      throw error;
    }
  },

  /**
   * Prepare a delegation transaction (returns unsigned transaction)
   * @param {string} delegateAddress - Address to delegate to (server wallet)
   * @param {boolean} status - True to delegate, false to revoke
   * @returns {Promise<Object>} Unsigned transaction data
   */
  prepareDelegationTransaction: async (delegateAddress, status) => {
    try {
      const response = await apiClient.post(`${DELEGATION_BASE_URL}/set`, {
        delegate_address: delegateAddress,
        status: status
      });
      return response.data;
    } catch (error) {
      console.error('Error preparing delegation transaction:', error);
      throw error;
    }
  },

  /**
   * Check specific delegation between two addresses
   * @param {string} ownerAddress - The owner address
   * @param {string} delegateAddress - The delegate address
   * @returns {Promise<Object>} Delegation status between the addresses
   */
  checkSpecificDelegation: async (ownerAddress, delegateAddress) => {
    try {
      const response = await apiClient.get(
        `${DELEGATION_BASE_URL}/check/${ownerAddress}/${delegateAddress}`
      );
      return response.data;
    } catch (error) {
      console.error('Error checking specific delegation:', error);
      throw error;
    }
  },

  /**
   * Helper function to format wallet addresses for display
   * @param {string} address - Full wallet address
   * @returns {string} Formatted address (first 6 + last 4 characters)
   */
  formatAddress: (address) => {
    if (!address) return '';
    if (address.length < 10) return address;
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  },

  /**
   * Helper function to check if an address is valid
   * @param {string} address - Address to validate
   * @returns {boolean} Whether the address appears valid
   */
  isValidAddress: (address) => {
    if (!address) return false;
    // Basic validation: starts with 0x and is 42 characters long
    return address.startsWith('0x') && address.length === 42;
  },

  /**
   * Get delegation explanation text for UI
   * @returns {Object} Explanation text for different delegation states
   */
  getDelegationExplanations: () => ({
    notDelegated: {
      title: 'Delegation Required',
      description: 'To use API keys, you must first delegate permission to the FuseVault server wallet.',
      benefits: [
        'You maintain full ownership of your assets',
        'The server cannot transfer or steal your assets',
        'You can revoke delegation at any time',
        'Required for API key functionality'
      ]
    },
    delegated: {
      title: 'Delegation Active',
      description: 'The FuseVault server wallet has permission to perform operations on your behalf.',
      capabilities: [
        'API keys can update your assets',
        'API keys can delete your assets',
        'Server can act as your delegate for blockchain operations'
      ]
    }
  }),

  /**
   * Get network information for display
   * @param {number} chainId - Chain ID from server info
   * @returns {Object} Network display information
   */
  getNetworkInfo: (chainId) => {
    const networks = {
      1: { name: 'Ethereum Mainnet', explorer: 'https://etherscan.io' },
      11155111: { name: 'Sepolia Testnet', explorer: 'https://sepolia.etherscan.io' },
      5: { name: 'Goerli Testnet', explorer: 'https://goerli.etherscan.io' }
    };
    
    return networks[chainId] || { 
      name: `Unknown Network (${chainId})`, 
      explorer: '#' 
    };
  },

  // User-to-User Delegation Methods

  /**
   * Search for users by wallet address or username
   * @param {string} query - Search query (wallet address or username)
   * @param {number} limit - Maximum number of results
   * @returns {Promise<Object>} Search results
   */
  searchUsers: async (query, limit = 10) => {
    try {
      const response = await apiClient.get(`${DELEGATION_BASE_URL}/users/search`, {
        params: { q: query, limit }
      });
      return response.data;
    } catch (error) {
      console.error('Error searching users:', error);
      throw error;
    }
  },

  /**
   * Prepare a transaction to delegate to another user
   * @param {string} delegateAddress - Address to delegate to
   * @param {boolean} status - True to delegate, false to revoke
   * @returns {Promise<Object>} Unsigned transaction data
   */
  prepareUserDelegationTransaction: async (delegateAddress, status) => {
    try {
      const response = await apiClient.post(`${DELEGATION_BASE_URL}/users/delegate`, {
        delegate_address: delegateAddress,
        status: status
      });
      return response.data;
    } catch (error) {
      console.error('Error preparing user delegation transaction:', error);
      throw error;
    }
  },

  /**
   * Get list of users I have delegated to
   * @returns {Promise<Object>} List of delegates
   */
  getMyDelegates: async () => {
    try {
      const response = await apiClient.get(`${DELEGATION_BASE_URL}/users/my-delegates`);
      return response.data;
    } catch (error) {
      console.error('Error getting my delegates:', error);
      throw error;
    }
  },

  /**
   * Get list of users who have delegated to me
   * @returns {Promise<Object>} List of delegators
   */
  getDelegatedToMe: async () => {
    try {
      const response = await apiClient.get(`${DELEGATION_BASE_URL}/users/delegated-to-me`);
      return response.data;
    } catch (error) {
      console.error('Error getting delegated to me:', error);
      throw error;
    }
  },

  /**
   * Prepare a transaction to revoke delegation from a user
   * @param {string} delegateAddress - Address to revoke delegation from
   * @returns {Promise<Object>} Unsigned transaction data
   */
  prepareRevokeDelegationTransaction: async (delegateAddress) => {
    try {
      const response = await apiClient.delete(`${DELEGATION_BASE_URL}/users/delegate/${delegateAddress}`);
      return response.data;
    } catch (error) {
      console.error('Error preparing revoke delegation transaction:', error);
      throw error;
    }
  },

  /**
   * Get assets of a user who has delegated to me
   * @param {string} ownerAddress - Address of the user who delegated to me
   * @returns {Promise<Object>} Delegated assets
   */
  getDelegatedAssets: async (ownerAddress) => {
    try {
      const response = await apiClient.get(`${DELEGATION_BASE_URL}/users/${ownerAddress}/assets`);
      return response.data;
    } catch (error) {
      console.error('Error getting delegated assets:', error);
      throw error;
    }
  },

  /**
   * Helper function to execute a delegation transaction using MetaMask
   * @param {Object} txData - Transaction data from prepare delegation methods
   * @param {Function} onProgress - Progress callback function
   * @returns {Promise<Object>} Transaction receipt
   */
  executeDelegationTransaction: async (txData, onProgress = () => {}) => {
    try {
      if (!window.ethereum) {
        throw new Error('MetaMask is not installed');
      }

      onProgress('Connecting to wallet...');
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();

      if (!txData.transaction_data) {
        throw new Error('Invalid transaction data');
      }

      onProgress('Sending transaction...');
      const tx = await signer.sendTransaction(txData.transaction_data.transaction);

      onProgress('Waiting for confirmation...');
      const receipt = await tx.wait();

      if (receipt.status === 0) {
        throw new Error('Transaction failed on blockchain');
      }

      return receipt;
    } catch (error) {
      console.error('Error executing delegation transaction:', error);
      throw error;
    }
  }
};

export default delegationService;