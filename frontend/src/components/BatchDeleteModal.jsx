import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  TextField,
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Checkbox,
  Alert,
  Chip,
  LinearProgress,
  IconButton,
  Collapse,
  Paper,
  Stepper,
  Step,
  StepLabel,
  Divider
} from '@mui/material';
import {
  Delete,
  Warning,
  CheckCircle,
  Error,
  ExpandMore,
  ExpandLess,
  Info,
  AccountBalanceWallet,
  LocalGasStation
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import { transactionFlow, metamaskUtils } from '../services/blockchainService';

const BatchDeleteModal = ({ 
  open, 
  onClose, 
  selectedAssets = [],
  onDeleteSuccess 
}) => {
  const [deleteReason, setDeleteReason] = useState('');
  const [checkedAssets, setCheckedAssets] = useState(new Set());
  const [processing, setProcessing] = useState(false);
  const [step, setStep] = useState(0); // 0: select, 1: confirm, 2: sign, 3: processing
  const [expandedWarnings, setExpandedWarnings] = useState(false);
  const [deleteResults, setDeleteResults] = useState(null);
  const [networkStatus, setNetworkStatus] = useState(null);
  const [gasEstimate, setGasEstimate] = useState(null);
  const [transactionProgress, setTransactionProgress] = useState(0);
  const [currentTransactionStep, setCurrentTransactionStep] = useState('');
  const [error, setError] = useState(null);
  const { currentAccount } = useAuth();

  // Initialize checked assets when modal opens or assets change
  useEffect(() => {
    if (open && selectedAssets.length > 0) {
      setCheckedAssets(new Set(selectedAssets.map(asset => asset.assetId)));
      setStep(0);
      setDeleteResults(null);
      setProcessing(false);
      setError(null);
      setTransactionProgress(0);
      setCurrentTransactionStep('');
    }
  }, [open, selectedAssets]);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setDeleteReason('');
      setCheckedAssets(new Set());
      setStep(0);
      setDeleteResults(null);
      setProcessing(false);
      setExpandedWarnings(false);
      setNetworkStatus(null);
      setGasEstimate(null);
      setTransactionProgress(0);
      setCurrentTransactionStep('');
      setError(null);
    }
  }, [open]);

  // Check network and estimate gas when reaching step 2 (sign transaction)
  useEffect(() => {
    if (step === 2) {
      checkNetwork();
      estimateGas();
    }
  }, [step, checkedAssets]);

  const checkNetwork = async () => {
    try {
      if (metamaskUtils.isMetaMaskAvailable()) {
        const status = await metamaskUtils.checkNetwork();
        setNetworkStatus(status);
      }
    } catch (error) {
      console.error('Error checking network:', error);
    }
  };

  const estimateGas = () => {
    const assetCount = checkedAssets.size;
    const baseGas = 100000;
    const perAssetGas = 50000;
    const totalGas = baseGas + (assetCount * perAssetGas);
    
    setGasEstimate({
      estimatedGas: totalGas,
      gasPrice: 20000000000, // 20 gwei
      estimatedCostEth: ((totalGas * 20000000000) / 1e18).toFixed(4)
    });
  };

  const handleNetworkSwitch = async () => {
    try {
      await metamaskUtils.switchToSepolia();
      setTimeout(() => {
        checkNetwork();
      }, 1000);
    } catch (error) {
      console.error('Error switching network:', error);
      setError('Failed to switch network: ' + (error.message || 'Unknown error'));
    }
  };

  const handleAssetToggle = (assetId) => {
    const newChecked = new Set(checkedAssets);
    if (newChecked.has(assetId)) {
      newChecked.delete(assetId);
    } else {
      newChecked.add(assetId);
    }
    setCheckedAssets(newChecked);
  };

  const handleSelectAll = () => {
    if (checkedAssets.size === selectedAssets.length) {
      setCheckedAssets(new Set());
    } else {
      setCheckedAssets(new Set(selectedAssets.map(asset => asset.assetId)));
    }
  };

  const getCheckedAssets = () => {
    return selectedAssets.filter(asset => checkedAssets.has(asset.assetId));
  };

  const handleNext = () => {
    if (step === 0) {
      if (checkedAssets.size === 0) {
        toast.error('Please select at least one asset to delete');
        return;
      }
      setStep(1);
    } else if (step === 1) {
      setStep(2); // Go to sign transaction step
    }
  };

  const handleBack = () => {
    if (step > 0 && !processing) {
      setStep(step - 1);
      setError(null);
    }
  };

  const handleSignTransaction = async () => {
    const assetsToDelete = getCheckedAssets();
    const assetIds = assetsToDelete.map(asset => asset.assetId);
    setProcessing(true);
    setStep(3); // Go to processing step
    setError(null);
    setTransactionProgress(0);
    setCurrentTransactionStep('Starting batch deletion...');
    
    try {
      const result = await transactionFlow.batchDeleteWithSigning(
        assetIds,
        currentAccount,
        deleteReason || 'Batch deletion',
        (stepMessage, progress, metadata) => {
          setCurrentTransactionStep(stepMessage);
          setTransactionProgress(progress);
        }
      );
      
      setDeleteResults(result);
      setProcessing(false);
      setTransactionProgress(100);
      setCurrentTransactionStep('Batch deletion completed!');
      
      // Calculate counts from results only (ignore backend success_count to avoid conflicts)
      const results = result.results || {};
      const syncedCount = Object.values(results).filter(r => r.status === 'synced').length;
      const deletedCount = Object.values(results).filter(r => r.status === 'success').length;
      const errorCount = Object.values(results).filter(r => r.status === 'error').length;
      const totalCount = Object.keys(results).length;
      
      // Show appropriate success message based on what actually happened
      if (syncedCount > 0 && deletedCount === 0 && errorCount === 0) {
        // All assets were already deleted on blockchain
        toast.success(`Database synced: ${syncedCount} assets were already deleted on blockchain`, {
          duration: 6000,
          position: 'top-center'
        });
      } else if (syncedCount > 0 && deletedCount > 0) {
        // Mixed operation - some deleted, some synced
        toast.success(`Batch completed: ${deletedCount} deleted, ${syncedCount} synced`, {
          duration: 6000,
          position: 'top-center'
        });
      } else if (deletedCount > 0 && errorCount === 0) {
        // Normal successful deletion
        toast.success(`Successfully deleted ${deletedCount} assets!`, {
          duration: 6000,
          position: 'top-center'
        });
      } else if (deletedCount > 0 || syncedCount > 0) {
        // Partial success
        const successfulCount = deletedCount + syncedCount;
        toast.success(`Batch completed: ${successfulCount} successful, ${errorCount} failed`, {
          duration: 6000,
          position: 'top-center'
        });
      } else {
        // All failed
        toast.error(`Batch failed: ${errorCount} assets could not be processed`, {
          duration: 6000,
          position: 'top-center'
        });
      }
      
      // Keep modal open for users to read the detailed results
      // Don't auto-close or call onDeleteSuccess until user manually closes modal
      
    } catch (error) {
      console.error('Batch delete failed:', error);
      setProcessing(false);
      setError(error.message || 'Transaction failed');
      
      // Don't go back if user cancelled
      if (!error.message?.toLowerCase().includes('cancelled')) {
        setStep(2); // Stay on sign transaction step
        toast.error(`Batch deletion failed: ${error.message}`);
      }
    }
  };

  const handleClose = () => {
    if (!processing) {
      // If we have successful results and haven't called onDeleteSuccess yet, call it now
      if (deleteResults && (deleteResults.status === 'success' || deleteResults.status === 'partial')) {
        if (onDeleteSuccess) {
          onDeleteSuccess(deleteResults);
        }
      }
      onClose();
    }
  };

  const getStepContent = () => {
    const assetsToDelete = getCheckedAssets();
    
    switch (step) {
      case 0:
        return (
          <Box>
            <Typography variant="body1" gutterBottom>
              Select the assets you want to delete:
            </Typography>
            
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Checkbox
                checked={checkedAssets.size === selectedAssets.length && selectedAssets.length > 0}
                indeterminate={checkedAssets.size > 0 && checkedAssets.size < selectedAssets.length}
                onChange={handleSelectAll}
              />
              <Typography variant="body2">
                Select all ({checkedAssets.size}/{selectedAssets.length} selected)
              </Typography>
            </Box>

            <Paper sx={{ maxHeight: 300, overflow: 'auto', mb: 2 }}>
              <List dense>
                {selectedAssets.map((asset) => (
                  <ListItem
                    key={asset.assetId}
                    button
                    onClick={() => handleAssetToggle(asset.assetId)}
                    sx={{ 
                      backgroundColor: checkedAssets.has(asset.assetId) ? 'action.selected' : 'transparent'
                    }}
                  >
                    <ListItemIcon>
                      <Checkbox
                        checked={checkedAssets.has(asset.assetId)}
                        tabIndex={-1}
                        disableRipple
                      />
                    </ListItemIcon>
                    <ListItemText
                      primary={asset.criticalMetadata?.name || 'Untitled Asset'}
                      secondary={`ID: ${asset.assetId} | Version: ${asset.versionNumber}`}
                    />
                  </ListItem>
                ))}
              </List>
            </Paper>

            <TextField
              label="Reason for deletion (optional)"
              fullWidth
              multiline
              rows={2}
              value={deleteReason}
              onChange={(e) => setDeleteReason(e.target.value)}
              placeholder="Enter a reason for this batch deletion..."
            />
          </Box>
        );

      case 1:
        return (
          <Box>
            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Confirm Batch Deletion
              </Typography>
              <Typography>
                You are about to delete {assetsToDelete.length} asset{assetsToDelete.length !== 1 ? 's' : ''}. 
                This action cannot be undone.
              </Typography>
            </Alert>

            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Typography variant="subtitle1">
                  Assets to delete ({assetsToDelete.length})
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => setExpandedWarnings(!expandedWarnings)}
                  sx={{ ml: 1 }}
                >
                  {expandedWarnings ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </Box>
              
              <Collapse in={expandedWarnings}>
                <Paper sx={{ p: 2, maxHeight: 200, overflow: 'auto' }}>
                  {assetsToDelete.map((asset) => (
                    <Box key={asset.assetId} sx={{ mb: 1 }}>
                      <Typography variant="body2" fontWeight="bold">
                        {asset.criticalMetadata?.name || 'Untitled Asset'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        ID: {asset.assetId} | Version: {asset.versionNumber}
                      </Typography>
                    </Box>
                  ))}
                </Paper>
              </Collapse>
            </Box>

            {deleteReason && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Deletion Reason:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {deleteReason}
                </Typography>
              </Box>
            )}

            <Alert severity="info">
              <Typography variant="body2">
                This operation will require a blockchain transaction. 
                You'll need to sign the transaction with MetaMask to proceed.
              </Typography>
            </Alert>
          </Box>
        );

      case 2:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              <AccountBalanceWallet sx={{ mr: 1, verticalAlign: 'middle' }} />
              Sign Transaction
            </Typography>
            
            <Alert severity="info" sx={{ mb: 3 }}>
              <Typography variant="body2">
                Review the transaction details below and click "Sign Transaction" to proceed with MetaMask.
              </Typography>
            </Alert>

            {/* Assets Summary */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                Assets to Delete: {checkedAssets.size}
              </Typography>
              <Box sx={{ mb: 2 }}>
                {assetsToDelete.slice(0, 3).map((asset) => (
                  <Typography key={asset.assetId} variant="body2" color="text.secondary">
                    • {asset.criticalMetadata?.name || 'Untitled Asset'}
                  </Typography>
                ))}
                {assetsToDelete.length > 3 && (
                  <Typography variant="body2" color="text.secondary">
                    ... and {assetsToDelete.length - 3} more
                  </Typography>
                )}
              </Box>
            </Box>

            <Divider sx={{ mb: 3 }} />

            {/* Network Status */}
            {networkStatus && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Network Status
                </Typography>
                {networkStatus.isCorrectNetwork ? (
                  <Alert severity="success">
                    <Typography variant="body2">
                      Connected to Sepolia Testnet
                    </Typography>
                  </Alert>
                ) : (
                  <Alert severity="warning" action={
                    <Button size="small" onClick={handleNetworkSwitch}>
                      Switch Network
                    </Button>
                  }>
                    <Typography variant="body2">
                      Wrong Network: {networkStatus.networkName}
                    </Typography>
                    <Typography variant="body2">
                      Please switch to Sepolia Testnet to continue.
                    </Typography>
                  </Alert>
                )}
              </Box>
            )}

            {/* Gas Estimate */}
            {gasEstimate && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  <LocalGasStation sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Transaction Cost Estimate
                </Typography>
                <Alert severity="info">
                  <Typography variant="body2">
                    <strong>Estimated Cost:</strong> {gasEstimate.estimatedCostEth} ETH
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Gas Limit: {gasEstimate.estimatedGas.toLocaleString()} | 
                    Gas Price: {(gasEstimate.gasPrice / 1e9).toFixed(1)} Gwei
                  </Typography>
                  <br />
                  <Typography variant="caption" color="text.secondary">
                    Note: Actual cost may vary based on network conditions.
                  </Typography>
                </Alert>
              </Box>
            )}

            {/* Error Display */}
            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                <Typography variant="body2">
                  {error}
                </Typography>
              </Alert>
            )}
          </Box>
        );

      case 3:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              {processing ? 'Processing Batch Deletion...' : 'Batch Deletion Complete'}
            </Typography>
            
            {processing && (
              <Box sx={{ mb: 2 }}>
                <LinearProgress variant="determinate" value={transactionProgress} />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  {currentTransactionStep}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {Math.round(transactionProgress)}% complete
                </Typography>
              </Box>
            )}

            {deleteResults && (
              <Box>
                <Alert 
                  severity={deleteResults.status === 'success' ? 'success' : deleteResults.status === 'partial' ? 'warning' : 'error'} 
                  sx={{ mb: 2 }}
                >
                  <Typography variant="h6" gutterBottom>
                    {deleteResults.status === 'success' ? 'Operation Completed Successfully!' : 
                     deleteResults.status === 'partial' ? 'Operation Partially Completed' : 
                     'Operation Failed'}
                  </Typography>
                  <Typography>
                    {deleteResults.message}
                  </Typography>
                  
                  {(deleteResults.status === 'success' || deleteResults.status === 'partial') && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontStyle: 'italic' }}>
                      Review the results above. When ready, click "Close" to refresh your assets list.
                    </Typography>
                  )}
                  
                  {/* Summary Statistics - Use same calculation as toast */}
                  {(() => {
                    const results = deleteResults.results || {};
                    const syncedCount = Object.values(results).filter(r => r.status === 'synced').length;
                    const deletedCount = Object.values(results).filter(r => r.status === 'success').length;
                    const errorCount = Object.values(results).filter(r => r.status === 'error').length;
                    const totalCount = Object.keys(results).length;
                    const successfulCount = deletedCount + syncedCount;
                    
                    return (
                      <Box sx={{ mt: 1, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                        <Chip 
                          label={`Total: ${totalCount}`} 
                          size="small" 
                          color="primary" 
                          variant="outlined"
                        />
                        <Chip 
                          label={`Successful: ${successfulCount}`} 
                          size="small" 
                          color="success" 
                          variant="outlined"
                        />
                        {errorCount > 0 && (
                          <Chip 
                            label={`Failed: ${errorCount}`} 
                            size="small" 
                            color="error" 
                            variant="outlined"
                          />
                        )}
                        {syncedCount > 0 && (
                          <Chip 
                            label={`Synced: ${syncedCount}`} 
                            size="small" 
                            color="info" 
                            variant="outlined"
                          />
                        )}
                        {deletedCount > 0 && (
                          <Chip 
                            label={`Deleted: ${deletedCount}`} 
                            size="small" 
                            color="success" 
                            variant="filled"
                          />
                        )}
                      </Box>
                    );
                  })()}
                </Alert>
                
                {deleteResults.results && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Detailed Results ({Object.keys(deleteResults.results).length} assets):
                    </Typography>
                    {Object.entries(deleteResults.results).map(([assetId, result]) => (
                      <Box key={assetId} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        {result.status === 'success' ? (
                          <CheckCircle color="success" sx={{ mr: 1 }} />
                        ) : result.status === 'synced' ? (
                          <Info color="info" sx={{ mr: 1 }} />
                        ) : (
                          <Error color="error" sx={{ mr: 1 }} />
                        )}
                        <Typography variant="body2">
                          <strong>{assetId}:</strong> {result.message}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                )}
              </Box>
            )}

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  {error}
                </Typography>
              </Alert>
            )}
          </Box>
        );

      default:
        return null;
    }
  };

  const steps = ['Select Assets', 'Confirm Deletion', 'Sign Transaction', 'Processing'];

  return (
    <Dialog 
        open={open} 
        onClose={handleClose}
        maxWidth="md"
        fullWidth
        disableEscapeKeyDown={processing}
      >
        <DialogTitle sx={{ pb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Delete sx={{ mr: 1, color: 'error.main' }} />
            Batch Delete Assets
          </Box>
          
          <Stepper activeStep={step} sx={{ mt: 2 }}>
            {steps.map((label, index) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </DialogTitle>

        <DialogContent sx={{ pb: 1 }}>
          {getStepContent()}
        </DialogContent>

        <DialogActions>
          {step > 0 && step < 3 && !processing && (
            <Button 
              onClick={handleBack}
              disabled={processing}
            >
              Back
            </Button>
          )}
          
          <Button 
            onClick={handleClose} 
            disabled={processing}
            variant={step === 3 && deleteResults ? 'contained' : 'text'}
            color={step === 3 && deleteResults?.status === 'success' ? 'success' : 'primary'}
          >
            {step === 3 && deleteResults ? 'Close' : 'Cancel'}
          </Button>
          
          {step < 2 && (
            <Button 
              onClick={handleNext}
              variant="contained"
              color={step === 1 ? 'error' : 'primary'}
              disabled={processing || (step === 0 && checkedAssets.size === 0)}
            >
              {step === 0 ? 'Next' : `Delete ${checkedAssets.size} Asset${checkedAssets.size !== 1 ? 's' : ''}`}
            </Button>
          )}
          
          {step === 2 && (
            <Button 
              onClick={handleSignTransaction}
              variant="contained"
              color="error"
              disabled={processing || (networkStatus && !networkStatus.isCorrectNetwork)}
              startIcon={<AccountBalanceWallet />}
            >
              {processing ? 'Processing...' : 'Sign Transaction'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
  );
};

export default BatchDeleteModal;