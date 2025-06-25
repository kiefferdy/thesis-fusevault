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
  const [showAssetDetails, setShowAssetDetails] = useState(false);
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

  // Calculate overall progress
  const overallProgress = useMemo(() => {
    if (assets.length === 0) return uploadProgress;
    
    const totalAssetProgress = Object.values(assetProgress).reduce((sum, progress) => sum + progress, 0);
    const maxProgress = assets.length * 100;
    
    return maxProgress > 0 ? (totalAssetProgress / maxProgress) * 100 : uploadProgress;
  }, [assets.length, assetProgress, uploadProgress]);

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
        {assets.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Asset Status ({assets.length} total)
              </Typography>
              <Button
                size="small"
                onClick={() => setShowAssetDetails(!showAssetDetails)}
                endIcon={showAssetDetails ? <ExpandLess /> : <ExpandMore />}
              >
                Details
              </Button>
            </Box>
            
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {assetStatusCounts.completed > 0 && (
                <Chip 
                  icon={<CheckCircle />}
                  label={`${assetStatusCounts.completed} completed`}
                  size="small"
                  color="success"
                  sx={{ fontWeight: 500 }}
                />
              )}
              {assetStatusCounts.processing > 0 && (
                <Chip 
                  icon={<Pending />}
                  label={`${assetStatusCounts.processing} processing`}
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

        {/* Detailed Asset Progress */}
        <Collapse in={showAssetDetails}>
          <Card 
            variant="outlined" 
            sx={{ 
              mb: 3,
              border: '1px solid',
              borderColor: 'divider',
              bgcolor: 'grey.50'
            }}
          >
            <CardContent sx={{ pt: 2, pb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Individual Asset Progress
              </Typography>
              <List dense>
                {assets.map((asset) => {
                  const progress = assetProgress[asset.assetId] || 0;
                  const error = errors[asset.assetId];
                  const warning = warnings[asset.assetId];
                  
                  return (
                    <ListItem key={asset.assetId} sx={{ px: 0 }}>
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        {error ? (
                          <Error color="error" />
                        ) : warning ? (
                          <Warning color="warning" />
                        ) : progress === 100 ? (
                          <CheckCircle color="success" />
                        ) : progress > 0 ? (
                          <Pending color="primary" />
                        ) : (
                          <Pending color="disabled" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={asset.criticalMetadata?.name || asset.assetId}
                        secondary={`${progress}%`}
                        sx={{ 
                          '& .MuiListItemText-primary': { 
                            fontSize: '0.875rem',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            maxWidth: '60%'
                          },
                          '& .MuiListItemText-secondary': {
                            fontSize: '0.75rem'
                          }
                        }}
                      />
                      <Box sx={{ flexGrow: 1, ml: 2 }}>
                        <LinearProgress 
                          variant="determinate" 
                          value={progress} 
                          size="small"
                          sx={{ 
                            height: 4, 
                            mb: 0.5, 
                            borderRadius: 2,
                            bgcolor: 'grey.200',
                            '& .MuiLinearProgress-bar': {
                              borderRadius: 2,
                              transition: 'transform 0.3s ease'
                            }
                          }}
                          color={error ? 'error' : warning ? 'warning' : 'primary'}
                        />
                        {(error || warning) && (
                          <Typography variant="caption" color={error ? 'error' : 'warning.main'}>
                            {error || warning}
                          </Typography>
                        )}
                      </Box>
                    </ListItem>
                  );
                })}
              </List>
            </CardContent>
          </Card>
        </Collapse>

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
        {networkStatus && (
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
                      
                      {/* Stage-specific progress */}
                      {status === 'active' && (
                        <Box sx={{ mt: 2 }}>
                          <LinearProgress 
                            variant={uploadProgress > 0 ? 'determinate' : 'indeterminate'}
                            value={uploadProgress}
                            sx={{ 
                              mb: 1, 
                              height: 6,
                              borderRadius: 3,
                              bgcolor: 'grey.200',
                              '& .MuiLinearProgress-bar': {
                                borderRadius: 3
                              }
                            }}
                          />
                          <Typography variant="caption" color="primary.main" sx={{ fontWeight: 500 }}>
                            {stage.label} in progress... {uploadProgress > 0 ? `${Math.round(uploadProgress)}%` : ''}
                          </Typography>
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
        {!isUploading && uploadProgress === 100 && (
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