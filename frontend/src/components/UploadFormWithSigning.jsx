import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  CircularProgress,
  LinearProgress,
  Grid,
  Chip,
  IconButton,
  Divider,
  Alert,
  MenuItem,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  Tooltip
} from '@mui/material';
import {
  Add as AddIcon,
  Close as CloseIcon,
  Info as InfoIcon,
  HelpOutline,
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material';
import { v4 as uuidv4 } from 'uuid';
import { useTransactionSigner } from '../hooks/useTransactionSigner';
import TransactionSigner from './TransactionSigner';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';

const UploadFormWithSigning = ({ onUploadSuccess }) => {
  const { currentAccount, isAuthenticated } = useAuth();


  // Example templates
  const templates = [
    { name: 'Document', fields: { 'document_type': '', 'author': '', 'version': '', 'creation_date': '' } },
    { name: 'Artwork', fields: { 'artist': '', 'medium': '', 'dimensions': '', 'year_created': '' } },
    { name: 'Certificate', fields: { 'issuer': '', 'recipient': '', 'issue_date': '', 'expiration_date': '' } },
    { name: 'Custom', fields: {} }
  ];

  // State initialization function
  const getInitialFormData = () => ({
    assetId: uuidv4(),
    walletAddress: currentAccount,
    criticalMetadata: {
      name: '',
      description: '',
      tags: []
    },
    nonCriticalMetadata: {}
  });

  // Initialize form state
  const [formData, setFormData] = useState(getInitialFormData);
  const [selectedTemplate, setSelectedTemplate] = useState('Custom');
  const [newTag, setNewTag] = useState('');
  const [criticalFieldName, setCriticalFieldName] = useState('');
  const [criticalFieldValue, setCriticalFieldValue] = useState('');
  const [nonCriticalFieldName, setNonCriticalFieldName] = useState('');
  const [nonCriticalFieldValue, setNonCriticalFieldValue] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const {
    isVisible,
    operation,
    operationData,
    showUploadSigner,
    hideSigner,
    onSuccess,
    onError
  } = useTransactionSigner();

  // Update form data when currentAccount changes
  useEffect(() => {
    setFormData(prev => ({
      ...prev,
      walletAddress: currentAccount
    }));
  }, [currentAccount]);


  // Handle form field changes for critical metadata
  const handleCriticalMetadataChange = (field) => (event) => {
    setFormData({
      ...formData,
      criticalMetadata: {
        ...formData.criticalMetadata,
        [field]: event.target.value
      }
    });
  };

  // Handle adding a new tag
  const handleAddTag = () => {
    if (newTag.trim() === '') return;

    setFormData({
      ...formData,
      criticalMetadata: {
        ...formData.criticalMetadata,
        tags: [...(formData.criticalMetadata.tags || []), newTag.trim()]
      }
    });

    setNewTag('');
  };

  // Handle removing a tag
  const handleRemoveTag = (tagToRemove) => {
    setFormData({
      ...formData,
      criticalMetadata: {
        ...formData.criticalMetadata,
        tags: formData.criticalMetadata.tags.filter(tag => tag !== tagToRemove)
      }
    });
  };

  // Handle adding a custom field to non-critical metadata
  const handleAddCustomField = () => {
    if (nonCriticalFieldName.trim() === '') return;

    setFormData({
      ...formData,
      nonCriticalMetadata: {
        ...formData.nonCriticalMetadata,
        [nonCriticalFieldName.trim()]: nonCriticalFieldValue
      }
    });

    setNonCriticalFieldName('');
    setNonCriticalFieldValue('');
  };

  // Handle removing a custom field
  const handleRemoveCustomField = (fieldName) => {
    const updatedMetadata = { ...formData.nonCriticalMetadata };
    delete updatedMetadata[fieldName];

    setFormData({
      ...formData,
      nonCriticalMetadata: updatedMetadata
    });
  };

  // Apply a template
  const applyTemplate = (templateName) => {
    const template = templates.find(t => t.name === templateName);
    if (!template) return;

    setSelectedTemplate(templateName);

    if (templateName === 'Custom') {
      setFormData(prev => ({
        ...prev,
        criticalMetadata: {
          name: prev.criticalMetadata.name || '',
          description: prev.criticalMetadata.description || '',
          tags: prev.criticalMetadata.tags || []
        }
      }));
      return;
    }

    // Add template fields to critical metadata
    setFormData(prev => ({
      ...prev,
      criticalMetadata: {
        name: prev.criticalMetadata.name || '',
        description: prev.criticalMetadata.description || '',
        tags: prev.criticalMetadata.tags || [],
        ...template.fields
      }
    }));
  };


  // Form validation
  const validateForm = () => {
    const errors = [];
    
    if (!currentAccount) {
      errors.push('Please connect your wallet first');
    }
    
    if (!formData.assetId?.trim()) {
      errors.push('Asset ID is required');
    } 
    
    if (!formData.criticalMetadata.name?.trim()) {
      errors.push('Asset name is required');
    } else if (formData.criticalMetadata.name.length > 100) {
      errors.push('Asset name must be 100 characters or less');
    }
    
    if (formData.criticalMetadata.description && formData.criticalMetadata.description.length > 500) {
      errors.push('Description must be 500 characters or less');
    }
    
    return errors;
  };

  // Handle form submission
  const handleSubmit = (event) => {
    event.preventDefault();

    const validationErrors = validateForm();
    if (validationErrors.length > 0) {
      toast.error(validationErrors.join('. '));
      return;
    }

    setIsUploading(true);

    // Prepare upload data
    const uploadData = {
      assetId: formData.assetId,
      walletAddress: currentAccount,
      criticalMetadata: formData.criticalMetadata,
      nonCriticalMetadata: formData.nonCriticalMetadata
    };

    // Show transaction signer for upload
    showUploadSigner(
      uploadData,
      (result) => {
        console.log('Upload successful:', result);
        setIsUploading(false);
        hideSigner();
        
        // Reset form for next asset
        setFormData(getInitialFormData());
        setSelectedTemplate('Custom');
        
        if (onUploadSuccess) {
          onUploadSuccess(result);
        }
      },
      (error) => {
        console.error('Upload failed:', error);
        setIsUploading(false);
        
        let errorMessage = 'Upload failed';
        if (error?.message) {
          errorMessage = error.message;
        }
        
        toast.error(errorMessage);
      }
    );
  };

  // Show wallet connection warning if not connected
  if (!isAuthenticated || !currentAccount) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Please connect and authenticate your wallet to create assets.
        </Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3, position: 'relative' }}>

      <Typography variant="h5" gutterBottom>
        Create New Asset
      </Typography>

      <form onSubmit={handleSubmit}>
        <Grid container spacing={3}>
          {/* Asset ID (readonly) */}
          <Grid item xs={12}>
            <TextField
              label="Asset ID"
              value={formData.assetId}
              fullWidth
              disabled
              helperText="Asset ID is automatically generated and cannot be changed"
            />
          </Grid>

          {/* Critical Metadata Section */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Critical Metadata
              </Typography>

              <Tooltip title="During retrieval, critical metadata undergo a strict verification process to ensure their authenticity.">
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <HelpOutline fontSize="small" color="primary" sx={{ mr: 1 }} />
                  <Typography variant="caption" color="text.secondary">
                    High Security
                  </Typography>
                </Box>
              </Tooltip>
            </Box>

            <Alert severity="info" sx={{ mb: 2 }}>
              Metadata can be considered critical if they define your asset. Note that modifying these in the future take longer to process.
            </Alert>

            {/* Template selection */}
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Metadata Template</InputLabel>
              <Select
                value={selectedTemplate}
                label="Metadata Template"
                onChange={(e) => applyTemplate(e.target.value)}
              >
                {templates.map((template) => (
                  <MenuItem key={template.name} value={template.name}>
                    {template.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  label="Name"
                  value={formData.criticalMetadata.name}
                  onChange={handleCriticalMetadataChange('name')}
                  fullWidth
                  required
                />
              </Grid>

              <Grid item xs={12}>
                <TextField
                  label="Description"
                  value={formData.criticalMetadata.description}
                  onChange={handleCriticalMetadataChange('description')}
                  fullWidth
                  multiline
                  rows={3}
                />
              </Grid>

              {/* Display all custom critical metadata fields */}
              {Object.entries(formData.criticalMetadata).filter(([key]) =>
                !['name', 'description', 'tags'].includes(key)
              ).map(([key, value]) => (
                <Grid item xs={12} sm={6} key={key}>
                  <TextField
                    label={key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    value={value}
                    onChange={handleCriticalMetadataChange(key)}
                    fullWidth
                  />
                </Grid>
              ))}

              {/* Custom critical field addition */}
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1, mt: 1 }}>
                  <TextField
                    label="New Field Name"
                    value={criticalFieldName}
                    onChange={(e) => setCriticalFieldName(e.target.value)}
                    size="small"
                    sx={{ flexGrow: 1 }}
                  />

                  <TextField
                    label="Value"
                    value={criticalFieldValue}
                    onChange={(e) => setCriticalFieldValue(e.target.value)}
                    size="small"
                    sx={{ flexGrow: 1 }}
                  />

                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => {
                      if (!criticalFieldName.trim()) return;
                      setFormData({
                        ...formData,
                        criticalMetadata: {
                          ...formData.criticalMetadata,
                          [criticalFieldName.trim()]: criticalFieldValue
                        }
                      });
                      setCriticalFieldName('');
                      setCriticalFieldValue('');
                    }}
                    size="small"
                  >
                    Add
                  </Button>
                </Box>
              </Grid>

              {/* Tags input */}
              <Grid item xs={12}>
                <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                  Tags
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <TextField
                    label="Add Tag"
                    value={newTag}
                    onChange={(e) => setNewTag(e.target.value)}
                    fullWidth
                    size="small"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddTag();
                      }
                    }}
                  />
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleAddTag}
                    sx={{ ml: 1 }}
                    size="small"
                  >
                    Add
                  </Button>
                </Box>

                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                  {formData.criticalMetadata.tags?.map((tag, index) => (
                    <Chip
                      key={index}
                      label={tag}
                      onDelete={() => handleRemoveTag(tag)}
                      size="small"
                    />
                  ))}
                </Box>
              </Grid>
            </Grid>
          </Grid>

          {/* Non-Critical Metadata Section */}
          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Non-Critical Metadata
              </Typography>

              <Tooltip title="Non-critical metadata go through standard security procedures, allowing for faster updates and modifications.">
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <HelpOutline fontSize="small" color="secondary" sx={{ mr: 1 }} />
                  <Typography variant="caption" color="text.secondary">
                    Standard Security
                  </Typography>
                </Box>
              </Tooltip>
            </Box>

            <Alert severity="info" sx={{ mb: 2 }}>
              Non-critical metadata include supplementary information that can be quickly updated. These can be modified with fewer computational resources.
            </Alert>

            {/* Custom fields */}
            <Box sx={{ mb: 2 }}>
              {Object.entries(formData.nonCriticalMetadata).map(([key, value]) => (
                <Box key={key} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <TextField
                    label={key}
                    value={value}
                    onChange={(e) => setFormData({
                      ...formData,
                      nonCriticalMetadata: {
                        ...formData.nonCriticalMetadata,
                        [key]: e.target.value
                      }
                    })}
                    fullWidth
                    size="small"
                  />
                  <IconButton
                    onClick={() => handleRemoveCustomField(key)}
                    color="error"
                    size="small"
                  >
                    <CloseIcon />
                  </IconButton>
                </Box>
              ))}
            </Box>

            {/* Add custom field */}
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
              <TextField
                label="Field Name"
                value={nonCriticalFieldName}
                onChange={(e) => setNonCriticalFieldName(e.target.value)}
                size="small"
                sx={{ flexGrow: 1 }}
              />
              <TextField
                label="Value"
                value={nonCriticalFieldValue}
                onChange={(e) => setNonCriticalFieldValue(e.target.value)}
                size="small"
                sx={{ flexGrow: 1 }}
              />
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleAddCustomField}
                sx={{ mt: 1 }}
                size="small"
              >
                Add
              </Button>
            </Box>
          </Grid>

          {/* Submit Button */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                disabled={isUploading || !isAuthenticated || !currentAccount}
                sx={{ minWidth: 120 }}
                size="large"
              >
                {isUploading ? (
                  <CircularProgress size={24} />
                ) : (
                  'Create Asset'
                )}
              </Button>
            </Box>
          </Grid>
        </Grid>
      </form>

      {/* Transaction Signer Modal */}
      <TransactionSigner
        operation={operation}
        operationData={operationData}
        onSuccess={onSuccess}
        onError={onError}
        onCancel={() => {
          // Reset uploading state when modal is cancelled
          setIsUploading(false);
          hideSigner();
        }}
        isVisible={isVisible}
      />
    </Paper>
  );
};

export default UploadFormWithSigning;