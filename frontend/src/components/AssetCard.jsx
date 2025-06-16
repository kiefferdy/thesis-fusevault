import { useState } from 'react';
import { 
  Card, 
  CardHeader, 
  CardContent, 
  CardActions, 
  Typography,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  Box
} from '@mui/material';
import { Delete, Edit, History, Visibility } from '@mui/icons-material';
import { formatDate, formatTransactionHash } from '../utils/formatters';
import { useNavigate } from 'react-router-dom';
import { useAssets } from '../hooks/useAssets';
import { useTransactionSigner } from '../hooks/useTransactionSigner';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';
import TransactionSigner from './TransactionSigner';

function AssetCard({ asset }) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteReason, setDeleteReason] = useState('');
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

  const handleView = () => {
    navigate(`/assets/${asset.assetId}`);
  };

  const handleEdit = () => {
    navigate(`/assets/${asset.assetId}/edit`);
  };

  const handleHistory = () => {
    navigate(`/assets/${asset.assetId}/history`);
  };

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    // Close the dialog first
    setDeleteDialogOpen(false);
    
    // Show the transaction signer with the reason
    showDeleteSigner(
      asset.assetId,
      currentAccount,
      deleteReason || 'User requested deletion',
      (result) => {
        console.log('Delete successful:', result);
        toast.success('Asset deleted successfully!');
        setDeleteReason('');
        // Note: AssetCard doesn't need to navigate, parent component should handle refresh
      },
      (error) => {
        console.error('Delete failed:', error);
        let errorMessage = 'Delete failed';
        if (error?.message) {
          errorMessage = error.message;
        }
        toast.error(errorMessage);
        // Reopen dialog on error so user can try again
        setDeleteDialogOpen(true);
      }
    );
  };

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardHeader
        title={asset.criticalMetadata.name || 'Untitled Asset'}
        subheader={`ID: ${asset.assetId} | Version: ${asset.versionNumber}`}
      />
      
      <CardContent sx={{ flexGrow: 1 }}>
        {asset.criticalMetadata.description && (
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {asset.criticalMetadata.description}
          </Typography>
        )}
        
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Created: {formatDate(asset.createdAt)}
          </Typography>
        </Box>
        
        {asset.blockchainTxHash && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              TX: {formatTransactionHash(asset.blockchainTxHash)}
            </Typography>
          </Box>
        )}
        
        {/* Display tags if available */}
        {asset.criticalMetadata.tags && (
          <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {asset.criticalMetadata.tags.map((tag, index) => (
              <Chip key={index} label={tag} size="small" />
            ))}
          </Box>
        )}
      </CardContent>
      
      <CardActions>
        <IconButton onClick={handleView} title="View Asset">
          <Visibility />
        </IconButton>
        <IconButton onClick={handleEdit} title="Edit Asset">
          <Edit />
        </IconButton>
        <IconButton onClick={handleHistory} title="View History">
          <History />
        </IconButton>
        <IconButton onClick={handleDeleteClick} title="Delete Asset" sx={{ marginLeft: 'auto' }}>
          <Delete />
        </IconButton>
      </CardActions>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            Are you sure you want to delete this asset? This operation can be reversed by creating a new version.
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            id="reason"
            label="Reason for deletion (optional)"
            type="text"
            fullWidth
            variant="outlined"
            value={deleteReason}
            onChange={(e) => setDeleteReason(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleDeleteConfirm} 
            color="error" 
            disabled={isVisible}
          >
            {isVisible ? 'Processing...' : 'Delete'}
          </Button>
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
    </Card>
  );
}

export default AssetCard;