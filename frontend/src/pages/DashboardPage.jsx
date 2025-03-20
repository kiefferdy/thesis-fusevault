import { useState } from 'react';
import { 
  Container, 
  Typography, 
  Box, 
  Grid,
  Paper,
  Button,
  TextField,
  CircularProgress,
  Tabs,
  Tab,
  Card,
  CardContent,
  Divider
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { AddCircleOutline, Search } from '@mui/icons-material';
import AssetCard from '../components/AssetCard';
import TransactionsList from '../components/TransactionsList';
import { useAssets } from '../hooks/useAssets';
import { useTransactions } from '../hooks/useTransactions';
import { useAuth } from '../contexts/AuthContext';
import { formatWalletAddress } from '../utils/formatters';

function DashboardPage() {
  const [tabValue, setTabValue] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const { currentAccount } = useAuth();
  const { assets, isLoading: assetsLoading } = useAssets();
  const { 
    summary, 
    recentTransactions, 
    isSummaryLoading, 
    isRecentLoading 
  } = useTransactions();
  const navigate = useNavigate();

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Filter assets based on search term
  const filteredAssets = assets.filter(asset => 
    asset.assetId.toLowerCase().includes(searchTerm.toLowerCase()) ||
    asset.criticalMetadata?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (asset.criticalMetadata?.tags && 
      asset.criticalMetadata.tags.some(tag => 
        tag.toLowerCase().includes(searchTerm.toLowerCase())
      ))
  );

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          Dashboard
        </Typography>
        
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddCircleOutline />}
          onClick={() => navigate('/upload')}
        >
          Create New Asset
        </Button>
      </Box>
      
      {/* Stats Summary */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Total Assets
              </Typography>
              <Typography variant="h4">
                {isSummaryLoading ? <CircularProgress size={24} /> : (summary.unique_assets || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Total Transactions
              </Typography>
              <Typography variant="h4">
                {isSummaryLoading ? <CircularProgress size={24} /> : (summary.total_transactions || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Wallet
              </Typography>
              <Typography variant="h6" noWrap>
                {currentAccount ? formatWalletAddress(currentAccount, 8, 6) : 'Not connected'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Actions
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                {isSummaryLoading ? (
                  <CircularProgress size={24} />
                ) : (
                  Object.entries(summary.actions || {}).map(([action, count]) => (
                    <Typography key={action} variant="body2">
                      {action}: {count}
                    </Typography>
                  ))
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      
      {/* Main content */}
      <Paper sx={{ mb: 4 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab label="My Assets" />
          <Tab label="Recent Activity" />
        </Tabs>
        
        <Divider />
        
        {/* Assets Tab */}
        {tabValue === 0 && (
          <Box sx={{ p: 3 }}>
            <Box sx={{ mb: 3 }}>
              <TextField
                fullWidth
                placeholder="Search by asset ID, name, or tags"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: <Search color="action" sx={{ mr: 1 }} />
                }}
              />
            </Box>
            
            {assetsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : filteredAssets.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body1" paragraph>
                  No assets found. 
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<AddCircleOutline />}
                  onClick={() => navigate('/upload')}
                >
                  Create Your First Asset
                </Button>
              </Box>
            ) : (
              <Grid container spacing={3}>
                {filteredAssets.map((asset) => (
                  <Grid item xs={12} sm={6} md={4} key={asset._id || asset.id}>
                    <AssetCard asset={asset} />
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>
        )}
        
        {/* Recent Activity Tab */}
        {tabValue === 1 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Transactions
            </Typography>
            
            <TransactionsList 
              transactions={recentTransactions} 
              isLoading={isRecentLoading} 
            />
            
            {recentTransactions.length > 0 && (
              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Button 
                  variant="outlined"
                  onClick={() => navigate('/history')}
                >
                  View Full History
                </Button>
              </Box>
            )}
          </Box>
        )}
      </Paper>
    </Container>
  );
}

export default DashboardPage;