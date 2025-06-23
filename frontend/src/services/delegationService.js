import apiClient from './apiClient';

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
  }
};

export default delegationService;