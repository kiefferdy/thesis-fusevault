import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import delegationService from '../services/delegationService';
import { toast } from 'react-hot-toast';
import './DelegateAssetManagementPage.css';

const DelegateAssetManagementPage = () => {
  const { ownerAddress } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [ownerInfo, setOwnerInfo] = useState({});

  const loadDelegatedAssets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await delegationService.getDelegatedAssets(ownerAddress);
      
      setAssets(response.assets || []);
      setOwnerInfo({
        address: response.owner_address,
        username: response.owner_username,
        totalAssets: response.total_assets
      });
      
    } catch (err) {
      setError('Failed to load delegated assets');
      console.error('Error loading delegated assets:', err);
      
      if (err.response?.status === 403) {
        toast.error('You do not have permission to manage assets for this user');
        navigate('/delegation');
      }
    } finally {
      setLoading(false);
    }
  }, [ownerAddress, navigate]);

  useEffect(() => {
    if (isAuthenticated && ownerAddress) {
      loadDelegatedAssets();
    }
  }, [isAuthenticated, ownerAddress, loadDelegatedAssets]);

  const formatAddress = (address) => {
    if (!address) return '';
    if (address.length < 10) return address;
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    return new Date(dateString).toLocaleDateString();
  };

  const handleAssetClick = (assetId) => {
    // Navigate to asset details or management page
    navigate(`/assets/${assetId}`);
  };

  const handleBack = () => {
    navigate('/delegation');
  };

  if (!isAuthenticated) {
    return (
      <div className="delegate-asset-management">
        <div className="container">
          <h1>Delegate Asset Management</h1>
          <p>Please connect your wallet to manage delegated assets.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="delegate-asset-management">
        <div className="container">
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading delegated assets...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="delegate-asset-management">
        <div className="container">
          <div className="error-state">
            <h1>Error</h1>
            <p>{error}</p>
            <button onClick={handleBack} className="btn btn-primary">
              Back to Delegation
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="delegate-asset-management">
      <div className="container">
        <div className="page-header">
          <button onClick={handleBack} className="back-button">
            ← Back to Delegation
          </button>
          <div className="header-info">
            <h1>🛠️ Managing Assets</h1>
            <div className="owner-info">
              <h2>Owner: {ownerInfo.username || 'Unknown User'}</h2>
              <p className="owner-address">{formatAddress(ownerInfo.address)}</p>
              <p className="asset-count">{ownerInfo.totalAssets} assets</p>
            </div>
          </div>
        </div>

        {assets.length === 0 ? (
          <div className="empty-state">
            <h3>No Assets Found</h3>
            <p>This user has no assets or all assets are currently deleted.</p>
          </div>
        ) : (
          <div className="assets-section">
            <div className="assets-grid">
              {assets.map((asset) => (
                <div 
                  key={asset._id} 
                  className={`asset-card ${asset.isDeleted ? 'deleted' : ''}`}
                  onClick={() => handleAssetClick(asset.assetId)}
                >
                  <div className="asset-header">
                    <h3>{asset.assetId}</h3>
                    {asset.isDeleted && (
                      <span className="deleted-badge">Deleted</span>
                    )}
                  </div>
                  
                  <div className="asset-info">
                    <div className="asset-meta">
                      <p><strong>Name:</strong> {asset.criticalMetadata?.name || 'Unnamed'}</p>
                      <p><strong>Type:</strong> {asset.criticalMetadata?.type || 'Unknown'}</p>
                      <p><strong>Version:</strong> {asset.versionNumber || 1}</p>
                      <p><strong>Created:</strong> {formatDate(asset.createdAt)}</p>
                      <p><strong>Updated:</strong> {formatDate(asset.updatedAt)}</p>
                    </div>
                    
                    {asset.criticalMetadata?.description && (
                      <div className="asset-description">
                        <p><strong>Description:</strong></p>
                        <p className="description-text">
                          {asset.criticalMetadata.description.length > 100 
                            ? `${asset.criticalMetadata.description.substring(0, 100)}...`
                            : asset.criticalMetadata.description
                          }
                        </p>
                      </div>
                    )}
                  </div>
                  
                  <div className="asset-actions">
                    <div className="action-buttons">
                      <button 
                        className="btn btn-secondary btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAssetClick(asset.assetId);
                        }}
                      >
                        View Details
                      </button>
                      {!asset.isDeleted && (
                        <button 
                          className="btn btn-primary btn-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            // Navigate to edit page or open edit modal
                            navigate(`/upload?edit=${asset.assetId}&delegate=${ownerInfo.address}`);
                          }}
                        >
                          Edit Metadata
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="delegate-info">
          <h2>Delegation Information</h2>
          <div className="info-grid">
            <div className="info-card">
              <h3>🔒 Your Role</h3>
              <p>
                You have been granted delegate permissions by this user. 
                You can view, edit, and manage their assets on their behalf.
              </p>
            </div>
            <div className="info-card">
              <h3>⚡ Available Actions</h3>
              <ul>
                <li>View asset details and metadata</li>
                <li>Update asset metadata</li>
                <li>Create new versions of assets</li>
                <li>Delete assets (if permitted)</li>
              </ul>
            </div>
            <div className="info-card">
              <h3>🛡️ Responsibilities</h3>
              <p>
                Use these permissions responsibly. All actions you perform 
                will be recorded with your address as the performer while 
                maintaining the original owner's ownership.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DelegateAssetManagementPage;