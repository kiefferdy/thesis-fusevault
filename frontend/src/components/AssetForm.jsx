import { useState, useEffect } from 'react';
import { 
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  CircularProgress,
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
import { useAuth } from '../contexts/AuthContext';
import { useAssets } from '../hooks/useAssets';
import { toast } from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

function AssetForm({ existingAsset = null }) {
  const { currentAccount } = useAuth();
  const { uploadMetadata, isUploading } = useAssets();
  const navigate = useNavigate();
  
  // Additional state for metadata templates and custom fields
  const [newTag, setNewTag] = useState('');
  const [fieldType, setFieldType] = useState('text');
  const [uploadStep, setUploadStep] = useState(0);
  const [uploadProgress, setUploadProgress] = useState(0);
  
  // Steps for the upload process
  const uploadSteps = ['Preparing data', 'Uploading to IPFS', 'Storing on blockchain', 'Finalizing'];
  
  // Common field types
  const fieldTypes = [
    { value: 'text', label: 'Text' },
    { value: 'number', label: 'Number' },
    { value: 'date', label: 'Date' },
    { value: 'url', label: 'URL' },
    { value: 'email', label: 'Email' },
    { value: 'boolean', label: 'Yes/No' }
  ];
  
  // Example templates
  const templates = [
    { name: 'Document', fields: { 'document_type': '', 'author': '', 'version': '', 'creation_date': '' } },
    { name: 'Artwork', fields: { 'artist': '', 'medium': '', 'dimensions': '', 'year_created': '' } },
    { name: 'Certificate', fields: { 'issuer': '', 'recipient': '', 'issue_date': '', 'expiration_date': '' } },
    { name: 'Custom', fields: {} }
  ];
  
  // Initialize form state based on existing asset or with defaults
  const [formData, setFormData] = useState({
    assetId: existingAsset?.assetId || uuidv4(),
    walletAddress: currentAccount,
    criticalMetadata: {
      name: existingAsset?.criticalMetadata?.name || '',
      description: existingAsset?.criticalMetadata?.description || '',
      tags: existingAsset?.criticalMetadata?.tags || [],
      ...existingAsset?.criticalMetadata
    },
    nonCriticalMetadata: existingAsset?.nonCriticalMetadata || {}
  });
  
  // Selected template
  const [selectedTemplate, setSelectedTemplate] = useState('Custom');
  
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
    
    if (!formData.criticalMetadata.tags) {
      formData.criticalMetadata.tags = [];
    }
    
    setFormData({
      ...formData,
      criticalMetadata: {
        ...formData.criticalMetadata,
        tags: [...formData.criticalMetadata.tags, newTag.trim()]
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

  // Fields for critical and non-critical metadata
  const [criticalFieldName, setCriticalFieldName] = useState('');
  const [criticalFieldValue, setCriticalFieldValue] = useState('');
  const [nonCriticalFieldName, setNonCriticalFieldName] = useState('');
  const [nonCriticalFieldValue, setNonCriticalFieldValue] = useState('');

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
      // Reset to just the basic fields for custom template
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
        // Keep basic fields
        name: prev.criticalMetadata.name || '',
        description: prev.criticalMetadata.description || '',
        tags: prev.criticalMetadata.tags || [],
        // Add template fields
        ...template.fields
      }
    }));
  };
  
  // Effect to update progress simulation
  useEffect(() => {
    let progressInterval;
    
    if (isUploading) {
      setUploadProgress(0);
      setUploadStep(0);
      
      progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = prev + 1;
          
          // Change steps at certain thresholds
          if (newProgress === 25) setUploadStep(1);
          if (newProgress === 50) setUploadStep(2);
          if (newProgress === 75) setUploadStep(3);
          
          return newProgress < 99 ? newProgress : 99;
        });
      }, 150);
    } else {
      // When upload completes or fails
      clearInterval(progressInterval);
    }
    
    return () => clearInterval(progressInterval);
  }, [isUploading]);
  
  // Handle form submission
  const handleSubmit = (event) => {
    event.preventDefault();
    
    if (!formData.criticalMetadata.name) {
      toast.error('Asset name is required');
      return;
    }
    
    try {
      uploadMetadata(formData, {
        onSuccess: () => {
          // Show 100% completion
          setUploadProgress(100);
          
          // Navigate to dashboard after a moment
          setTimeout(() => {
            navigate('/dashboard');
          }, 1000);
        }
      });
    } catch (error) {
      toast.error(`Error: ${error.message}`);
    }
  };

  return (
    <Paper sx={{ p: 3, position: 'relative' }}>
      {/* Upload progress overlay */}
      {isUploading && (
        <Box sx={{ 
          position: 'absolute', 
          top: 0, 
          left: 0, 
          right: 0, 
          bottom: 0, 
          bgcolor: 'rgba(255,255,255,0.9)', 
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 1
        }}>
          <Card sx={{ maxWidth: 400, mb: 3, p: 3, boxShadow: 3 }}>
            <CardContent>
              <Typography variant="h6" color="primary" gutterBottom textAlign="center">
                {uploadProgress === 100 ? 'Upload Complete!' : 'Uploading Asset'}
              </Typography>
              
              <Box sx={{ mb: 3, mt: 2 }}>
                {uploadProgress < 100 ? (
                  <Box sx={{ width: '100%' }}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {uploadSteps[uploadStep]}
                    </Typography>
                    <Box sx={{ width: '100%', mr: 1 }}>
                      <LinearProgress 
                        variant="determinate" 
                        value={uploadProgress} 
                        sx={{ height: 10, borderRadius: 5 }}
                      />
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                      <Typography variant="body2" color="text.secondary">
                        {uploadProgress}%
                      </Typography>
                    </Box>
                  </Box>
                ) : (
                  <Box sx={{ textAlign: 'center' }}>
                    <CheckCircleIcon color="success" sx={{ fontSize: 60, mb: 2 }} />
                    <Typography>Redirecting to dashboard...</Typography>
                  </Box>
                )}
              </Box>
              
              <Typography variant="caption" color="text.secondary" textAlign="center" display="block">
                This process can take a few minutes. Please don't close this window.
              </Typography>
            </CardContent>
          </Card>
        </Box>
      )}
      
      <Typography variant="h5" gutterBottom>
        {existingAsset ? 'Edit Asset' : 'Create New Asset'}
      </Typography>
      
      <form onSubmit={handleSubmit}>
        <Grid container spacing={3}>
          {/* Asset ID (readonly if editing) */}
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
              
              <Tooltip title="This data is highly secured and cannot be modified once created">
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <HelpOutline fontSize="small" color="primary" sx={{ mr: 1 }} />
                  <Typography variant="caption" color="text.secondary">
                    High Security
                  </Typography>
                </Box>
              </Tooltip>
            </Box>
            
            <Alert severity="info" sx={{ mb: 2 }}>
              Critical metadata is essential for asset identification and cannot be modified after creation. Choose a template or define custom fields.
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
                    size="medium"
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
              
              <Tooltip title="This data can be updated in the future and has standard security">
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <HelpOutline fontSize="small" color="secondary" sx={{ mr: 1 }} />
                  <Typography variant="caption" color="text.secondary">
                    Standard Security
                  </Typography>
                </Box>
              </Tooltip>
            </Box>
            
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
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={handleAddCustomField}
                sx={{ mt: 1 }}
                size="small"
              >
                Add Field
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
                disabled={isUploading}
                sx={{ minWidth: 120 }}
                size="large"
              >
                {isUploading ? (
                  <CircularProgress size={24} />
                ) : existingAsset ? (
                  'Update Asset'
                ) : (
                  'Create Asset'
                )}
              </Button>
            </Box>
          </Grid>
        </Grid>
      </form>
    </Paper>
  );
}

export default AssetForm;