import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import apiKeyService from '../services/apiKeyService';
import './ApiKeysPage.css';

const ApiKeysPage = () => {
  const { account, isAuthenticated } = useAuth();
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showCreatedKey, setShowCreatedKey] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    permissions: ['read'],
    expiresIn: 90,
    metadata: {}
  });

  useEffect(() => {
    if (isAuthenticated) {
      fetchApiKeys();
    }
  }, [isAuthenticated]);

  const fetchApiKeys = async () => {
    try {
      setLoading(true);
      const keys = await apiKeyService.listApiKeys();
      setApiKeys(keys);
      setError(null);
    } catch (err) {
      setError('Failed to fetch API keys');
      console.error('Error fetching API keys:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApiKey = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      
      // Calculate expiration date
      const expiresAt = new Date();
      expiresAt.setDate(expiresAt.getDate() + formData.expiresIn);
      
      const apiKeyData = {
        name: formData.name,
        permissions: formData.permissions,
        expires_at: expiresAt.toISOString(),
        metadata: {
          ...formData.metadata,
          createdBy: account,
          createdAt: new Date().toISOString()
        }
      };

      const createdKey = await apiKeyService.createApiKey(apiKeyData);
      
      // Show the created key to the user (only shown once)
      setShowCreatedKey(createdKey);
      setShowCreateForm(false);
      setFormData({
        name: '',
        permissions: ['read'],
        expiresIn: 90,
        metadata: {}
      });
      
      // Refresh the list
      await fetchApiKeys();
    } catch (err) {
      setError('Failed to create API key');
      console.error('Error creating API key:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeKey = async (keyName) => {
    if (!window.confirm(`Are you sure you want to revoke the API key "${keyName}"?`)) {
      return;
    }

    try {
      setLoading(true);
      await apiKeyService.revokeApiKey(keyName);
      await fetchApiKeys();
      setError(null);
    } catch (err) {
      setError('Failed to revoke API key');
      console.error('Error revoking API key:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionToggle = (permission) => {
    setFormData(prev => {
      const newPermissions = prev.permissions.includes(permission)
        ? prev.permissions.filter(p => p !== permission)
        : [...prev.permissions, permission];
      
      // If admin is selected, it overrides all other permissions
      if (permission === 'admin' && newPermissions.includes('admin')) {
        return { ...prev, permissions: ['admin'] };
      }
      
      // If other permissions are selected, remove admin
      if (permission !== 'admin' && newPermissions.includes('admin')) {
        return { ...prev, permissions: newPermissions.filter(p => p !== 'admin') };
      }
      
      return { ...prev, permissions: newPermissions };
    });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert('API key copied to clipboard!');
  };

  if (!isAuthenticated) {
    return (
      <div className="api-keys-page">
        <div className="container">
          <h1>API Keys</h1>
          <p>Please connect your wallet to manage API keys.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="api-keys-page">
      <div className="container">
        <div className="page-header">
          <h1>API Keys</h1>
          <button 
            className="btn btn-primary"
            onClick={() => setShowCreateForm(true)}
            disabled={loading}
          >
            Create New API Key
          </button>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {showCreatedKey && (
          <div className="api-key-created">
            <div className="warning-box">
              <h3>⚠️ Important: Save Your API Key</h3>
              <p>This is the only time you'll see this API key. Please copy and save it securely.</p>
              <div className="api-key-display">
                <code>{showCreatedKey.api_key}</code>
                <button 
                  className="btn btn-secondary"
                  onClick={() => copyToClipboard(showCreatedKey.api_key)}
                >
                  Copy
                </button>
              </div>
              <button 
                className="btn btn-primary"
                onClick={() => setShowCreatedKey(null)}
              >
                I've Saved My Key
              </button>
            </div>
          </div>
        )}

        {showCreateForm && (
          <div className="create-form-modal">
            <div className="modal-content">
              <h2>Create New API Key</h2>
              <form onSubmit={handleCreateApiKey}>
                <div className="form-group">
                  <label htmlFor="name">Key Name</label>
                  <input
                    type="text"
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., My Application Key"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Permissions</label>
                  <div className="permissions-grid">
                    {apiKeyService.getAvailablePermissions().map(({ value, label }) => (
                      <label key={value} className="permission-checkbox">
                        <input
                          type="checkbox"
                          checked={formData.permissions.includes(value)}
                          onChange={() => handlePermissionToggle(value)}
                        />
                        <span>{label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="expiresIn">Expires In (days)</label>
                  <select
                    id="expiresIn"
                    value={formData.expiresIn}
                    onChange={(e) => setFormData({ ...formData, expiresIn: parseInt(e.target.value) })}
                  >
                    <option value={30}>30 days</option>
                    <option value={90}>90 days</option>
                    <option value={180}>180 days</option>
                    <option value={365}>1 year</option>
                  </select>
                </div>

                <div className="form-actions">
                  <button type="submit" className="btn btn-primary" disabled={loading}>
                    Create API Key
                  </button>
                  <button 
                    type="button" 
                    className="btn btn-secondary"
                    onClick={() => setShowCreateForm(false)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        <div className="api-keys-list">
          <h2>Your API Keys</h2>
          {loading ? (
            <p>Loading...</p>
          ) : apiKeys.length === 0 ? (
            <p>No API keys yet. Create your first one!</p>
          ) : (
            <div className="keys-table">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Permissions</th>
                    <th>Created</th>
                    <th>Last Used</th>
                    <th>Expires</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {apiKeys.map((key) => (
                    <tr key={key.name}>
                      <td>{key.name}</td>
                      <td>{apiKeyService.formatPermissions(key.permissions)}</td>
                      <td>{new Date(key.created_at).toLocaleDateString()}</td>
                      <td>{key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}</td>
                      <td>{key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never'}</td>
                      <td>
                        <span className={`status ${key.is_active ? 'active' : 'inactive'}`}>
                          {key.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <button 
                          className="btn btn-danger btn-sm"
                          onClick={() => handleRevokeKey(key.name)}
                          disabled={!key.is_active || loading}
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="api-usage-info">
          <h2>Using Your API Keys</h2>
          <div className="code-example">
            <h3>Example Request</h3>
            <pre>
{`curl -X GET \\
  https://api.fusevault.com/assets/user/{wallet_address} \\
  -H 'X-API-Key: your_api_key_here'`}
            </pre>
          </div>
          <div className="info-box">
            <h3>Important Notes:</h3>
            <ul>
              <li>API keys are tied to your wallet address and can only access your assets</li>
              <li>For blockchain operations, you must first delegate permission to the FuseVault server</li>
              <li>Keep your API keys secure and never share them publicly</li>
              <li>Revoked keys cannot be restored</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApiKeysPage;