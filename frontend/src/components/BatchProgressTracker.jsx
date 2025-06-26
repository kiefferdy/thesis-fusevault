import { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Collapse,
  Button,
  Chip,
  Alert,
  IconButton,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Pending,
  ExpandMore,
  ExpandLess,
  Refresh,
  Info,
  Timer,
  CloudUpload,
  Security,
  Storage,
  CheckCircleOutline,
  Launch
} from '@mui/icons-material';

const BatchProgressTracker = ({
  isUploading = false,
  uploadProgress = 0,
  currentStage = 0,
  stages = [],
  assets = [],
  assetProgress = {},
  errors = {},
  warnings = {},
  onRetry,
  estimatedTimeRemaining = null,
  blockchainTxHash = null,
  networkStatus = null
}) => {
  const [expandedStages, setExpandedStages] = useState(new Set([0]));
  const [txDetailsDialog, setTxDetailsDialog] = useState(false);
  const [startTime, setStartTime] = useState(null);

  // Default stages if none provided
  const defaultStages = [
    {
      id: 'validation',
      label: 'Validating Assets',
      description: 'Checking asset data and preparing for upload',
      icon: <CheckCircleOutline />,
      details: 'Validating JSON structure, checking for duplicates, and preparing batch'
    },
    {
      id: 'ipfs',
      label: 'Uploading to IPFS',
      description: 'Storing metadata on decentralized storage',
      icon: <CloudUpload />,
      details: 'Each asset\'s critical metadata is being uploaded to IPFS for permanent storage'
    },
    {
      id: 'blockchain',
      label: 'Blockchain Transaction',
      description: 'Preparing and signing blockchain transaction',
      icon: <Security />,
      details: 'Creating batch transaction for blockchain recording'
    },
    {
      id: 'confirmation',
      label: 'Awaiting Confirmation',
      description: 'Waiting for blockchain confirmation',
      icon: <Timer />,
      details: 'Transaction is being processed by the Sepolia network'
    },
    {
      id: 'completion',
      label: 'Finalizing',
      description: 'Updating database and completing upload',
      icon: <Storage />,
      details: 'Recording assets in database and finalizing the batch upload'
    }
  ];

  const stageList = stages.length > 0 ? stages : defaultStages;

  // Start timer when upload begins
  useEffect(() => {
    if (isUploading && !startTime) {
      setStartTime(Date.now());
    } else if (!isUploading) {
      setStartTime(null);
    }
  }, [isUploading, startTime]);

  // Calculate elapsed time
  const [elapsedTime, setElapsedTime] = useState(null);
  
  useEffect(() => {
    let interval;
    if (startTime && isUploading) {
      interval = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
    } else if (!isUploading) {
      setElapsedTime(null);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [startTime, isUploading]);

  // Format time
  const formatTime = (seconds) => {
    if (!seconds) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  // Get stage status
  const getStageStatus = (stageIndex) => {
    if (stageIndex < currentStage) return 'completed';
    if (stageIndex === currentStage && isUploading) return 'active';
    if (stageIndex === currentStage && !isUploading && errors.general) return 'error';
    return 'pending';
  };

  // Get stage icon
  const getStageIcon = (stage, status) => {
    if (status === 'completed') return <CheckCircle color="success" />;
    if (status === 'error') return <Error color="error" />;
    if (status === 'active') return stage.icon;
    return <Pending color="disabled" />;
  };

  // Toggle stage expansion
  const toggleStageExpansion = (stageIndex) => {
    const newExpanded = new Set(expandedStages);
    if (newExpanded.has(stageIndex)) {
      newExpanded.delete(stageIndex);
    } else {
      newExpanded.add(stageIndex);
    }
    setExpandedStages(newExpanded);
  };

  // Get asset status counts
  const assetStatusCounts = useMemo(() => {
    const counts = { pending: 0, processing: 0, completed: 0, error: 0 };
    
    assets.forEach(asset => {
      const progress = assetProgress[asset.assetId];
      const error = errors[asset.assetId];
      
      if (error) {
        counts.error++;
      } else if (progress === 100) {
        counts.completed++;
      } else if (progress > 0) {
        counts.processing++;
      } else {
        counts.pending++;
      }
    });
    
    return counts;
  }, [assets, assetProgress, errors]);

  // Use uploadProgress directly from props (calculated by backend progress tracking)
  const overallProgress = uploadProgress;

  if (!isUploading && uploadProgress === 0) {
    return null;
  }

  return (
    <Card sx={{ mt: 3 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Batch Upload Progress
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
            {elapsedTime !== null && (
              <Chip 
                icon={<Timer />} 
                label={`${formatTime(elapsedTime)} elapsed`} 
                size="small" 
                variant="outlined"
                sx={{ fontWeight: 500 }}
              />
            )}
            {estimatedTimeRemaining && (
              <Chip 
                icon={<Timer />}
                label={`~${formatTime(estimatedTimeRemaining)} remaining`} 
                size="small" 
                color="primary" 
                variant="outlined"
                sx={{ fontWeight: 500 }}
              />
            )}
            {isUploading && (
              <Chip 
                label="In Progress" 
                size="small" 
                color="primary"
                sx={{ fontWeight: 500 }}
              />
            )}
          </Box>
        </Box>

        {/* Overall Progress */}
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Overall Progress
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {Math.round(overallProgress)}%
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={overallProgress} 
            sx={{ 
              height: 8, 
              borderRadius: 4,
              bgcolor: 'grey.200',
              '& .MuiLinearProgress-bar': {
                borderRadius: 4,
                transition: 'transform 0.4s ease'
              }
            }}
          />
        </Box>

        {/* Asset Status Summary */}
        {assets.length > 0 && currentStage === 1 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Asset Status ({assets.length} total)
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {assetStatusCounts.completed > 0 && (
                <Chip 
                  icon={<CheckCircle />}
                  label={`${assetStatusCounts.completed} uploaded`}
                  size="small"
                  color="success"
                  sx={{ fontWeight: 500 }}
                />
              )}
              {assetStatusCounts.processing > 0 && (
                <Chip 
                  icon={<Pending />}
                  label={`${assetStatusCounts.processing} uploading`}
                  size="small"
                  color="primary"
                  sx={{ fontWeight: 500 }}
                />
              )}
              {assetStatusCounts.pending > 0 && (
                <Chip 
                  icon={<Pending />}
                  label={`${assetStatusCounts.pending} pending`}
                  size="small"
                  variant="outlined"
                  sx={{ fontWeight: 500 }}
                />
              )}
              {assetStatusCounts.error > 0 && (
                <Chip 
                  icon={<Error />}
                  label={`${assetStatusCounts.error} errors`}
                  size="small"
                  color="error"
                  sx={{ fontWeight: 500 }}
                />
              )}
            </Box>
          </Box>
        )}

        {/* Compact IPFS Asset Progress - Only show during IPFS upload stage */}
        {currentStage === 1 && assets.length > 0 && (
          <Card 
            variant="outlined" 
            sx={{ 
              mb: 3,
              border: '1px solid',
              borderColor: 'primary.main',
              bgcolor: 'primary.50'
            }}
          >
            <CardContent sx={{ pt: 2, pb: 2 }}>
              <Typography variant="subtitle2" gutterBottom sx={{ color: 'primary.main', fontWeight: 600 }}>
                📁 IPFS Upload Progress
              </Typography>
              
              
              {/* Compact grid layout for assets */}
              <Box sx={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: 1,
                mt: 1
              }}>
                {assets.map((asset) => {
                  const assetProgressData = assetProgress[asset.assetId];
                  const status = assetProgressData?.status || 'pending';
                  const progress = assetProgressData?.progress || 0;
                  
                  return (
                    <Box 
                      key={asset.assetId}
                      sx={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: 1,
                        p: 1,
                        bgcolor: 'background.paper',
                        borderRadius: 1,
                        border: '1px solid',
                        borderColor: 'divider'
                      }}
                    >
                      {/* Status icon */}
                      <Box sx={{ minWidth: 20 }}>
                        {status === 'completed' ? (
                          <CheckCircle sx={{ fontSize: 16, color: 'success.main' }} />
                        ) : status === 'uploading' ? (
                          <CloudUpload sx={{ fontSize: 16, color: 'primary.main' }} />
                        ) : status === 'error' ? (
                          <Error sx={{ fontSize: 16, color: 'error.main' }} />
                        ) : (
                          <Pending sx={{ fontSize: 16, color: 'grey.400' }} />
                        )}
                      </Box>
                      
                      {/* Asset name - truncated */}
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          flex: 1,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontSize: '0.75rem',
                          fontWeight: status === 'uploading' ? 600 : 400
                        }}
                        title={asset.criticalMetadata?.name || asset.assetId}
                      >
                        {asset.criticalMetadata?.name || asset.assetId}
                      </Typography>
                      
                      {/* Status badge */}
                      <Chip 
                        label={status === 'completed' ? '✓' : status === 'uploading' ? '...' : '○'} 
                        size="small"
                        variant={status === 'completed' ? 'filled' : 'outlined'}
                        color={status === 'completed' ? 'success' : status === 'uploading' ? 'primary' : 'default'}
                        sx={{ 
                          height: 16, 
                          fontSize: '0.6rem',
                          '& .MuiChip-label': { px: 0.5 }
                        }}
                      />
                    </Box>
                  );
                })}
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Blockchain Transaction Info */}
        {blockchainTxHash && (
          <Alert 
            severity="info" 
            sx={{ 
              mb: 3,
              '& .MuiAlert-message': {
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%'
              }
            }}
            action={
              <Button
                size="small"
                onClick={() => setTxDetailsDialog(true)}
                endIcon={<Launch />}
                sx={{ fontWeight: 500 }}
              >
                View Transaction
              </Button>
            }
          >
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                Blockchain Transaction Submitted
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                {blockchainTxHash.slice(0, 10)}...{blockchainTxHash.slice(-8)}
              </Typography>
            </Box>
          </Alert>
        )}

        {/* Network Status */}
        {networkStatus && networkStatus.message && (
          <Alert severity={networkStatus.type} sx={{ mb: 3 }}>
            {networkStatus.message}
          </Alert>
        )}

        {/* Stage Progress */}
        <Stepper 
          activeStep={currentStage} 
          orientation="vertical"
          sx={{
            '& .MuiStepLabel-root': {
              cursor: 'pointer',
              '&:hover': {
                bgcolor: 'action.hover',
                borderRadius: 1
              }
            },
            '& .MuiStepContent-root': {
              borderLeft: '2px solid',
              borderColor: 'divider'
            }
          }}
        >
          {stageList.map((stage, index) => {
            const status = getStageStatus(index);
            const isExpanded = expandedStages.has(index);
            
            return (
              <Step key={stage.id}>
                <StepLabel
                  icon={getStageIcon(stage, status)}
                  onClick={() => toggleStageExpansion(index)}
                  sx={{ cursor: 'pointer' }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                    <Box>
                      <Typography variant="body1">{stage.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {stage.description}
                      </Typography>
                    </Box>
                    <IconButton size="small">
                      {isExpanded ? <ExpandLess /> : <ExpandMore />}
                    </IconButton>
                  </Box>
                </StepLabel>
                
                <StepContent>
                  <Collapse in={isExpanded}>
                    <Box sx={{ pl: 2, pb: 2 }}>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        {stage.details}
                      </Typography>
                      
                      {/* Stage-specific content */}
                      {index === 0 && ( // Validation stage
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • Checking asset data structure and required fields
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • Validating asset IDs for uniqueness
                          </Typography>
                          <Typography variant="body2">
                            • Preparing {assets.length} assets for upload
                          </Typography>
                          {status === 'active' && (
                            <LinearProgress 
                              variant="indeterminate"
                              sx={{ mt: 2, height: 4, borderRadius: 2 }}
                            />
                          )}
                        </Box>
                      )}
                      
                      {index === 1 && ( // IPFS stage
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • Uploading critical metadata to IPFS (up to 10 concurrent)
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • Each asset stored on decentralized network
                          </Typography>
                          {Object.keys(assetProgress).length > 0 && (
                            <Typography variant="body2" sx={{ fontWeight: 500, color: 'primary.main' }}>
                              Progress: {Object.values(assetProgress).filter(p => p?.status === 'completed').length}/{assets.length} assets uploaded
                            </Typography>
                          )}
                          {status === 'active' && (
                            <LinearProgress 
                              variant="determinate"
                              value={uploadProgress}
                              sx={{ mt: 2, height: 6, borderRadius: 3 }}
                            />
                          )}
                        </Box>
                      )}
                      
                      {index === 2 && ( // Blockchain stage
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • Creating blockchain transaction for all assets
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • Single transaction covers {assets.length} assets (gas efficient)
                          </Typography>
                          <Typography variant="body2">
                            • Waiting for MetaMask signature...
                          </Typography>
                          {status === 'active' && (
                            <LinearProgress 
                              variant="indeterminate"
                              sx={{ mt: 2, height: 4, borderRadius: 2 }}
                            />
                          )}
                        </Box>
                      )}
                      
                      {index === 3 && ( // Confirmation stage
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • Waiting for Sepolia network confirmation
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • Typically takes 15-30 seconds
                          </Typography>
                          {blockchainTxHash && (
                            <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                              TX: {blockchainTxHash.slice(0, 20)}...
                            </Typography>
                          )}
                          {status === 'active' && (
                            <LinearProgress 
                              variant="indeterminate"
                              sx={{ mt: 2, height: 4, borderRadius: 2 }}
                            />
                          )}
                        </Box>
                      )}
                      
                      {index === 4 && ( // Completion stage
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • Recording assets in database
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            • Updating transaction records
                          </Typography>
                          <Typography variant="body2">
                            • Finalizing batch upload process
                          </Typography>
                          {status === 'active' && (
                            <LinearProgress 
                              variant="determinate"
                              value={uploadProgress}
                              sx={{ mt: 2, height: 6, borderRadius: 3 }}
                            />
                          )}
                        </Box>
                      )}
                      
                      {/* Stage errors */}
                      {status === 'error' && errors.general && (
                        <Alert 
                          severity="error" 
                          sx={{ mt: 1 }}
                          action={
                            onRetry && (
                              <Button size="small" onClick={onRetry} startIcon={<Refresh />}>
                                Retry
                              </Button>
                            )
                          }
                        >
                          {errors.general}
                        </Alert>
                      )}
                    </Box>
                  </Collapse>
                </StepContent>
              </Step>
            );
          })}
        </Stepper>

        {/* Completion Status */}
        {!isUploading && uploadProgress === 100 && currentStage === 4 && (
          <Alert severity="success" sx={{ mt: 2 }}>
            <Typography variant="body2" fontWeight="bold">
              Batch upload completed successfully!
            </Typography>
            <Typography variant="body2">
              {assets.length} assets have been uploaded and recorded on the blockchain.
            </Typography>
          </Alert>
        )}

        {/* Error Summary */}
        {!isUploading && Object.keys(errors).length > 0 && (
          <Alert 
            severity="error" 
            sx={{ mt: 2 }}
            action={
              onRetry && (
                <Button size="small" onClick={onRetry} startIcon={<Refresh />}>
                  Retry Upload
                </Button>
              )
            }
          >
            <Typography variant="body2" fontWeight="bold">
              Upload completed with errors
            </Typography>
            <Typography variant="body2">
              {Object.keys(errors).length} asset(s) failed to upload. Check individual asset details above.
            </Typography>
          </Alert>
        )}
      </CardContent>

      {/* Transaction Details Dialog */}
      <Dialog 
        open={txDetailsDialog}
        onClose={() => setTxDetailsDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Blockchain Transaction Details</DialogTitle>
        <DialogContent>
          {blockchainTxHash && (
            <Box>
              <Typography variant="body2" gutterBottom>
                <strong>Transaction Hash:</strong>
              </Typography>
              <Typography 
                variant="body2" 
                sx={{ 
                  fontFamily: 'monospace', 
                  bgcolor: 'grey.100', 
                  p: 1, 
                  borderRadius: 1,
                  wordBreak: 'break-all'
                }}
              >
                {blockchainTxHash}
              </Typography>
              
              <Typography variant="body2" sx={{ mt: 2 }} gutterBottom>
                <strong>Network:</strong> Sepolia Testnet
              </Typography>
              
              <Typography variant="body2" gutterBottom>
                <strong>Status:</strong> {isUploading ? 'Processing' : 'Confirmed'}
              </Typography>
              
              <Button
                variant="outlined"
                size="small"
                sx={{ mt: 2 }}
                onClick={() => window.open(`https://sepolia.etherscan.io/tx/${blockchainTxHash}`, '_blank')}
                endIcon={<Launch />}
              >
                View on Etherscan
              </Button>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTxDetailsDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default BatchProgressTracker;