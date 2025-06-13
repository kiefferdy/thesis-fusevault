import { useState, useEffect, useMemo } from 'react';
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
import { formatWalletAddress } from '../utils/formatters';

function DashboardPage() {
  const [tabValue, setTabValue] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [openSetupDialog, setOpenSetupDialog] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const { currentAccount } = useAuth();
  const { user, isLoading: userLoading, register, isRegistering, error: userError } = useUser();
  const { assets, isLoading: assetsLoading } = useAssets();
  const {
    summary,
    recentTransactions,
    allTransactions,
    isSummaryLoading,
    isRecentLoading,
    getAllTransactions
  } = useTransactions();

  // Fetch all transactions when dashboard loads
  useEffect(() => {
    if (currentAccount) {
      getAllTransactions();
    }
  }, [currentAccount, getAllTransactions]);

  // Calculate action counts from all transactions
  const actionCounts = useMemo(() => {
    if (!allTransactions || allTransactions.length === 0) {
      return summary.actions || {};
    }

    const counts = {};
    allTransactions.forEach(tx => {
      if (tx.action) {
        // Group similar actions (e.g., CREATE, VERSION_CREATE would both count toward 'CREATE')
        let actionType = tx.action;
        if (actionType.includes('CREATE')) actionType = 'CREATE';
        else if (actionType.includes('UPDATE')) actionType = 'UPDATE';
        else if (actionType.includes('DELETE')) actionType = 'DELETE';

        counts[actionType] = (counts[actionType] || 0) + 1;
      }
    });

    return counts;
  }, [allTransactions, summary.actions]);

  const navigate = useNavigate();

  // Check if we need to show the setup dialog
  useEffect(() => {
    // If user data failed to load and we're not already registering
    if (userError && !userLoading && !isRegistering && currentAccount) {
      setOpenSetupDialog(true);
    }
  }, [userError, userLoading, isRegistering, currentAccount]);

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

  // Handle search input change
  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  // Filter assets based on search term
  const filteredAssets = assets.filter(asset => {
    if (!searchTerm) return true;

    const searchLower = searchTerm.toLowerCase();
    return (
      asset.criticalMetadata?.name?.toLowerCase().includes(searchLower) ||
      asset.assetId?.toLowerCase().includes(searchLower) ||
      asset.criticalMetadata?.tags?.some(tag => tag.toLowerCase().includes(searchLower))
    );
  });

  if (userLoading) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Welcome Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Welcome back{user?.name ? `, ${user.name}` : ''}!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Here's an overview of your digital assets and recent activity.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* User Profile Card */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: 'fit-content' }}>
            <CardHeader
              avatar={
                <Avatar sx={{ bgcolor: 'primary.main' }}>
                  {user?.name ? user.name.charAt(0).toUpperCase() : <Person />}
                </Avatar>
              }
              title={user?.name || 'FuseVault User'}
              subheader={formatWalletAddress(currentAccount)}
            />
            <CardContent>
              {userLoading ? (
                <CircularProgress size={24} />
              ) : (
                <>
                  {user?.bio && (
                    <Typography variant="body2" color="text.secondary" paragraph>
                      {user.bio}
                    </Typography>
                  )}

                  {user?.organization && (
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Work sx={{ mr: 1, fontSize: 16 }} />
                      <Typography variant="body2">
                        {user.job_title ? `${user.job_title} at ${user.organization}` : user.organization}
                      </Typography>
                    </Box>
                  )}

                  <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                    {user?.github && (
                      <Tooltip title="GitHub">
                        <IconButton
                          size="small"
                          component="a"
                          href={user.github.startsWith('http') ? user.github : `https://github.com/${user.github}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <GitHub fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {user?.twitter && (
                      <Tooltip title="Twitter">
                        <IconButton
                          size="small"
                          component="a"
                          href={user.twitter.startsWith('http') ? user.twitter : `https://twitter.com/${user.twitter}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Twitter fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {user?.linkedin && (
                      <Tooltip title="LinkedIn">
                        <IconButton
                          size="small"
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
            {/* Total Assets Card - CLICKABLE */}
            <Grid item xs={12} sm={6}>
              <Card
                sx={{
                  bgcolor: 'primary.light',
                  color: 'primary.contrastText',
                  cursor: 'pointer',
                  '&:hover': {
                    bgcolor: 'primary.main',
                    transform: 'translateY(-2px)',
                    transition: 'all 0.2s ease-in-out'
                  }
                }}
                onClick={() => {
                  // Scroll to assets section
                  const assetsSection = document.getElementById('assets-section');
                  if (assetsSection) {
                    assetsSection.scrollIntoView({ behavior: 'smooth' });
                  }
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Box>
                      <Typography variant="subtitle2" sx={{ opacity: 0.8 }}>
                        Total Assets
                      </Typography>
                      <Typography variant="h4">
                        {isSummaryLoading || assetsLoading ?
                          <CircularProgress size={24} color="inherit" /> :
                          (filteredAssets.length || assets.length || summary?.total_assets || 0)
                        }
                      </Typography>
                    </Box>
                    <Avatar sx={{ bgcolor: 'primary.dark' }}>
                      <Storage />
                    </Avatar>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Total Transactions Card - CLICKABLE */}
            <Grid item xs={12} sm={6}>
              <Card
                sx={{
                  bgcolor: 'secondary.light',
                  color: 'secondary.contrastText',
                  cursor: 'pointer',
                  '&:hover': {
                    bgcolor: 'secondary.main',
                    transform: 'translateY(-2px)',
                    transition: 'all 0.2s ease-in-out'
                  }
                }}
                onClick={() => navigate('/history')}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Box>
                      <Typography variant="subtitle2" sx={{ opacity: 0.8 }}>
                        Total Transactions
                      </Typography>
                      <Typography variant="h4">
                        {isSummaryLoading ?
                          <CircularProgress size={24} color="inherit" /> :
                          (allTransactions.length || summary?.total_transactions || 0)
                        }
                      </Typography>
                    </Box>
                    <Avatar sx={{ bgcolor: 'secondary.dark' }}>
                      <Timeline />
                    </Avatar>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Paper sx={{ p: 3, mt: 4 }}>
        <Typography variant="h6" gutterBottom>
          Quick Actions
        </Typography>
        <Grid container spacing={2}>
          <Grid item>
            <Button
              variant="contained"
              startIcon={<AddCircleOutline />}
              onClick={() => navigate('/upload')}
            >
              Create Asset
            </Button>
          </Grid>
          <Grid item>
            <Button
              variant="outlined"
              startIcon={<Timeline />}
              onClick={() => navigate('/history')}
            >
              View History
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Main Content Area */}
      <Paper sx={{ mt: 4 }}>
        <Tabs value={tabValue} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab label="My Assets" />
          <Tab label="Recent Activity" />
        </Tabs>

        {/* Assets Tab */}
        {tabValue === 0 && (
          <Box id="assets-section" sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Your Assets ({assets.length})
              </Typography>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <TextField
                  size="small"
                  placeholder="Search assets..."
                  value={searchTerm}
                  onChange={handleSearchChange}
                  InputProps={{
                    startAdornment: <Search sx={{ color: 'action.active', mr: 1 }} />
                  }}
                />
                <Button
                  variant="contained"
                  startIcon={<AddCircleOutline />}
                  onClick={() => navigate('/upload')}
                >
                  Create Asset
                </Button>
              </Box>
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

      {/* User Setup Dialog */}
      <Dialog open={openSetupDialog} onClose={() => setOpenSetupDialog(false)}>
        <DialogTitle>Complete Your Profile</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Welcome to FuseVault! Let's set up your profile to get started.
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
          />
          <TextField
            margin="dense"
            label="Name (Optional)"
            type="text"
            fullWidth
            variant="outlined"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenSetupDialog(false)}>Skip</Button>
          <Button
            onClick={handleSetupSubmit}
            variant="contained"
            disabled={!email || isRegistering}
          >
            {isRegistering ? 'Creating...' : 'Complete Setup'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default DashboardPage;