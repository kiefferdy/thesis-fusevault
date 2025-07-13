import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  alpha
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
  Link as LinkIcon
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { assetService } from '../services/assetService';
import { useAssets } from '../hooks/useAssets';
import { useTransactionSigner } from '../hooks/useTransactionSigner';
import { useAuth } from '../contexts/AuthContext';
import TransactionSigner from '../components/TransactionSigner';
import { formatDate, formatWalletAddress, formatTransactionHash } from '../utils/formatters';

function AssetDetailPage() {
  const { assetId } = useParams();
  const [asset, setAsset] = useState(null);
  const [version] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recoveryStatus, setRecoveryStatus] = useState(null);
  const [recoveryMessage, setRecoveryMessage] = useState('Loading asset data...');
  const [progressPercent, setProgressPercent] = useState(0);
  const [copiedField, setCopiedField] = useState(null);
  const { deleteAsset, isDeleting } = useAssets();
  const { currentAccount } = useAuth();
  const {
    isVisible,
    operation,
    operationData,
    showDeleteSigner,
    hideSigner,
    onSuccess,
    onError
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


  const handleEdit = () => {
    navigate(`/assets/${assetId}/edit`);
  };

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
    navigate('/dashboard');
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

  // Helper component for copyable fields
  const CopyableField = ({ label, value, icon }) => {
    const fieldKey = `${label}-${value}`;
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
                  onClick={handleEdit}
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
                  disabled={isVisible}
                  sx={{ 
                    borderRadius: 2,
                    textTransform: 'none',
                    fontWeight: 500
                  }}
                >
                  {isVisible ? 'Processing...' : 'Delete'}
                </Button>
              </Box>
            </Box>
          </Box>

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
                        value={asset.versionNumber || 1}
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
                  <Grid container spacing={2}>
                    {asset.criticalMetadata && Object.entries(asset.criticalMetadata).map(([key, value]) => (
                      <Grid item xs={12} md={6} key={key}>
                        <CopyableField label={key} value={value} />
                      </Grid>
                    ))}
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
                    title="Additional Metadata"
                    subheader="Supplementary information"
                    titleTypographyProps={{ variant: 'h6', fontWeight: 600 }}
                    sx={{ 
                      backgroundColor: alpha(theme.palette.info.main, 0.04),
                      borderBottom: `1px solid ${alpha(theme.palette.info.main, 0.1)}`
                    }}
                  />
                  <CardContent sx={{ p: 3 }}>
                    <Grid container spacing={2}>
                      {Object.entries(asset.nonCriticalMetadata).map(([key, value]) => (
                        <Grid item xs={12} md={6} key={key}>
                          <CopyableField label={key} value={value} />
                        </Grid>
                      ))}
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>

          {/* Transaction Signer Modal */}
          <TransactionSigner
            operation={operation}
            operationData={operationData}
            onSuccess={onSuccess}
            onError={onError}
            onCancel={hideSigner}
            isVisible={isVisible}
          />
        </Box>
      </Fade>
    </Container>
  );
}

export default AssetDetailPage;