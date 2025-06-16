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
import { useAuth } from '../contexts/AuthContext';
import { useAssets } from '../hooks/useAssets';
import { toast } from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

function AssetForm({ existingAsset = null }) {
  const { currentAccount } = useAuth();
  const { uploadMetadata, isUploading } = useAssets();
  const navigate = useNavigate();

  // Steps for the upload process
  const uploadSteps = [
    'Preparing upload',
    'Uploading to IPFS',
    'Waiting for signature',
    'Confirming transaction',
    'Storing to database'
  ];

  // Example templates
  const templates = [
    { name: 'Document', fields: { 'document_type': '', 'author': '', 'version': '', 'creation_date': '' } },
    { name: 'Artwork', fields: { 'artist': '', 'medium': '', 'dimensions': '', 'year_created': '' } },
    { name: 'Certificate', fields: { 'issuer': '', 'recipient': '', 'issue_date': '', 'expiration_date': '' } },
    { name: 'Custom', fields: {} }
  ];

  // State initialization function
  const getInitialFormData = () => ({
    assetId: existingAsset?.assetId || uuidv4(),
    walletAddress: currentAccount,
    criticalMetadata: {
      name: existingAsset?.criticalMetadata?.name || '',
      description: existingAsset?.criticalMetadata?.description || '',
      tags: existingAsset?.criticalMetadata?.tags || [],
      ...(existingAsset?.criticalMetadata ?
        Object.fromEntries(
          Object.entries(existingAsset.criticalMetadata).filter(
            ([key]) => !['name', 'description', 'tags'].includes(key)
          )
        ) : {}
      )
    },
    nonCriticalMetadata: existingAsset?.nonCriticalMetadata || {}
  });

  // Initialize form state
  const [formData, setFormData] = useState(getInitialFormData);
  const [selectedTemplate, setSelectedTemplate] = useState('Custom');
  const [newTag, setNewTag] = useState('');
  const [uploadStep, setUploadStep] = useState(0);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [criticalFieldName, setCriticalFieldName] = useState('');
  const [criticalFieldValue, setCriticalFieldValue] = useState('');
  const [nonCriticalFieldName, setNonCriticalFieldName] = useState('');
  const [nonCriticalFieldValue, setNonCriticalFieldValue] = useState('');

  // Update form data when existingAsset changes
  useEffect(() => {
    if (existingAsset) {
      const newFormData = getInitialFormData();
      setFormData(newFormData);

      // Set template based on existing asset structure
      if (existingAsset.criticalMetadata) {
        const assetFields = Object.keys(existingAsset.criticalMetadata);
        const matchingTemplate = templates.find(template => {
          const templateFields = Object.keys(template.fields);
          return templateFields.some(field => assetFields.includes(field));
        });

        if (matchingTemplate) {
          setSelectedTemplate(matchingTemplate.name);
        }
      }
    }
  }, [existingAsset, currentAccount]);

  // Handle upload progress
  useEffect(() => {
    let progressInterval;

    if (isUploading) {
      setUploadProgress(0);
      setUploadStep(0);

      progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = prev + 1;
          const stepsCount = uploadSteps.length;
          const progressPerStep = 100 / stepsCount;

          // Change steps at appropriate thresholds
          for (let i = 1; i < stepsCount; i++) {
            if (newProgress >= i * progressPerStep && newProgress < (i + 1) * progressPerStep) {
              setUploadStep(i);
            }
          }

          return newProgress < 99 ? newProgress : 99;
        });
      }, 350);
    } else {
      clearInterval(progressInterval);
      setUploadProgress(0);
      setUploadStep(0);
    }

    return () => clearInterval(progressInterval);
  }, [isUploading, uploadSteps.length]);

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

  // Handle form submission
  const handleSubmit = (event) => {
    event.preventDefault();

    if (!formData.criticalMetadata.name) {
      toast.error('Asset name is required');
      return;
    }

    uploadMetadata(formData, {
      onSuccess: () => {
        setTimeout(() => {
          navigate('/dashboard');
        }, 1000);
      }
    });
  };

  return (
    <Paper sx={{ p: 3, position: 'relative' }}>
      <Typography variant="h5" gutterBottom>
        {existingAsset ? 'Edit Asset' : 'Create New Asset'}
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
                </Box>
              </Tooltip>
            </Box>

            {/* Template Selector */}
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Template</InputLabel>
              <Select
                value={selectedTemplate}
                label="Template"
                onChange={handleTemplateChange}
              >
                {templates.map((template) => (
                  <MenuItem key={template.name} value={template.name}>
                    {template.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Critical Metadata Fields */}
            {Object.entries(formData.criticalMetadata).map(([key, value]) => (
              <Box key={key} sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <TextField
                  label="Field Name"
                  value={key}
                  onChange={(e) => handleMetadataKeyChange('critical', key, e.target.value)}
                  sx={{ mr: 2, minWidth: 200 }}
                />
                <TextField
                  label="Value"
                  value={value}
                  onChange={(e) => handleMetadataValueChange('critical', key, e.target.value)}
                  sx={{ flexGrow: 1, mr: 1 }}
                />
                <IconButton 
                  onClick={() => removeMetadataField('critical', key)}
                  color="error"
                  size="small"
                >
                  <CloseIcon />
                </IconButton>
              </Box>
            ))}

            <Button
              startIcon={<AddIcon />}
              onClick={() => addMetadataField('critical')}
              variant="outlined"
              size="small"
              sx={{ mt: 1 }}
            >
              Add Critical Field
            </Button>
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          {/* Non-Critical Metadata Section */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Non-Critical Metadata
              </Typography>

              <Tooltip title="Non-critical metadata are stored only in our database and are not verified during retrieval.">
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <InfoIcon fontSize="small" color="info" sx={{ mr: 1 }} />
                  <Typography variant="caption" color="text.secondary">
                    Standard Security
                  </Typography>
                </Box>
              </Tooltip>
            </Box>

            {/* Non-Critical Metadata Fields */}
            {Object.entries(formData.nonCriticalMetadata).map(([key, value]) => (
              <Box key={key} sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <TextField
                  label="Field Name"
                  value={key}
                  onChange={(e) => handleMetadataKeyChange('nonCritical', key, e.target.value)}
                  sx={{ mr: 2, minWidth: 200 }}
                />
                <TextField
                  label="Value"
                  value={value}
                  onChange={(e) => handleMetadataValueChange('nonCritical', key, e.target.value)}
                  sx={{ flexGrow: 1, mr: 1 }}
                />
                <IconButton 
                  onClick={() => removeMetadataField('nonCritical', key)}
                  color="error"
                  size="small"
                >
                  <CloseIcon />
                </IconButton>
              </Box>
            ))}

            <Button
              startIcon={<AddIcon />}
              onClick={() => addMetadataField('nonCritical')}
              variant="outlined"
              size="small"
              sx={{ mt: 1 }}
            >
              Add Non-Critical Field
            </Button>
          </Grid>

          {/* Submit Button */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={isUploading || Object.keys(formData.criticalMetadata).length === 0}
                startIcon={isUploading ? <CircularProgress size={20} /> : null}
              >
                {isUploading ? 'Processing...' : (existingAsset ? 'Update Asset' : 'Create Asset')}
              </Button>
            </Box>
          </Grid>
        </Grid>
      </form>
    </Paper>
  );
}

export default AssetForm;
