import { useState } from 'react';
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
  Divider
} from '@mui/material';
import { Add as AddIcon, Close as CloseIcon } from '@mui/icons-material';
import { v4 as uuidv4 } from 'uuid';
import { useAuth } from '../contexts/AuthContext';
import { useAssets } from '../hooks/useAssets';
import { toast } from 'react-hot-toast';

function AssetForm({ existingAsset = null }) {
  const { currentAccount } = useAuth();
  const { uploadMetadata, isUploading } = useAssets();
  
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

  // Extra state for tag input
  const [newTag, setNewTag] = useState('');
  
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

  // Handle adding a custom field to non-critical metadata
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldValue, setNewFieldValue] = useState('');

  const handleAddCustomField = () => {
    if (newFieldName.trim() === '') return;
    
    setFormData({
      ...formData,
      nonCriticalMetadata: {
        ...formData.nonCriticalMetadata,
        [newFieldName.trim()]: newFieldValue
      }
    });
    
    setNewFieldName('');
    setNewFieldValue('');
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

  // Handle form submission
  const handleSubmit = (event) => {
    event.preventDefault();
    
    if (!formData.criticalMetadata.name) {
      toast.error('Asset name is required');
      return;
    }
    
    try {
      uploadMetadata(formData);
    } catch (error) {
      toast.error(`Error: ${error.message}`);
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
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
            <Typography variant="h6" gutterBottom>
              Critical Metadata (Stored on Blockchain)
            </Typography>
            
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
              
              {/* Tags input */}
              <Grid item xs={12}>
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
            <Typography variant="h6" gutterBottom>
              Additional Metadata (Not stored on blockchain)
            </Typography>
            
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
                value={newFieldName}
                onChange={(e) => setNewFieldName(e.target.value)}
                size="small"
                sx={{ flexGrow: 1 }}
              />
              <TextField
                label="Value"
                value={newFieldValue}
                onChange={(e) => setNewFieldValue(e.target.value)}
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