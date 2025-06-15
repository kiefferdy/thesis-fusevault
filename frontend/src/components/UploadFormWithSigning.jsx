import React, { useState } from 'react';
import { useTransactionSigner } from '../hooks/useTransactionSigner';
import TransactionSigner from './TransactionSigner';
import { useAuth } from '../contexts/AuthContext';

const UploadFormWithSigning = ({ onUploadSuccess }) => {
  const [formData, setFormData] = useState({
    assetId: '',
    criticalMetadata: {
      name: '',
      description: '',
      type: ''
    },
    nonCriticalMetadata: {
      tags: '',
      notes: ''
    }
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const { user } = useAuth();
  
  const {
    isVisible,
    operation,
    operationData,
    showUploadSigner,
    hideSigner,
    onSuccess,
    onError,
    uploadWithSigning
  } = useTransactionSigner();

  const handleInputChange = (field, value) => {
    if (field.includes('.')) {
      const [parent, child] = field.split('.');
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...prev[parent],
          [child]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  const validateForm = () => {
    const errors = [];
    
    if (!user?.walletAddress) {
      errors.push('Please connect your wallet first');
    }
    
    if (!formData.assetId?.trim()) {
      errors.push('Asset ID is required');
    } else if (formData.assetId.length < 3) {
      errors.push('Asset ID must be at least 3 characters long');
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.assetId)) {
      errors.push('Asset ID can only contain letters, numbers, hyphens, and underscores');
    }
    
    if (!formData.criticalMetadata.name?.trim()) {
      errors.push('Asset name is required');
    } else if (formData.criticalMetadata.name.length > 100) {
      errors.push('Asset name must be 100 characters or less');
    }
    
    if (formData.criticalMetadata.description && formData.criticalMetadata.description.length > 500) {
      errors.push('Description must be 500 characters or less');
    }
    
    if (formData.nonCriticalMetadata.tags) {
      const tags = formData.nonCriticalMetadata.tags.split(',').map(tag => tag.trim()).filter(Boolean);
      if (tags.length > 10) {
        errors.push('Maximum 10 tags allowed');
      }
      for (const tag of tags) {
        if (tag.length > 30) {
          errors.push('Each tag must be 30 characters or less');
        }
      }
    }
    
    if (formData.nonCriticalMetadata.notes && formData.nonCriticalMetadata.notes.length > 1000) {
      errors.push('Notes must be 1000 characters or less');
    }
    
    return errors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    
    const validationErrors = validateForm();
    if (validationErrors.length > 0) {
      setError(validationErrors.join('. '));
      return;
    }

    const uploadData = {
      assetId: formData.assetId,
      walletAddress: user.walletAddress,
      criticalMetadata: {
        ...formData.criticalMetadata,
        timestamp: new Date().toISOString()
      },
      nonCriticalMetadata: {
        ...formData.nonCriticalMetadata,
        tags: formData.nonCriticalMetadata.tags.split(',').map(tag => tag.trim()).filter(Boolean)
      }
    };

    try {
      setIsLoading(true);
      
      // Option 1: Use the UI-based transaction signer
      showUploadSigner(
        uploadData,
        (result) => {
          console.log('Upload successful:', result);
          setIsLoading(false);
          hideSigner();
          
          // Reset form
          setFormData({
            assetId: '',
            criticalMetadata: { name: '', description: '', type: '' },
            nonCriticalMetadata: { tags: '', notes: '' }
          });
          
          if (onUploadSuccess) {
            onUploadSuccess(result);
          }
        },
        (error) => {
          console.error('Upload failed:', error);
          let errorMessage = 'Upload failed';
          
          if (error?.message) {
            errorMessage = error.message;
          } else if (error?.response?.data?.detail) {
            errorMessage = error.response.data.detail;
          } else if (error?.response?.status === 401) {
            errorMessage = 'Authentication failed - please reconnect your wallet';
          } else if (error?.response?.status === 400) {
            errorMessage = 'Invalid request - please check your input data';
          } else if (error?.response?.status >= 500) {
            errorMessage = 'Server error - please try again later';
          }
          
          setError(errorMessage);
          setIsLoading(false);
          hideSigner();
        }
      );

      // Option 2: Use direct method without UI (commented out)
      /*
      const result = await uploadWithSigning(uploadData, (step, progress) => {
        console.log(`${step} - ${progress}%`);
      });
      
      console.log('Upload successful:', result);
      setIsLoading(false);
      
      // Reset form
      setFormData({
        assetId: '',
        criticalMetadata: { name: '', description: '', type: '' },
        nonCriticalMetadata: { tags: '', notes: '' }
      });
      
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
      */
      
    } catch (error) {
      console.error('Upload error:', error);
      let errorMessage = 'Upload failed';
      
      if (error?.message) {
        errorMessage = error.message;
      } else if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error?.response?.status === 401) {
        errorMessage = 'Authentication failed - please reconnect your wallet';
      } else if (error?.response?.status === 400) {
        errorMessage = 'Invalid request - please check your input data';
      } else if (error?.response?.status >= 500) {
        errorMessage = 'Server error - please try again later';
      }
      
      setError(errorMessage);
      setIsLoading(false);
    }
  };

  return (
    <div className="upload-form-container">
      <form onSubmit={handleSubmit} className="upload-form">
        <h2>Upload Asset Metadata</h2>
        
        {error && (
          <div className="error-alert">
            <p>{error}</p>
          </div>
        )}

        <div className="form-group">
          <label htmlFor="assetId">Asset ID *</label>
          <input
            id="assetId"
            type="text"
            value={formData.assetId}
            onChange={(e) => handleInputChange('assetId', e.target.value)}
            placeholder="Enter unique asset identifier"
            required
            disabled={isLoading}
          />
        </div>

        <div className="form-section">
          <h3>Critical Metadata</h3>
          <p className="section-description">
            This data will be stored on IPFS and tracked on the blockchain
          </p>

          <div className="form-group">
            <label htmlFor="name">Name *</label>
            <input
              id="name"
              type="text"
              value={formData.criticalMetadata.name}
              onChange={(e) => handleInputChange('criticalMetadata.name', e.target.value)}
              placeholder="Asset name"
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={formData.criticalMetadata.description}
              onChange={(e) => handleInputChange('criticalMetadata.description', e.target.value)}
              placeholder="Asset description"
              rows={3}
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="type">Type</label>
            <select
              id="type"
              value={formData.criticalMetadata.type}
              onChange={(e) => handleInputChange('criticalMetadata.type', e.target.value)}
              disabled={isLoading}
            >
              <option value="">Select type</option>
              <option value="document">Document</option>
              <option value="image">Image</option>
              <option value="video">Video</option>
              <option value="audio">Audio</option>
              <option value="data">Data</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <div className="form-section">
          <h3>Non-Critical Metadata</h3>
          <p className="section-description">
            This data will be stored in the database only
          </p>

          <div className="form-group">
            <label htmlFor="tags">Tags</label>
            <input
              id="tags"
              type="text"
              value={formData.nonCriticalMetadata.tags}
              onChange={(e) => handleInputChange('nonCriticalMetadata.tags', e.target.value)}
              placeholder="tag1, tag2, tag3"
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              value={formData.nonCriticalMetadata.notes}
              onChange={(e) => handleInputChange('nonCriticalMetadata.notes', e.target.value)}
              placeholder="Additional notes"
              rows={2}
              disabled={isLoading}
            />
          </div>
        </div>

        <div className="form-actions">
          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={isLoading || !user?.walletAddress}
          >
            {isLoading ? 'Processing...' : 'Upload Metadata'}
          </button>
          
          {!user?.walletAddress && (
            <p className="wallet-warning">
              Please connect your wallet to upload metadata
            </p>
          )}
        </div>
      </form>

      {/* Transaction Signer Modal */}
      <TransactionSigner
        operation={operation}
        operationData={operationData}
        onSuccess={onSuccess}
        onError={onError}
        onCancel={hideSigner}
        isVisible={isVisible}
      />

      <style jsx>{`
        .upload-form-container {
          max-width: 600px;
          margin: 0 auto;
          padding: 20px;
        }

        .upload-form {
          background: white;
          padding: 30px;
          border-radius: 8px;
          box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        .upload-form h2 {
          margin-top: 0;
          margin-bottom: 24px;
          color: #333;
        }

        .error-alert {
          background-color: #f8d7da;
          border: 1px solid #f5c6cb;
          color: #721c24;
          padding: 12px 16px;
          border-radius: 4px;
          margin-bottom: 20px;
        }

        .error-alert p {
          margin: 0;
        }

        .form-section {
          margin-bottom: 30px;
          padding-bottom: 20px;
          border-bottom: 1px solid #e9ecef;
        }

        .form-section:last-of-type {
          border-bottom: none;
        }

        .form-section h3 {
          margin: 0 0 8px 0;
          color: #495057;
          font-size: 18px;
        }

        .section-description {
          margin: 0 0 20px 0;
          color: #6c757d;
          font-size: 14px;
          font-style: italic;
        }

        .form-group {
          margin-bottom: 20px;
        }

        .form-group label {
          display: block;
          margin-bottom: 6px;
          font-weight: 500;
          color: #495057;
        }

        .form-group input,
        .form-group textarea,
        .form-group select {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid #ced4da;
          border-radius: 4px;
          font-size: 14px;
          transition: border-color 0.2s;
        }

        .form-group input:focus,
        .form-group textarea:focus,
        .form-group select:focus {
          outline: none;
          border-color: #007bff;
          box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
        }

        .form-group input:disabled,
        .form-group textarea:disabled,
        .form-group select:disabled {
          background-color: #e9ecef;
          opacity: 0.6;
        }

        .form-actions {
          margin-top: 30px;
          text-align: center;
        }

        .btn {
          padding: 12px 24px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
          font-size: 16px;
          transition: background-color 0.2s;
        }

        .btn-primary {
          background-color: #007bff;
          color: white;
        }

        .btn-primary:hover:not(:disabled) {
          background-color: #0056b3;
        }

        .btn:disabled {
          background-color: #6c757d;
          cursor: not-allowed;
          opacity: 0.6;
        }

        .wallet-warning {
          margin-top: 12px;
          color: #dc3545;
          font-size: 14px;
          font-style: italic;
        }
      `}</style>
    </div>
  );
};

export default UploadFormWithSigning;