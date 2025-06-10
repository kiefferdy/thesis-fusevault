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
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
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
import { transactionService } from '../services/transactionService';
import { useAssets } from '../hooks/useAssets';
import { formatDate, formatWalletAddress, formatTransactionHash } from '../utils/formatters';

function AssetDetailPage() {
  const { assetId } = useParams();
  const [asset, setAsset] = useState(null);
  const [version] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const { deleteAsset, isDeleting } = useAssets();
  const navigate = useNavigate();

  // Fetch asset data
  useEffect(() => {
    const fetchAsset = async () => {
      setLoading(true);
      try {
        const assetData = await assetService.retrieveMetadata(assetId, version);
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

  // Fetch asset history when history tab is selected
  useEffect(() => {
    if (tabValue === 1 && assetId) {
      const fetchHistory = async () => {
        setHistoryLoading(true);
        try {
          const historyData = await transactionService.getAssetHistory(assetId);
          setHistory(historyData.transactions || []);
        } catch (err) {
          console.error('Error fetching history:', err);
          toast.error('Error loading transaction history');
        } finally {
          setHistoryLoading(false);
        }
      };

      fetchHistory();
    }
  }, [assetId, tabValue]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleEdit = () => {
    navigate(`/assets/${assetId}/edit`);
  };

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this asset?')) {
      deleteAsset({ 
        assetId: assetId
      }, {
        onSuccess: () => {
          navigate('/dashboard');
        }
      });
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
          Loading asset data...
        </Typography>
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
        
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          {asset.criticalMetadata?.name || 'Asset Details'}
        </Typography>
        
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
            disabled={isDeleting}
          >
            {isDeleting ? 'Deleting...' : 'Delete'}
          </Button>
        </Box>
      </Box>
      
      {/* Integrity Status Alert */}
      {asset.verificationStatus && (
        <Alert
          severity={asset.verificationStatus === 'verified' ? 'success' : 'warning'}
          icon={asset.verificationStatus === 'verified' ? <VerifiedUser /> : <Warning />}
          sx={{ mb: 3 }}
        >
          {asset.verificationStatus === 'verified' 
            ? 'Asset integrity verified on blockchain' 
            : 'Potential integrity issues detected'}
        </Alert>
      )}
      
      <Paper sx={{ mb: 4 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab label="Asset Information" />
          <Tab label="Transaction History" />
        </Tabs>
        
        <Divider />
        
        {/* Asset Information Tab */}
        {tabValue === 0 && (
          <Box sx={{ p: 3 }}>
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
                        <TableCell>{formatWalletAddress(asset.ownerAddress, 6, 4)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell component="th">
                          Created
                        </TableCell>
                        <TableCell>{formatDate(asset.createdAt)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell component="th">
                          Last Modified
                        </TableCell>
                        <TableCell>{formatDate(asset.updatedAt)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell component="th">
                          IPFS CID
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" component="div" sx={{ wordBreak: 'break-all' }}>
                            {asset.ipfsCid}
                          </Typography>
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell component="th">
                          Blockchain TX
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" component="div" sx={{ wordBreak: 'break-all' }}>
                            {asset.blockchainTxHash}
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
        )}
        
        {/* Transaction History Tab */}
        {tabValue === 1 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Transaction History
            </Typography>
            
            {historyLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : history.length === 0 ? (
              <Alert severity="info">No transaction history found</Alert>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell>Action</TableCell>
                      <TableCell>Initiator</TableCell>
                      <TableCell>Version</TableCell>
                      <TableCell>Blockchain TX</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {history.map((tx) => (
                      <TableRow key={tx._id || tx.id}>
                        <TableCell>{formatDate(tx.timestamp)}</TableCell>
                        <TableCell>
                          <Chip 
                            label={tx.action}
                            color={tx.action === 'CREATE' ? 'success' : 
                                  tx.action === 'UPDATE' ? 'info' : 
                                  tx.action === 'DELETE' ? 'error' : 'default'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{formatWalletAddress(tx.walletAddress)}</TableCell>
                        <TableCell>{tx.metadata?.versionNumber || '1'}</TableCell>
                        <TableCell>
                          {tx.blockchainTxHash ? (
                            formatTransactionHash(tx.blockchainTxHash)
                          ) : (
                            <Typography variant="body2" color="text.secondary">
                              N/A
                            </Typography>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        )}
      </Paper>
    </Container>
  );
}

export default AssetDetailPage;