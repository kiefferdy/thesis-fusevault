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
  StepLabel
} from '@mui/material';
import {
  Delete,
  Warning,
  CheckCircle,
  Error,
  ExpandMore,
  ExpandLess,
  Info
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import TransactionSigner from './TransactionSigner';
import { useTransactionSigner } from '../hooks/useTransactionSigner';

const BatchDeleteModal = ({ 
  open, 
  onClose, 
  selectedAssets = [],
  onDeleteSuccess 
}) => {
  const [deleteReason, setDeleteReason] = useState('');
  const [checkedAssets, setCheckedAssets] = useState(new Set());
  const [processing, setProcessing] = useState(false);
  const [step, setStep] = useState(0); // 0: select, 1: confirm, 2: processing
  const [expandedWarnings, setExpandedWarnings] = useState(false);
  const [deleteResults, setDeleteResults] = useState(null);
  const { currentAccount } = useAuth();
  
  const {
    isVisible,
    operation,
    operationData,
    showBatchDeleteSigner,
    hideSigner,
    onSuccess,
    onError
  } = useTransactionSigner();

  // Initialize checked assets when modal opens or assets change
  useEffect(() => {
    if (open && selectedAssets.length > 0) {
      setCheckedAssets(new Set(selectedAssets.map(asset => asset.assetId)));
      setStep(0);
      setDeleteResults(null);
      setProcessing(false);
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
    }
  }, [open]);

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
      handleDelete();
    }
  };

  const handleBack = () => {
    if (step > 0) {
      setStep(step - 1);
    }
  };

  const handleDelete = () => {
    const assetsToDelete = getCheckedAssets();
    const assetIds = assetsToDelete.map(asset => asset.assetId);
    
    setProcessing(true);
    setStep(2);
    
    // Show the transaction signer for batch delete
    showBatchDeleteSigner(
      assetIds,
      currentAccount,
      deleteReason || 'Batch deletion',
      (result) => {
        console.log('Batch delete successful:', result);
        setDeleteResults(result);
        setProcessing(false);
        toast.success(`Successfully deleted ${result.success_count || result.successCount || 0} assets!`);
        
        // Call success callback
        if (onDeleteSuccess) {
          onDeleteSuccess(result);
        }
        
        // Auto-close after a delay
        setTimeout(() => {
          onClose();
        }, 2000);
      },
      (error) => {
        console.error('Batch delete failed:', error);
        setProcessing(false);
        
        let friendlyMessage = 'Batch delete failed';
        if (error?.message) {
          friendlyMessage = error.message;
        }
        toast.error(friendlyMessage);
        
        // Go back to confirm step on error
        setStep(1);
      }
    );
  };

  const handleClose = () => {
    if (!processing && !isVisible) {
      onClose();
    }
  };

  const getStepContent = () => {
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
        const assetsToDelete = getCheckedAssets();
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
              {processing ? 'Processing Batch Deletion...' : 'Batch Deletion Complete'}
            </Typography>
            
            {processing && (
              <Box sx={{ mb: 2 }}>
                <LinearProgress />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Please sign the transaction in MetaMask to proceed...
                </Typography>
              </Box>
            )}

            {deleteResults && (
              <Box>
                <Alert 
                  severity={deleteResults.status === 'success' ? 'success' : 'warning'} 
                  sx={{ mb: 2 }}
                >
                  <Typography>
                    {deleteResults.message}
                  </Typography>
                </Alert>
                
                {deleteResults.results && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Results:
                    </Typography>
                    {Object.entries(deleteResults.results).map(([assetId, result]) => (
                      <Box key={assetId} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        {result.status === 'success' ? (
                          <CheckCircle color="success" sx={{ mr: 1 }} />
                        ) : (
                          <Error color="error" sx={{ mr: 1 }} />
                        )}
                        <Typography variant="body2">
                          {assetId}: {result.message}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                )}
              </Box>
            )}
          </Box>
        );

      default:
        return null;
    }
  };

  const steps = ['Select Assets', 'Confirm Deletion', 'Processing'];

  return (
    <>
      <Dialog 
        open={open} 
        onClose={handleClose}
        maxWidth="md"
        fullWidth
        disableEscapeKeyDown={processing || isVisible}
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
          {step > 0 && step < 2 && (
            <Button 
              onClick={handleBack}
              disabled={processing || isVisible}
            >
              Back
            </Button>
          )}
          
          <Button 
            onClick={handleClose} 
            disabled={processing || isVisible}
          >
            {step === 2 && deleteResults ? 'Close' : 'Cancel'}
          </Button>
          
          {step < 2 && (
            <Button 
              onClick={handleNext}
              variant="contained"
              color={step === 1 ? 'error' : 'primary'}
              disabled={processing || isVisible || (step === 0 && checkedAssets.size === 0)}
            >
              {step === 0 ? 'Next' : `Delete ${checkedAssets.size} Asset${checkedAssets.size !== 1 ? 's' : ''}`}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Transaction Signer Modal */}
      <TransactionSigner
        operation={operation}
        operationData={operationData}
        onSuccess={onSuccess}
        onError={onError}
        onCancel={hideSigner}
        isVisible={isVisible}
      />
    </>
  );
};

export default BatchDeleteModal;