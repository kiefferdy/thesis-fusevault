import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  Button,
  CircularProgress,
  Divider,
  Chip,
  Alert,
  Card,
  CardContent,
  CardHeader,
  IconButton,
  LinearProgress,
  Tooltip,
  Fade,
  Zoom,
  useTheme,
  alpha,
  TextField,
  InputAdornment,
  Stack
} from '@mui/material';
import {
  Edit,
  Delete,
  ArrowBack,
  History,
  VerifiedUser,
  Warning,
  ContentCopy,
  Download,
  Check,
  Security,
  Storage,
  Schedule,
  Person,
  Fingerprint,
  Link as LinkIcon,
  Save,
  Cancel,
  Add,
  Remove,
  HelpOutline
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { assetService } from '../services/assetService';
import { useAssets } from '../hooks/useAssets';
import { useTransactionSigner } from '../hooks/useTransactionSigner';
import { useAuth } from '../contexts/AuthContext';
import TransactionSigner from '../components/TransactionSigner';
import { formatDate, formatWalletAddress, formatTransactionHash } from '../utils/formatters';

// Define EditableField component outside to prevent re-creation on every render
const EditableField = React.memo(({ label, value, onChange, onRemove, isCritical = false, theme, alpha }) => {
  const handleChange = React.useCallback((e) => {
    if (Array.isArray(value)) {
      onChange(label, e.target.value.split(', ').filter(item => item.trim()));
    } else {
      onChange(label, e.target.value);
    }
  }, [label, value, onChange]);

  const handleRemove = React.useCallback(() => {
    onRemove(label, isCritical);
  }, [label, isCritical, onRemove]);

  return (
    <Box 
      sx={{ 
        position: 'relative',
        p: 2,
        borderRadius: 2,
        backgroundColor: alpha(theme.palette.background.paper, 0.6),
        border: `2px solid ${alpha(theme.palette.primary.main, 0.3)}`,
        transition: 'all 0.2s ease-in-out'
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" sx={{ 
            fontWeight: 600, 
            color: theme.palette.text.secondary,
            mb: 1,
            textTransform: 'uppercase',
            fontSize: '0.75rem',
            letterSpacing: '0.5px'
          }}>
            {label}
          </Typography>
          {Array.isArray(value) ? (
            <TextField
              fullWidth
              multiline
              rows={2}
              variant="outlined"
              value={Array.isArray(value) ? value.join(', ') : value}
              onChange={handleChange}
              placeholder="Enter comma-separated values"
              size="small"
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontFamily: 'monospace',
                  fontSize: '0.875rem'
                }
              }}
            />
          ) : (
            <TextField
              fullWidth
              variant="outlined"
              value={value || ''}
              onChange={handleChange}
              size="small"
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontFamily: 'monospace',
                  fontSize: '0.875rem'
                }
              }}
            />
          )}
        </Box>
        <Tooltip title="Remove field">
          <IconButton
            onClick={handleRemove}
            sx={{
              color: theme.palette.error.main,
              '&:hover': {
                backgroundColor: alpha(theme.palette.error.main, 0.1),
              }
            }}
          >
            <Remove fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );
});

function AssetDetailPage() {
  const { assetId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [asset, setAsset] = useState(null);
  const [version] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recoveryStatus, setRecoveryStatus] = useState(null);
  const [recoveryMessage, setRecoveryMessage] = useState('Loading asset data...');
  const [progressPercent, setProgressPercent] = useState(0);
  const [copiedField, setCopiedField] = useState(null);
  
  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editedCriticalMetadata, setEditedCriticalMetadata] = useState({});
  const [editedNonCriticalMetadata, setEditedNonCriticalMetadata] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  
  // Delegation mode state
  const [isDelegateMode, setIsDelegateMode] = useState(false);
  const [originalOwner, setOriginalOwner] = useState(null);

  // Check for delegation parameters on component mount
  useEffect(() => {
    const delegateOwner = searchParams.get('delegate');
    if (delegateOwner) {
      setIsDelegateMode(true);
      setOriginalOwner(delegateOwner);
    }
  }, [searchParams]);
  
  // Tag management state
  const [newTag, setNewTag] = useState('');
  const { deleteAsset, isDeleting } = useAssets();
  const { currentAccount } = useAuth();
  const {
    isVisible: isTransactionVisible,
    operation: transactionOperation,
    operationData: transactionData,
    showDeleteSigner,
    showEditSigner,
    checkEditRequiresSignature,
    hideSigner,
    onSuccess: onTransactionSuccess,
    onError: onTransactionError
  } = useTransactionSigner();
  const navigate = useNavigate();
  const theme = useTheme();

  // Copy to clipboard functionality
  const handleCopyToClipboard = async (value, fieldName, displayName) => {
    try {
      const textValue = typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value);
      await navigator.clipboard.writeText(textValue);
      setCopiedField(fieldName);
      toast.success(`${displayName} copied to clipboard`);
      
      // Reset the copied state after 2 seconds
      setTimeout(() => {
        setCopiedField(null);
      }, 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      toast.error('Failed to copy to clipboard');
    }
  };

  // Export asset as JSON (batch upload format)
  const handleExportAsset = () => {
    try {
      const exportData = {
        assetId: asset.assetId,
        walletAddress: asset.walletAddress,
        criticalMetadata: asset.criticalMetadata,
        nonCriticalMetadata: asset.nonCriticalMetadata
      };

      const dataStr = JSON.stringify(exportData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `fusevault-asset-${asset.assetId}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      toast.success('Asset exported successfully');
    } catch (err) {
      console.error('Failed to export asset:', err);
      toast.error('Failed to export asset');
    }
  };

  // Handle real streaming progress from backend
  const handleStreamingProgress = (progressData) => {
    setRecoveryMessage(progressData.message);
    
    // Calculate progress percentage based on step
    const progress = (progressData.step / progressData.totalSteps) * 100;
    setProgressPercent(progress);
    
    if (progressData.completed) {
      if (progressData.error) {
        setError('Failed to load asset data. Please try again later.');
        setLoading(false);
      }
      setProgressPercent(100);
      // Note: completion with success will be handled in the onComplete callback
    }
  };

  // Fetch asset data
  useEffect(() => {
    let streamConnection = null;
    
    const fetchAsset = () => {
      setLoading(true);
      setRecoveryMessage('Loading asset data...');
      setRecoveryStatus(null);
      setError(null);
      setProgressPercent(0);
      
      // Try streaming first, with fallback to regular API
      streamConnection = assetService.retrieveMetadataStream(
        assetId,
        version,
        handleStreamingProgress,
        (assetData) => {
          // Success callback
          console.log('Asset data received via streaming:', assetData);
          
          // Check if recovery was performed
          if (assetData.verification && assetData.verification.recoveryNeeded) {
            setRecoveryStatus('recovered');
          }
          
          setAsset(assetData);
          setError(null);
          setLoading(false);
        },
        (error) => {
          // Error callback - fallback to regular API
          console.warn('Streaming failed, falling back to regular API:', error);
          fallbackToRegularAPI();
        }
      );
      
      // If streaming is not supported or fails immediately, fallback
      if (!streamConnection) {
        fallbackToRegularAPI();
      }
    };
    
    const fallbackToRegularAPI = async () => {
      try {
        setRecoveryMessage('Loading asset data...');
        const assetData = await assetService.retrieveMetadata(assetId, version);
        
        // Check if recovery was performed
        if (assetData.verification && assetData.verification.recoveryNeeded) {
          setRecoveryStatus('recovered');
          // For fallback, show a simple completion message
          if (assetData.verification.recoverySuccessful) {
            setRecoveryMessage('Asset metadata restored successfully');
          } else {
            setRecoveryMessage('Recovery failed - asset integrity could not be verified');
          }
        } else {
          setRecoveryMessage('Asset verified successfully');
        }
        
        setAsset(assetData);
        setError(null);
      } catch (err) {
        console.error('Error fetching asset:', err);
        setError('Failed to load asset data. Please try again later.');
        toast.error('Error loading asset data');
      } finally {
        setLoading(false);
      }
    };

    fetchAsset();
    
    // Cleanup function to close EventSource on component unmount
    return () => {
      if (streamConnection && streamConnection.close) {
        streamConnection.close();
      }
    };
  }, [assetId, version]);

  // Check for edit mode from URL parameter
  useEffect(() => {
    if (asset && searchParams.get('edit') === 'true' && !isEditing) {
      // Remove the edit parameter from URL to clean it up
      setSearchParams({});
      // Automatically enter edit mode
      setEditedCriticalMetadata({ ...asset.criticalMetadata });
      setEditedNonCriticalMetadata({ ...asset.nonCriticalMetadata });
      setIsEditing(true);
    }
  }, [asset, searchParams, isEditing, setSearchParams]);

  // Initialize edit state with current metadata
  const handleEditToggle = () => {
    if (!isEditing) {
      setEditedCriticalMetadata({ ...asset.criticalMetadata });
      setEditedNonCriticalMetadata({ ...asset.nonCriticalMetadata });
    }
    setIsEditing(!isEditing);
  };

  // Cancel editing and reset to original data
  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedCriticalMetadata({});
    setEditedNonCriticalMetadata({});
  };

  // Validate metadata before saving
  const validateMetadata = () => {
    const errors = [];
    
    // Check if critical metadata has required fields (name is required)
    if (!editedCriticalMetadata.name || editedCriticalMetadata.name.trim() === '') {
      errors.push('Asset name is required');
    }
    
    // Check for empty field names
    const allFields = [...Object.keys(editedCriticalMetadata), ...Object.keys(editedNonCriticalMetadata)];
    const emptyFields = allFields.filter(key => !key || key.trim() === '');
    if (emptyFields.length > 0) {
      errors.push('Field names cannot be empty');
    }
    
    // Check for duplicate field names between critical and non-critical
    const criticalKeys = Object.keys(editedCriticalMetadata);
    const nonCriticalKeys = Object.keys(editedNonCriticalMetadata);
    const duplicates = criticalKeys.filter(key => nonCriticalKeys.includes(key));
    if (duplicates.length > 0) {
      errors.push(`Duplicate field names found: ${duplicates.join(', ')}`);
    }
    
    return errors;
  };

  // Check if critical metadata has changed (client-side comparison)
  const hasCriticalMetadataChanged = (newCriticalMetadata, existingCriticalMetadata) => {
    if (!existingCriticalMetadata) return true;
    
    // Get all keys from both objects
    const newKeys = Object.keys(newCriticalMetadata || {});
    const existingKeys = Object.keys(existingCriticalMetadata || {});
    const allKeys = [...new Set([...newKeys, ...existingKeys])];
    
    // Compare each key
    for (const key of allKeys) {
      const newValue = newCriticalMetadata[key];
      const existingValue = existingCriticalMetadata[key];
      
      // Handle arrays (like tags)
      if (Array.isArray(newValue) && Array.isArray(existingValue)) {
        if (newValue.length !== existingValue.length) return true;
        if (!newValue.every((val, index) => val === existingValue[index])) return true;
      }
      // Handle other values
      else if (newValue !== existingValue) {
        return true;
      }
    }
    
    return false;
  };

  // Save edited metadata (follows the same pattern as the old edit page)
  const handleSaveEdit = async () => {
    try {
      setIsSaving(true);
      
      // Validate metadata before saving
      const validationErrors = validateMetadata();
      if (validationErrors.length > 0) {
        toast.error('Validation failed: ' + validationErrors.join(', '));
        return;
      }
      
      // Prepare upload data (same format as upload/edit)
      const uploadData = {
        assetId: assetId,
        walletAddress: currentAccount, // Current user signs the transaction
        criticalMetadata: editedCriticalMetadata,
        nonCriticalMetadata: editedNonCriticalMetadata
      };
      
      // Use the same edit flow as the old edit page
      // First, do a client-side check to determine if critical metadata changed
      const criticalMetadataChanged = hasCriticalMetadataChanged(uploadData.criticalMetadata, asset.criticalMetadata);
      
      if (criticalMetadataChanged) {
        // Critical metadata changed - show TransactionSigner modal immediately (no server call needed)
        console.log('Critical metadata changed, showing MetaMask signer');
        showEditSigner(
          uploadData,
          (result) => {
            console.log('Edit with signing successful:', result);
            setIsSaving(false);
            setIsEditing(false);
            
            // Refresh the asset data to show updated values
            window.location.reload(); // Simple way to refresh and get updated data
            
            toast.success('Asset updated successfully!');
          },
          (error) => {
            console.error('Edit with signing failed:', error);
            setIsSaving(false);
            
            let errorMessage = 'Edit failed';
            if (error?.message) {
              errorMessage = error.message;
            }
            
            toast.error(errorMessage);
          }
        );
      } else {
        // Only non-critical metadata changed - complete directly without modal
        console.log('Only non-critical metadata changed, uploading directly');
        try {
          const checkResult = await checkEditRequiresSignature(uploadData);
          console.log('checkEditRequiresSignature result:', checkResult);
          
          setIsSaving(false);
          setIsEditing(false);
          
          // Refresh the asset data to show updated values
          window.location.reload(); // Simple way to refresh and get updated data
          
          toast.success('Asset updated successfully! (Only non-critical metadata changed)');
        } catch (error) {
          console.error('Edit failed:', error);
          setIsSaving(false);
          
          let errorMessage = 'Edit failed';
          if (error?.message) {
            errorMessage = error.message;
          } else if (typeof error === 'string') {
            errorMessage = error;
          }
          
          toast.error(errorMessage);
        }
      }
    } catch (error) {
      console.error('Error in save process:', error);
      toast.error('Failed to save changes: ' + (error.message || 'Unknown error'));
      setIsSaving(false);
    }
  };

  // Handle metadata field changes - memoized to prevent re-renders
  const handleCriticalMetadataChange = useCallback((key, value) => {
    setEditedCriticalMetadata(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);

  const handleNonCriticalMetadataChange = useCallback((key, value) => {
    setEditedNonCriticalMetadata(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);

  // Add new metadata field
  const handleAddMetadataField = (isCritical) => {
    const key = prompt(`Enter new ${isCritical ? 'critical' : 'non-critical'} metadata field name:`);
    if (key && key.trim()) {
      if (isCritical) {
        handleCriticalMetadataChange(key.trim(), '');
      } else {
        handleNonCriticalMetadataChange(key.trim(), '');
      }
    }
  };

  // Remove metadata field - memoized to prevent re-renders
  const handleRemoveMetadataField = useCallback((key, isCritical) => {
    if (isCritical) {
      setEditedCriticalMetadata(prev => {
        const newData = { ...prev };
        delete newData[key];
        return newData;
      });
    } else {
      setEditedNonCriticalMetadata(prev => {
        const newData = { ...prev };
        delete newData[key];
        return newData;
      });
    }
  }, []);

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this asset?')) {
      showDeleteSigner(
        assetId,
        currentAccount,
        'User requested deletion',
        (result) => {
          console.log('Delete successful:', result);
          toast.success('Asset deleted successfully!');
          navigate('/dashboard');
        },
        (error) => {
          console.error('Delete failed:', error);
          let errorMessage = 'Delete failed';
          if (error?.message) {
            errorMessage = error.message;
          }
          toast.error(errorMessage);
        }
      );
    }
  };

  const handleBack = () => {
    // Check if we're viewing someone else's asset (delegation context)
    const isViewingOthersAsset = asset && asset.walletAddress && 
                                 currentAccount && 
                                 asset.walletAddress.toLowerCase() !== currentAccount.toLowerCase();
    
    if (isDelegateMode && originalOwner) {
      // Explicit delegation mode with URL parameter
      navigate(`/delegation/manage/${originalOwner}`);
    } else if (isViewingOthersAsset) {
      // Viewing someone else's asset (implicit delegation)
      navigate(`/delegation/manage/${asset.walletAddress}`);
    } else {
      navigate('/dashboard');
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Fade in={loading}>
          <Card sx={{ 
            maxWidth: 600, 
            mx: 'auto', 
            mt: 8,
            background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.secondary.main, 0.1)} 100%)`,
            backdropFilter: 'blur(10px)',
            borderRadius: 3,
            boxShadow: theme.shadows[10]
          }}>
            <CardContent sx={{ p: 4, textAlign: 'center' }}>
              <Box sx={{ position: 'relative', display: 'inline-flex', mb: 3 }}>
                <CircularProgress 
                  size={60} 
                  thickness={4}
                  sx={{ 
                    color: theme.palette.primary.main,
                    '& .MuiCircularProgress-circle': {
                      strokeLinecap: 'round',
                    }
                  }}
                />
                {progressPercent > 0 && (
                  <Box
                    sx={{
                      top: 0,
                      left: 0,
                      bottom: 0,
                      right: 0,
                      position: 'absolute',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Typography variant="caption" component="div" color="text.secondary">
                      {Math.round(progressPercent)}%
                    </Typography>
                  </Box>
                )}
              </Box>
              
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: theme.palette.text.primary }}>
                Loading Asset
              </Typography>
              
              <Typography variant="body1" sx={{ mb: 2, color: theme.palette.text.secondary }}>
                {recoveryMessage}
              </Typography>
              
              {progressPercent > 0 && (
                <Box sx={{ width: '100%', mb: 2 }}>
                  <LinearProgress 
                    variant="determinate" 
                    value={progressPercent}
                    sx={{
                      height: 6,
                      borderRadius: 3,
                      backgroundColor: alpha(theme.palette.primary.main, 0.2),
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 3,
                        background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`
                      }
                    }}
                  />
                </Box>
              )}
              
              {recoveryStatus === 'recovered' && (
                <Alert 
                  severity="info" 
                  sx={{ 
                    mt: 2,
                    borderRadius: 2,
                    '& .MuiAlert-icon': {
                      color: theme.palette.info.main
                    }
                  }}
                >
                  Ensuring data integrity - this may take a moment...
                </Alert>
              )}
            </CardContent>
          </Card>
        </Fade>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Fade in={!!error}>
          <Card sx={{ 
            maxWidth: 500, 
            mx: 'auto', 
            mt: 8,
            borderRadius: 3,
            boxShadow: theme.shadows[8]
          }}>
            <CardContent sx={{ p: 4, textAlign: 'center' }}>
              <Warning sx={{ fontSize: 60, color: theme.palette.error.main, mb: 2 }} />
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Error Loading Asset
              </Typography>
              <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
                {error}
              </Alert>
              <Button 
                variant="contained" 
                onClick={handleBack}
                startIcon={<ArrowBack />}
                sx={{ borderRadius: 2 }}
              >
Back to Dashboard
              </Button>
            </CardContent>
          </Card>
        </Fade>
      </Container>
    );
  }

  if (!asset) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Fade in={!asset}>
          <Card sx={{ 
            maxWidth: 500, 
            mx: 'auto', 
            mt: 8,
            borderRadius: 3,
            boxShadow: theme.shadows[8]
          }}>
            <CardContent sx={{ p: 4, textAlign: 'center' }}>
              <Security sx={{ fontSize: 60, color: theme.palette.warning.main, mb: 2 }} />
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Asset Not Found
              </Typography>
              <Alert severity="warning" sx={{ mb: 3, borderRadius: 2 }}>
                The requested asset could not be found or you don't have permission to view it.
              </Alert>
              <Button 
                variant="contained" 
                onClick={handleBack}
                startIcon={<ArrowBack />}
                sx={{ borderRadius: 2 }}
              >
Back to Dashboard
              </Button>
            </CardContent>
          </Card>
        </Fade>
      </Container>
    );
  }

  // Helper component for view-only fields
  const CopyableField = ({ label, value, icon }) => {
    const fieldKey = `${label}`;
    const isCopied = copiedField === fieldKey;
    
    return (
      <Box 
        sx={{ 
          position: 'relative',
          p: 2,
          borderRadius: 2,
          backgroundColor: alpha(theme.palette.background.paper, 0.6),
          border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            backgroundColor: alpha(theme.palette.primary.main, 0.04),
            borderColor: alpha(theme.palette.primary.main, 0.2),
            '& .copy-button': {
              opacity: 1,
              transform: 'translateX(0)'
            }
          }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
          {icon && (
            <Box sx={{ color: theme.palette.text.secondary, mt: 0.5 }}>
              {icon}
            </Box>
          )}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="subtitle2" sx={{ 
              fontWeight: 600, 
              color: theme.palette.text.secondary,
              mb: 0.5,
              textTransform: 'uppercase',
              fontSize: '0.75rem',
              letterSpacing: '0.5px'
            }}>
              {label}
            </Typography>
            <Typography variant="body2" sx={{ 
              wordBreak: 'break-all',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              lineHeight: 1.6,
              color: theme.palette.text.primary
            }}>
              {Array.isArray(value) ? (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {value.map((item, index) => (
                    <Chip 
                      key={index} 
                      label={item} 
                      size="small"
                      sx={{ 
                        backgroundColor: alpha(theme.palette.primary.main, 0.1),
                        color: theme.palette.primary.main,
                        fontWeight: 500
                      }}
                    />
                  ))}
                </Box>
              ) : (
                typeof value === 'object' ? JSON.stringify(value, null, 2) : value
              )}
            </Typography>
          </Box>
          <Zoom in={true}>
            <IconButton
              className="copy-button"
              onClick={() => handleCopyToClipboard(value, fieldKey, label)}
              sx={{
                opacity: 0,
                transform: 'translateX(10px)',
                transition: 'all 0.2s ease-in-out',
                backgroundColor: isCopied ? alpha(theme.palette.success.main, 0.1) : alpha(theme.palette.action.hover, 0.5),
                color: isCopied ? theme.palette.success.main : theme.palette.text.secondary,
                '&:hover': {
                  backgroundColor: isCopied ? alpha(theme.palette.success.main, 0.2) : alpha(theme.palette.action.hover, 0.8),
                }
              }}
            >
              {isCopied ? <Check fontSize="small" /> : <ContentCopy fontSize="small" />}
            </IconButton>
          </Zoom>
        </Box>
      </Box>
    );
  };

  // Handle adding a new tag
  const handleAddTag = () => {
    if (newTag.trim() === '') return;

    setEditedCriticalMetadata(prev => ({
      ...prev,
      tags: [...(prev.tags || []), newTag.trim()]
    }));

    setNewTag('');
  };

  // Handle removing a tag
  const handleRemoveTag = (tagToRemove) => {
    setEditedCriticalMetadata(prev => ({
      ...prev,
      tags: (prev.tags || []).filter(tag => tag !== tagToRemove)
    }));
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Fade in={true}>
        <Box>
          {/* Header Section */}
          <Box sx={{ 
            mb: 4, 
            p: 3,
            borderRadius: 3,
            background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.08)} 0%, ${alpha(theme.palette.secondary.main, 0.08)} 100%)`,
            border: `1px solid ${alpha(theme.palette.divider, 0.1)}`
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Button
                startIcon={<ArrowBack />}
                onClick={handleBack}
                sx={{ 
                  mr: 2,
                  borderRadius: 2,
                  textTransform: 'none',
                  fontWeight: 500
                }}
              >
                Back
              </Button>
              
              <Box sx={{ flexGrow: 1 }}>
                <Typography 
                  variant="h4" 
                  component="h1" 
                  sx={{ 
                    fontWeight: 700,
                    background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    mb: 1
                  }}
                >
                  {asset.criticalMetadata?.name || 'Asset Details'}
                </Typography>
                
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  {asset.verification?.verified && !asset.verification?.recoveryNeeded && (
                    <Tooltip title="Asset critical metadata authenticity verified. No integrity issues detected.">
                      <Chip
                        icon={<VerifiedUser />}
                        label="Verified"
                        color="success"
                        size="medium"
                        sx={{ 
                          fontWeight: 600,
                          '& .MuiChip-icon': { color: 'inherit' }
                        }}
                      />
                    </Tooltip>
                  )}
                  {recoveryStatus === 'recovered' && asset.verification?.recoverySuccessful && (
                    <Tooltip title="Asset metadata was automatically restored from blockchain due to potential tampering. Click to view recovery details in transaction history.">
                      <Chip
                        icon={<Warning />}
                        label="Metadata Restored"
                        color="warning"
                        size="medium"
                        clickable
                        onClick={() => navigate(`/assets/${assetId}/history`)}
                        sx={{ 
                          fontWeight: 600,
                          '& .MuiChip-icon': { color: 'inherit' },
                          '&:hover': { transform: 'translateY(-1px)' },
                          transition: 'transform 0.2s'
                        }}
                      />
                    </Tooltip>
                  )}
                  {recoveryStatus === 'recovered' && asset.verification?.recoveryNeeded && !asset.verification?.recoverySuccessful && (
                    <Tooltip title="Asset integrity could not be verified and recovery failed. Contact support for assistance. Click to view recovery details in transaction history.">
                      <Chip
                        icon={<Warning />}
                        label="Integrity Compromised"
                        color="error"
                        size="medium"
                        clickable
                        onClick={() => navigate(`/assets/${assetId}/history`)}
                        sx={{ 
                          fontWeight: 600,
                          '& .MuiChip-icon': { color: 'inherit' },
                          '&:hover': { transform: 'translateY(-1px)' },
                          transition: 'transform 0.2s'
                        }}
                      />
                    </Tooltip>
                  )}
                </Box>
              </Box>

              <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
                {!isEditing ? (
                  <>
                    <Button
                      variant="outlined"
                      startIcon={<Download />}
                      onClick={handleExportAsset}
                      sx={{ 
                        borderRadius: 2,
                        textTransform: 'none',
                        fontWeight: 500,
                        borderColor: alpha(theme.palette.primary.main, 0.5),
                        '&:hover': {
                          borderColor: theme.palette.primary.main,
                          backgroundColor: alpha(theme.palette.primary.main, 0.04)
                        }
                      }}
                    >
                      Export
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<Edit />}
                      onClick={handleEditToggle}
                      sx={{ 
                        borderRadius: 2,
                        textTransform: 'none',
                        fontWeight: 500
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="outlined"
                      color="error"
                      startIcon={<Delete />}
                      onClick={handleDelete}
                      disabled={isTransactionVisible}
                      sx={{ 
                        borderRadius: 2,
                        textTransform: 'none',
                        fontWeight: 500
                      }}
                    >
                      {isTransactionVisible ? 'Processing...' : 'Delete'}
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      variant="contained"
                      startIcon={<Save />}
                      onClick={handleSaveEdit}
                      disabled={isSaving}
                      sx={{ 
                        borderRadius: 2,
                        textTransform: 'none',
                        fontWeight: 500,
                        backgroundColor: theme.palette.success.main,
                        '&:hover': {
                          backgroundColor: theme.palette.success.dark
                        }
                      }}
                    >
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<Cancel />}
                      onClick={handleCancelEdit}
                      disabled={isSaving}
                      sx={{ 
                        borderRadius: 2,
                        textTransform: 'none',
                        fontWeight: 500
                      }}
                    >
                      Cancel
                    </Button>
                  </>
                )}
              </Box>
            </Box>
          </Box>

          {/* Delegation Mode Alert */}
          {isDelegateMode && (
            <Alert severity="info" sx={{ mb: 3 }}>
              <Typography variant="body2">
                <strong>Delegation Mode:</strong> You are viewing/editing this asset on behalf of {originalOwner}. 
                The original ownership will be preserved.
              </Typography>
            </Alert>
          )}

          <Grid container spacing={3}>
            {/* Basic Information Card */}
            <Grid item xs={12}>
              <Card sx={{ 
                borderRadius: 3,
                boxShadow: theme.shadows[4],
                border: `1px solid ${alpha(theme.palette.divider, 0.1)}`
              }}>
                <CardHeader 
                  avatar={<Security sx={{ color: theme.palette.primary.main }} />}
                  title="Basic Information"
                  titleTypographyProps={{ variant: 'h6', fontWeight: 600 }}
                  sx={{ 
                    backgroundColor: alpha(theme.palette.primary.main, 0.04),
                    borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`
                  }}
                />
                <CardContent sx={{ p: 3 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <CopyableField 
                        label="Asset ID" 
                        value={asset.assetId}
                        icon={<Fingerprint fontSize="small" />}
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <CopyableField 
                        label="Version" 
                        value={asset.version !== undefined && asset.version !== null ? asset.version : 1}
                        icon={<History fontSize="small" />}
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <CopyableField 
                        label="Owner" 
                        value={asset.walletAddress}
                        icon={<Person fontSize="small" />}
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <CopyableField 
                        label="Created" 
                        value={asset.createdAt ? formatDate(asset.createdAt) : 'N/A'}
                        icon={<Schedule fontSize="small" />}
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <CopyableField 
                        label="Last Modified" 
                        value={asset.updatedAt ? formatDate(asset.updatedAt) : 'N/A'}
                        icon={<Schedule fontSize="small" />}
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <CopyableField 
                        label="IPFS CID" 
                        value={asset.ipfsHash}
                        icon={<Storage fontSize="small" />}
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <CopyableField 
                        label="Blockchain Transaction" 
                        value={asset.blockchainTxId}
                        icon={<LinkIcon fontSize="small" />}
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            {/* Critical Metadata Card */}
            <Grid item xs={12}>
              <Card sx={{ 
                borderRadius: 3,
                boxShadow: theme.shadows[4],
                border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`
              }}>
                <CardHeader 
                  avatar={<VerifiedUser sx={{ color: theme.palette.success.main }} />}
                  title="Critical Metadata"
                  subheader="Blockchain-verified data"
                  titleTypographyProps={{ variant: 'h6', fontWeight: 600 }}
                  sx={{ 
                    backgroundColor: alpha(theme.palette.success.main, 0.04),
                    borderBottom: `1px solid ${alpha(theme.palette.success.main, 0.1)}`
                  }}
                />
                <CardContent sx={{ p: 3 }}>
                  <Grid container spacing={3}>
                    {isEditing ? (
                      <>
                        {/* Special section for core fields */}
                        <Grid item xs={12}>
                          <Typography variant="subtitle1" sx={{ 
                            fontWeight: 600, 
                            color: theme.palette.text.primary,
                            mb: 2,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1
                          }}>
                            Display Fields
                            <Tooltip title="These metadata fields appear on asset cards to help users quickly identify assets.">
                              <HelpOutline 
                                sx={{ 
                                  fontSize: '1rem', 
                                  color: theme.palette.text.secondary,
                                  cursor: 'help'
                                }} 
                              />
                            </Tooltip>
                          </Typography>
                          
                          <Grid container spacing={2}>
                            {/* Name field - required */}
                            <Grid item xs={12}>
                              <Box 
                                sx={{ 
                                  position: 'relative',
                                  p: 2,
                                  borderRadius: 2,
                                  backgroundColor: alpha(theme.palette.background.paper, 0.6),
                                  border: `2px solid ${alpha(theme.palette.primary.main, 0.3)}`,
                                  transition: 'all 0.2s ease-in-out'
                                }}
                              >
                                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                                  <Box sx={{ flex: 1, minWidth: 0 }}>
                                    <Typography variant="subtitle2" sx={{ 
                                      fontWeight: 600, 
                                      color: theme.palette.text.secondary,
                                      mb: 1,
                                      textTransform: 'uppercase',
                                      fontSize: '0.75rem',
                                      letterSpacing: '0.5px'
                                    }}>
                                      Name *
                                    </Typography>
                                    <TextField
                                      fullWidth
                                      variant="outlined"
                                      value={editedCriticalMetadata.name || ''}
                                      onChange={(e) => handleCriticalMetadataChange('name', e.target.value)}
                                      placeholder="Enter asset name..."
                                      size="small"
                                      sx={{
                                        '& .MuiOutlinedInput-root': {
                                          fontFamily: 'monospace',
                                          fontSize: '0.875rem'
                                        }
                                      }}
                                    />
                                  </Box>
                                </Box>
                              </Box>
                            </Grid>
                            
                            {/* Description field */}
                            <Grid item xs={12}>
                              <Box 
                                sx={{ 
                                  position: 'relative',
                                  p: 2,
                                  borderRadius: 2,
                                  backgroundColor: alpha(theme.palette.background.paper, 0.6),
                                  border: `2px solid ${alpha(theme.palette.primary.main, 0.3)}`,
                                  transition: 'all 0.2s ease-in-out'
                                }}
                              >
                                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                                  <Box sx={{ flex: 1, minWidth: 0 }}>
                                    <Typography variant="subtitle2" sx={{ 
                                      fontWeight: 600, 
                                      color: theme.palette.text.secondary,
                                      mb: 1,
                                      textTransform: 'uppercase',
                                      fontSize: '0.75rem',
                                      letterSpacing: '0.5px'
                                    }}>
                                      Description
                                    </Typography>
                                    <TextField
                                      fullWidth
                                      multiline
                                      rows={3}
                                      variant="outlined"
                                      value={editedCriticalMetadata.description || ''}
                                      onChange={(e) => handleCriticalMetadataChange('description', e.target.value)}
                                      placeholder="Enter asset description..."
                                      size="small"
                                      sx={{
                                        '& .MuiOutlinedInput-root': {
                                          fontFamily: 'monospace',
                                          fontSize: '0.875rem'
                                        }
                                      }}
                                    />
                                  </Box>
                                </Box>
                              </Box>
                            </Grid>
                            
                            {/* Tags field */}
                            <Grid item xs={12}>
                              <Box 
                                sx={{ 
                                  position: 'relative',
                                  p: 2,
                                  borderRadius: 2,
                                  backgroundColor: alpha(theme.palette.background.paper, 0.6),
                                  border: `2px solid ${alpha(theme.palette.primary.main, 0.3)}`,
                                  transition: 'all 0.2s ease-in-out'
                                }}
                              >
                                <Typography variant="subtitle2" sx={{ 
                                  fontWeight: 600, 
                                  color: theme.palette.text.secondary,
                                  mb: 2,
                                  textTransform: 'uppercase',
                                  fontSize: '0.75rem',
                                  letterSpacing: '0.5px'
                                }}>
                                  Tags
                                </Typography>
                                
                                {/* Tag input */}
                                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
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
                                    sx={{
                                      '& .MuiOutlinedInput-root': {
                                        fontFamily: 'monospace',
                                        fontSize: '0.875rem'
                                      }
                                    }}
                                  />
                                  <Button
                                    variant="contained"
                                    startIcon={<Add />}
                                    onClick={handleAddTag}
                                    sx={{ ml: 1 }}
                                    size="small"
                                  >
                                    Add
                                  </Button>
                                </Box>
                                
                                {/* Display tags */}
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                  {(editedCriticalMetadata.tags || []).map((tag, index) => (
                                    <Chip
                                      key={index}
                                      label={tag}
                                      onDelete={() => handleRemoveTag(tag)}
                                      size="small"
                                      sx={{ 
                                        backgroundColor: alpha(theme.palette.primary.main, 0.1),
                                        color: theme.palette.primary.main,
                                        fontWeight: 500
                                      }}
                                    />
                                  ))}
                                </Box>
                              </Box>
                            </Grid>
                          </Grid>
                        </Grid>
                        
                        {/* Other critical metadata fields */}
                        {Object.entries(editedCriticalMetadata)
                          .filter(([key]) => !['name', 'description', 'tags'].includes(key))
                          .length > 0 && (
                          <Grid item xs={12}>
                            <Divider sx={{ my: 2 }} />
                            <Typography variant="subtitle1" sx={{ 
                              fontWeight: 600, 
                              color: theme.palette.text.primary,
                              mb: 2
                            }}>
                              Custom Fields
                            </Typography>
                            
                            <Grid container spacing={2}>
                              {Object.entries(editedCriticalMetadata)
                                .filter(([key]) => !['name', 'description', 'tags'].includes(key))
                                .map(([key, value]) => (
                                <Grid item xs={12} md={6} key={key}>
                                  <EditableField 
                                    label={key} 
                                    value={value} 
                                    onChange={handleCriticalMetadataChange}
                                    onRemove={handleRemoveMetadataField}
                                    isCritical={true}
                                    theme={theme}
                                    alpha={alpha}
                                  />
                                </Grid>
                              ))}
                            </Grid>
                          </Grid>
                        )}
                        
                        {/* Add new field button */}
                        <Grid item xs={12}>
                          <Button
                            variant="outlined"
                            startIcon={<Add />}
                            onClick={() => handleAddMetadataField(true)}
                            sx={{ 
                              borderRadius: 2,
                              textTransform: 'none',
                              fontWeight: 500,
                              borderStyle: 'dashed',
                              color: theme.palette.success.main,
                              borderColor: theme.palette.success.main,
                              '&:hover': {
                                backgroundColor: alpha(theme.palette.success.main, 0.04),
                                borderColor: theme.palette.success.dark
                              }
                            }}
                          >
                            Add Critical Metadata Field
                          </Button>
                        </Grid>
                      </>
                    ) : (
                      /* View mode - show core fields section first, then other critical metadata */
                      <>
                        {/* Core Information Section - View Mode */}
                        <Grid item xs={12}>
                          <Typography variant="subtitle1" sx={{ 
                            fontWeight: 600, 
                            color: theme.palette.text.primary,
                            mb: 2,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1
                          }}>
                            Display Fields
                            <Tooltip title="These metadata fields appear on asset cards to help users quickly identify assets.">
                              <HelpOutline 
                                sx={{ 
                                  fontSize: '1rem', 
                                  color: theme.palette.text.secondary,
                                  cursor: 'help'
                                }} 
                              />
                            </Tooltip>
                          </Typography>
                          
                          <Grid container spacing={2}>
                            {/* Name field - view mode */}
                            {asset.criticalMetadata?.name && (
                              <Grid item xs={12}>
                                <CopyableField label="Name" value={asset.criticalMetadata.name} />
                              </Grid>
                            )}
                            
                            {/* Description field - view mode */}
                            {asset.criticalMetadata?.description && (
                              <Grid item xs={12}>
                                <CopyableField label="Description" value={asset.criticalMetadata.description} />
                              </Grid>
                            )}
                            
                            {/* Tags field - view mode */}
                            {asset.criticalMetadata?.tags && asset.criticalMetadata.tags.length > 0 && (
                              <Grid item xs={12}>
                                <CopyableField label="Tags" value={asset.criticalMetadata.tags} />
                              </Grid>
                            )}
                          </Grid>
                        </Grid>
                        
                        {/* Additional Critical Metadata Fields - View Mode */}
                        {asset.criticalMetadata && Object.entries(asset.criticalMetadata)
                          .filter(([key]) => !['name', 'description', 'tags'].includes(key))
                          .length > 0 && (
                          <Grid item xs={12}>
                            <Divider sx={{ my: 2 }} />
                            <Typography variant="subtitle1" sx={{ 
                              fontWeight: 600, 
                              color: theme.palette.text.primary,
                              mb: 2
                            }}>
                              Custom Fields
                            </Typography>
                            
                            <Grid container spacing={2}>
                              {Object.entries(asset.criticalMetadata)
                                .filter(([key]) => !['name', 'description', 'tags'].includes(key))
                                .map(([key, value]) => (
                                <Grid item xs={12} md={6} key={key}>
                                  <CopyableField label={key} value={value} />
                                </Grid>
                              ))}
                            </Grid>
                          </Grid>
                        )}
                      </>
                    )}
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            {/* Non-Critical Metadata Card */}
            {asset.nonCriticalMetadata && Object.keys(asset.nonCriticalMetadata).length > 0 && (
              <Grid item xs={12}>
                <Card sx={{ 
                  borderRadius: 3,
                  boxShadow: theme.shadows[4],
                  border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`
                }}>
                  <CardHeader 
                    avatar={<Storage sx={{ color: theme.palette.info.main }} />}
                    title="Non-Critical Metadata"
                    subheader="Supplementary information"
                    titleTypographyProps={{ variant: 'h6', fontWeight: 600 }}
                    sx={{ 
                      backgroundColor: alpha(theme.palette.info.main, 0.04),
                      borderBottom: `1px solid ${alpha(theme.palette.info.main, 0.1)}`
                    }}
                  />
                  <CardContent sx={{ p: 3 }}>
                    <Grid container spacing={2}>
                      {isEditing 
                        ? Object.entries(editedNonCriticalMetadata).map(([key, value]) => (
                            <Grid item xs={12} md={6} key={key}>
                              <EditableField 
                                label={key} 
                                value={value} 
                                onChange={handleNonCriticalMetadataChange}
                                onRemove={handleRemoveMetadataField}
                                isCritical={false}
                                theme={theme}
                                alpha={alpha}
                              />
                            </Grid>
                          ))
                        : Object.entries(asset.nonCriticalMetadata).map(([key, value]) => (
                            <Grid item xs={12} md={6} key={key}>
                              <CopyableField label={key} value={value} />
                            </Grid>
                          ))
                      }
                      {isEditing && (
                        <Grid item xs={12}>
                          <Button
                            variant="outlined"
                            startIcon={<Add />}
                            onClick={() => handleAddMetadataField(false)}
                            sx={{ 
                              borderRadius: 2,
                              textTransform: 'none',
                              fontWeight: 500,
                              borderStyle: 'dashed',
                              color: theme.palette.info.main,
                              borderColor: theme.palette.info.main,
                              '&:hover': {
                                backgroundColor: alpha(theme.palette.info.main, 0.04),
                                borderColor: theme.palette.info.dark
                              }
                            }}
                          >
                            Add Non-Critical Metadata Field
                          </Button>
                        </Grid>
                      )}
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>

          {/* Transaction Signer Modal */}
          <TransactionSigner
            operation={transactionOperation}
            operationData={transactionData}
            onSuccess={onTransactionSuccess}
            onError={onTransactionError}
            onCancel={() => {
              // Reset editing state when modal is cancelled
              setIsSaving(false);
              hideSigner();
            }}
            isVisible={isTransactionVisible}
          />
        </Box>
      </Fade>
    </Container>
  );
}

export default AssetDetailPage;