import apiClient from './apiClient';

const API_KEYS_BASE_URL = '/api-keys';

/**
 * API Key Service - handles all API key related operations
 */
const apiKeyService = {
  /**
   * Get API keys feature status
   * @returns {Promise<Object>} API keys status and configuration
   */
  getStatus: async () => {
    try {
      const response = await apiClient.get(`${API_KEYS_BASE_URL}/status`);
      return response.data;
    } catch (error) {
      console.error('Error getting API keys status:', error);
      throw error;
    }
  },

  /**
   * Create a new API key
   * @param {Object} apiKeyData - The API key creation data
   * @param {string} apiKeyData.name - User-friendly name for the API key
   * @param {string[]} apiKeyData.permissions - Array of permissions (read, write, delete)
   * @param {string} apiKeyData.expires_at - Optional expiration date
   * @param {Object} apiKeyData.metadata - Optional metadata
   * @returns {Promise<Object>} Created API key data including the key itself
   */
  createApiKey: async (apiKeyData) => {
    try {
      const response = await apiClient.post(`${API_KEYS_BASE_URL}/create`, apiKeyData);
      return response.data;
    } catch (error) {
      console.error('Error creating API key:', error);
      throw error;
    }
  },

  /**
   * List all API keys for the authenticated user
   * @returns {Promise<Array>} List of API keys (without the actual key values)
   */
  listApiKeys: async () => {
    try {
      const response = await apiClient.get(`${API_KEYS_BASE_URL}/list`);
      return response.data;
    } catch (error) {
      console.error('Error listing API keys:', error);
      throw error;
    }
  },

  /**
   * Revoke an API key
   * @param {string} keyName - The name of the API key to revoke
   * @returns {Promise<Object>} Success message
   */
  revokeApiKey: async (keyName) => {
    try {
      const response = await apiClient.delete(`${API_KEYS_BASE_URL}/${keyName}`);
      return response.data;
    } catch (error) {
      console.error('Error revoking API key:', error);
      throw error;
    }
  },

  /**
   * Update permissions for an API key
   * @param {string} keyName - The name of the API key
   * @param {string[]} permissions - New permissions array
   * @returns {Promise<Object>} Success message
   */
  updateApiKeyPermissions: async (keyName, permissions) => {
    try {
      const response = await apiClient.put(`${API_KEYS_BASE_URL}/${keyName}/permissions`, {
        permissions
      });
      return response.data;
    } catch (error) {
      console.error('Error updating API key permissions:', error);
      throw error;
    }
  },

  /**
   * Format permissions for display
   * @param {string[]} permissions - Array of permission strings
   * @returns {string} Formatted permissions string
   */
  formatPermissions: (permissions) => {
    if (!permissions || permissions.length === 0) return 'None';
    return permissions.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(', ');
  },

  /**
   * Check if a permission is valid
   * @param {string} permission - Permission to check
   * @returns {boolean} Whether the permission is valid
   */
  isValidPermission: (permission) => {
    const validPermissions = ['read', 'write', 'delete'];
    return validPermissions.includes(permission);
  },

  /**
   * Get available permissions
   * @returns {Array<{value: string, label: string}>} Available permissions
   */
  getAvailablePermissions: () => [
    { value: 'read', label: 'Read - View assets and data' },
    { value: 'write', label: 'Write - Create and update assets' },
    { value: 'delete', label: 'Delete - Remove assets' }
  ]
};

export default apiKeyService;