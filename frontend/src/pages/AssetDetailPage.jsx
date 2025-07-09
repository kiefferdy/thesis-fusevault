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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip
} from '@mui/material';
import {
  Edit,
  Delete,
  ArrowBack,
  History,
  VerifiedUser,
  Warning
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

  // Simulate recovery progress messages
  const simulateRecoveryProgress = async () => {
    const messages = [
      'Unable to verify asset authenticity...',
      'Restoring metadata from IPFS...',
      'Searching blockchain transaction history...',
      'Searching blockchain event logs...',
      'Asset metadata restored successfully'
    ];

    for (let i = 0; i < messages.length; i++) {
      setRecoveryMessage(messages[i]);
      await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second delay between messages
    }
  };

  // Fetch asset data
  useEffect(() => {
    const fetchAsset = async () => {
      setLoading(true);
      setRecoveryMessage('Loading asset data...');
      setRecoveryStatus(null);
      
      try {
        const assetData = await assetService.retrieveMetadata(assetId, version);
        
        // Check if recovery was performed
        if (assetData.verification && assetData.verification.recoveryNeeded) {
          setRecoveryStatus('recovered');
          // If recovery was needed, simulate the progress messages the user would have seen
          if (assetData.verification.recoverySuccessful) {
            await simulateRecoveryProgress();
          } else {
            setRecoveryMessage('Recovery failed - showing potentially compromised data');
          }
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
      <Container maxWidth="lg" sx={{ py: 4, textAlign: 'center' }}>
        <CircularProgress />
        <Typography variant="body1" mt={2}>
          {recoveryMessage}
        </Typography>
        {recoveryStatus === 'recovered' && (
          <Typography variant="body2" color="text.secondary" mt={1}>
            This may take a moment while we ensure data integrity...
          </Typography>
        )}
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">{error}</Alert>
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Button variant="contained" onClick={handleBack}>
            Back to Dashboard
          </Button>
        </Box>
      </Container>
    );
  }

  if (!asset) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="warning">Asset not found</Alert>
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Button variant="contained" onClick={handleBack}>
            Back to Dashboard
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={handleBack}
          sx={{ mr: 2 }}
        >
          Back
        </Button>

        <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h4" component="h1">
            {asset.criticalMetadata?.name || 'Asset Details'}
          </Typography>
          {recoveryStatus === 'recovered' && asset.verification?.recoverySuccessful && (
            <Tooltip title="Asset metadata was automatically restored from blockchain due to potential tampering. Click to view recovery details in transaction history.">
              <Chip
                icon={<Warning />}
                label="Metadata Restored"
                color="warning"
                size="small"
                variant="outlined"
                clickable
                onClick={() => navigate(`/assets/${assetId}/history`)}
                sx={{ cursor: 'pointer' }}
              />
            </Tooltip>
          )}
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<Edit />}
            onClick={handleEdit}
          >
            Edit
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<Delete />}
            onClick={handleDelete}
            disabled={isVisible}
          >
            {isVisible ? 'Processing...' : 'Delete'}
          </Button>
        </Box>
      </Box>


      <Paper sx={{ mb: 4 }}>
        {/* Asset Information */}
        <Box sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Asset Information
          </Typography>
          <Divider sx={{ mb: 3 }} />
          <Grid container spacing={3}>
              {/* Basic Information */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Basic Information
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table>
                    <TableBody>
                      <TableRow>
                        <TableCell component="th" width="30%">
                          Asset ID
                        </TableCell>
                        <TableCell>{asset.assetId}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell component="th">
                          Version
                        </TableCell>
                        <TableCell>{asset.versionNumber || 1}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell component="th">
                          Owner
                        </TableCell>
                        <TableCell>{formatWalletAddress(asset.walletAddress, 6, 4)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell component="th">
                          Created
                        </TableCell>
                        <TableCell>{asset.createdAt ? formatDate(asset.createdAt) : 'N/A'}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell component="th">
                          Last Modified
                        </TableCell>
                        <TableCell>{asset.updatedAt ? formatDate(asset.updatedAt) : 'N/A'}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell component="th">
                          IPFS CID
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" component="div" sx={{ wordBreak: 'break-all' }}>
                            {asset.ipfsHash}
                          </Typography>
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell component="th">
                          Blockchain TX
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" component="div" sx={{ wordBreak: 'break-all' }}>
                            {asset.blockchainTxId}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Grid>

              {/* Critical Metadata */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Critical Metadata (Blockchain-Verified)
                </Typography>

                <TableContainer component={Paper} variant="outlined">
                  <Table>
                    <TableBody>
                      {asset.criticalMetadata && Object.entries(asset.criticalMetadata).map(([key, value]) => (
                        <TableRow key={key}>
                          <TableCell component="th" width="30%">
                            {key}
                          </TableCell>
                          <TableCell>
                            {Array.isArray(value) ? (
                              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                {value.map((item, index) => (
                                  <Chip key={index} label={item} size="small" />
                                ))}
                              </Box>
                            ) : (
                              <Typography variant="body2" component="div" sx={{ wordBreak: 'break-all' }}>
                                {typeof value === 'object' ? JSON.stringify(value) : value}
                              </Typography>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Grid>

              {/* Non-Critical Metadata */}
              {asset.nonCriticalMetadata && Object.keys(asset.nonCriticalMetadata).length > 0 && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Additional Metadata
                  </Typography>

                  <TableContainer component={Paper} variant="outlined">
                    <Table>
                      <TableBody>
                        {Object.entries(asset.nonCriticalMetadata).map(([key, value]) => (
                          <TableRow key={key}>
                            <TableCell component="th" width="30%">
                              {key}
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" component="div" sx={{ wordBreak: 'break-all' }}>
                                {typeof value === 'object' ? JSON.stringify(value) : value}
                              </Typography>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Grid>
              )}
            </Grid>
          </Box>
      </Paper>

      {/* Transaction Signer Modal */}
      <TransactionSigner
        operation={operation}
        operationData={operationData}
        onSuccess={onSuccess}
        onError={onError}
        onCancel={hideSigner}
        isVisible={isVisible}
      />
    </Container>
  );
}

export default AssetDetailPage;