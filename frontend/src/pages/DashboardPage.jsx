import { useState, useEffect } from 'react';
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
  Divider,
  Avatar,
  Chip,
  IconButton,
  CardActions,
  CardHeader,
  Tooltip,
  Stack,
  Alert,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { 
  AddCircleOutline, 
  Search, 
  TrendingUp, 
  Storage, 
  SwapHoriz,
  DeleteOutline,
  Update,
  CloudUpload,
  MoreVert,
  Check,
  Timeline,
  Person,
  GitHub,
  Twitter,
  LinkedIn,
  Work
} from '@mui/icons-material';
import AssetCard from '../components/AssetCard';
import TransactionsList from '../components/TransactionsList';
import { useAssets } from '../hooks/useAssets';
import { useTransactions } from '../hooks/useTransactions';
import { useAuth } from '../contexts/AuthContext';
import { useUser } from '../hooks/useUser';
import { formatWalletAddress, formatDate } from '../utils/formatters';

function DashboardPage() {
  const [tabValue, setTabValue] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [openSetupDialog, setOpenSetupDialog] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const { currentAccount, isAuthenticated, backendAvailable } = useAuth();
  const { user, isLoading: userLoading, register, isRegistering, error: userError } = useUser();
  const { assets, isLoading: assetsLoading } = useAssets();
  const { 
    summary, 
    recentTransactions, 
    isSummaryLoading, 
    isRecentLoading 
  } = useTransactions();
  const navigate = useNavigate();
  
  // Check if we need to show the setup dialog
  useEffect(() => {
    // If user data failed to load and we're not already registering
    if (userError && !userLoading && !isRegistering && currentAccount && backendAvailable) {
      setOpenSetupDialog(true);
    }
  }, [userError, userLoading, isRegistering, currentAccount, backendAvailable]);
  
  // Handle setup form submission
  const handleSetupSubmit = () => {
    if (email) {
      register({
        wallet_address: currentAccount,
        email: email,
        name: name || 'FuseVault User',
        role: 'user'
      });
      setOpenSetupDialog(false);
    }
  };

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Filter assets based on search term
  console.log("Dashboard assets:", assets);
  
  const filteredAssets = assets.filter(asset => {
    if (!asset) return false;
    
    const assetIdMatch = asset.assetId?.toLowerCase().includes(searchTerm.toLowerCase());
    const nameMatch = asset.criticalMetadata?.name?.toLowerCase().includes(searchTerm.toLowerCase());
    const tagMatch = asset.criticalMetadata?.tags && 
      asset.criticalMetadata.tags.some(tag => 
        tag.toLowerCase().includes(searchTerm.toLowerCase())
      );
      
    return assetIdMatch || nameMatch || tagMatch;
  });

  // Get avatar component
  const getAvatar = () => {
    if (user?.profile_image) {
      return (
        <Avatar src={user.profile_image} alt={user.name || 'User'} />
      );
    } else if (user?.name) {
      const initials = user.name.split(' ').map(n => n[0]).join('').toUpperCase();
      return (
        <Avatar sx={{ bgcolor: 'primary.main' }}>{initials}</Avatar>
      );
    } else {
      return (
        <Avatar><Person /></Avatar>
      );
    }
  };

  // Calculate storage usage percentage
  const storageUsage = Math.min(
    ((summary?.total_asset_size || 0) / (100 * 1024 * 1024)) * 100, 
    100
  ); // Assuming 100MB limit for demo

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Profile Setup Dialog */}
      <Dialog open={openSetupDialog} onClose={() => setOpenSetupDialog(false)}>
        <DialogTitle>Welcome to FuseVault</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Please set up your profile to continue. This information will be associated with your wallet address.
          </DialogContentText>
          <TextField
            autoFocus
            margin="dense"
            label="Email Address"
            type="email"
            fullWidth
            variant="outlined"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            sx={{ mb: 2, mt: 2 }}
          />
          <TextField
            margin="dense"
            label="Your Name (Optional)"
            type="text"
            fullWidth
            variant="outlined"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleSetupSubmit} disabled={!email || isRegistering} variant="contained">
            {isRegistering ? 'Setting up...' : 'Continue'}
          </Button>
        </DialogActions>
      </Dialog>

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

      {!backendAvailable && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Running in demo mode. Some features may be limited.
        </Alert>
      )}
      
      {/* User Profile Summary Card & Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* User profile card */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardHeader
              avatar={getAvatar()}
              title={user?.name || 'Welcome!'}
              subheader={user ? 
                (user.job_title ? `${user.job_title}${user.organization ? ` at ${user.organization}` : ''}` : 
                (user.organization || formatWalletAddress(currentAccount, 6, 4))) : 
                formatWalletAddress(currentAccount, 6, 4)
              }
            />
            <CardContent>
              {userLoading ? (
                <CircularProgress size={20} />
              ) : (
                <>
                  {user?.bio && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {user.bio.length > 150 ? `${user.bio.substring(0, 150)}...` : user.bio}
                    </Typography>
                  )}
                  
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
                    {user?.location && (
                      <Chip 
                        label={user.location} 
                        size="small" 
                        variant="outlined" 
                      />
                    )}
                    {user?.created_at && (
                      <Chip 
                        label={`Joined ${new Date(user.created_at).toLocaleDateString()}`} 
                        size="small" 
                        variant="outlined" 
                      />
                    )}
                  </Stack>
                  
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    {user?.github && (
                      <Tooltip title={`GitHub: ${user.github}`}>
                        <IconButton 
                          size="small" 
                          color="default"
                          component="a"
                          href={`https://github.com/${user.github}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <GitHub fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {user?.twitter && (
                      <Tooltip title={`Twitter: ${user.twitter}`}>
                        <IconButton 
                          size="small" 
                          color="primary"
                          component="a"
                          href={`https://twitter.com/${user.twitter.replace('@', '')}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Twitter fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {user?.linkedin && (
                      <Tooltip title="LinkedIn Profile">
                        <IconButton 
                          size="small" 
                          color="primary"
                          component="a"
                          href={user.linkedin.startsWith('http') ? user.linkedin : `https://linkedin.com/in/${user.linkedin}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <LinkedIn fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </>
              )}
            </CardContent>
            <CardActions>
              <Button 
                size="small" 
                onClick={() => navigate('/profile')}
              >
                Edit Profile
              </Button>
            </CardActions>
          </Card>
        </Grid>

        {/* Stats */}
        <Grid item xs={12} md={8}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Card sx={{ bgcolor: 'primary.light', color: 'primary.contrastText' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Box>
                      <Typography variant="subtitle2" sx={{ opacity: 0.8 }}>
                        Total Assets
                      </Typography>
                      <Typography variant="h4">
                        {isSummaryLoading ? <CircularProgress size={24} color="inherit" /> : (summary.unique_assets || 0)}
                      </Typography>
                    </Box>
                    <Avatar sx={{ bgcolor: 'primary.dark' }}>
                      <Storage />
                    </Avatar>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <Card sx={{ bgcolor: 'secondary.light', color: 'secondary.contrastText' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Box>
                      <Typography variant="subtitle2" sx={{ opacity: 0.8 }}>
                        Total Transactions
                      </Typography>
                      <Typography variant="h4">
                        {isSummaryLoading ? <CircularProgress size={24} color="inherit" /> : (summary.total_transactions || 0)}
                      </Typography>
                    </Box>
                    <Avatar sx={{ bgcolor: 'secondary.dark' }}>
                      <SwapHoriz />
                    </Avatar>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Storage Usage
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={storageUsage} 
                    sx={{ height: 10, borderRadius: 5, mb: 1 }} 
                  />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">
                      {((summary?.total_asset_size || 0) / (1024 * 1024)).toFixed(2)} MB used
                    </Typography>
                    <Typography variant="body2">
                      100 MB limit
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Action Breakdown
                  </Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-around', py: 1 }}>
                    {isSummaryLoading ? (
                      <CircularProgress size={24} />
                    ) : (
                      <>
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                          <Avatar sx={{ bgcolor: 'success.light', mb: 1, width: 36, height: 36 }}>
                            <CloudUpload fontSize="small" />
                          </Avatar>
                          <Typography variant="h6">
                            {summary.actions?.CREATE || 0}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Creates
                          </Typography>
                        </Box>
                        
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                          <Avatar sx={{ bgcolor: 'info.light', mb: 1, width: 36, height: 36 }}>
                            <Update fontSize="small" />
                          </Avatar>
                          <Typography variant="h6">
                            {summary.actions?.UPDATE || 0}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Updates
                          </Typography>
                        </Box>
                        
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                          <Avatar sx={{ bgcolor: 'error.light', mb: 1, width: 36, height: 36 }}>
                            <DeleteOutline fontSize="small" />
                          </Avatar>
                          <Typography variant="h6">
                            {summary.actions?.DELETE || 0}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Deletes
                          </Typography>
                        </Box>
                      </>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
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
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Recent Transactions
              </Typography>
              
              {recentTransactions.length > 0 && (
                <Button 
                  variant="outlined"
                  size="small"
                  endIcon={<Timeline />}
                  onClick={() => navigate('/history')}
                >
                  View Full History
                </Button>
              )}
            </Box>
            
            <TransactionsList 
              transactions={recentTransactions} 
              isLoading={isRecentLoading} 
            />
          </Box>
        )}
      </Paper>
    </Container>
  );
}

export default DashboardPage;