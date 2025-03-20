import { useState } from 'react';
import { 
  Container, 
  Typography, 
  Box, 
  Paper, 
  Grid, 
  TextField, 
  Button, 
  Divider, 
  Avatar, 
  CircularProgress,
  Alert
} from '@mui/material';
import { Save, AccountCircle } from '@mui/icons-material';
import { useUser } from '../hooks/useUser';
import { useAuth } from '../contexts/AuthContext';
import { useTransactions } from '../hooks/useTransactions';
import { formatWalletAddress } from '../utils/formatters';

function ProfilePage() {
  const { user, isLoading, isError, update, isUpdating } = useUser();
  const { currentAccount, signOut } = useAuth();
  const { summary, isSummaryLoading } = useTransactions();
  
  // Initialize form data from user data
  const [formData, setFormData] = useState({
    email: user?.email || '',
    name: user?.name || '',
    organization: user?.organization || '',
    bio: user?.bio || ''
  });

  // Handle form changes
  const handleChange = (field) => (event) => {
    setFormData({
      ...formData,
      [field]: event.target.value
    });
  };

  // Handle form submission
  const handleSubmit = (event) => {
    event.preventDefault();
    
    // Remove empty fields to avoid overwriting with empty values
    const updateData = {};
    Object.entries(formData).forEach(([key, value]) => {
      if (value) updateData[key] = value;
    });
    
    update(updateData);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Profile Settings
      </Typography>
      
      <Grid container spacing={4}>
        {/* Profile Information Section */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" component="h2" gutterBottom>
              Personal Information
            </Typography>
            
            {isLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : isError ? (
              <Alert severity="error" sx={{ mb: 3 }}>
                Error loading profile data. Please try again later.
              </Alert>
            ) : (
              <form onSubmit={handleSubmit}>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <TextField
                      label="Email Address"
                      type="email"
                      fullWidth
                      value={formData.email}
                      onChange={handleChange('email')}
                      margin="normal"
                    />
                  </Grid>
                  
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Full Name"
                      fullWidth
                      value={formData.name}
                      onChange={handleChange('name')}
                      margin="normal"
                    />
                  </Grid>
                  
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Organization"
                      fullWidth
                      value={formData.organization}
                      onChange={handleChange('organization')}
                      margin="normal"
                    />
                  </Grid>
                  
                  <Grid item xs={12}>
                    <TextField
                      label="Bio"
                      multiline
                      rows={4}
                      fullWidth
                      value={formData.bio}
                      onChange={handleChange('bio')}
                      margin="normal"
                    />
                  </Grid>
                  
                  <Grid item xs={12} sx={{ mt: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <Button
                        type="submit"
                        variant="contained"
                        color="primary"
                        disabled={isUpdating}
                        startIcon={isUpdating ? <CircularProgress size={24} /> : <Save />}
                      >
                        {isUpdating ? 'Saving...' : 'Save Changes'}
                      </Button>
                    </Box>
                  </Grid>
                </Grid>
              </form>
            )}
          </Paper>
        </Grid>
        
        {/* Wallet Information Sidebar */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 3 }}>
              <Avatar sx={{ width: 80, height: 80, mb: 2, bgcolor: 'primary.main' }}>
                <AccountCircle fontSize="large" />
              </Avatar>
              
              <Typography variant="h6" align="center" gutterBottom>
                {user?.name || 'Ethereum User'}
              </Typography>
              
              <Typography variant="body2" align="center" color="text.secondary">
                {currentAccount ? formatWalletAddress(currentAccount, 8, 8) : 'Not connected'}
              </Typography>
              
              <Box sx={{ mt: 2 }}>
                <Button 
                  variant="outlined" 
                  color="primary"
                  onClick={signOut}
                >
                  Disconnect Wallet
                </Button>
              </Box>
            </Box>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="h6" gutterBottom>
              Account Summary
            </Typography>
            
            {isSummaryLoading ? (
              <CircularProgress size={24} />
            ) : (
              <Box>
                <Grid container spacing={1}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Total Assets:
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      {summary.unique_assets || 0}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Transactions:
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      {summary.total_transactions || 0}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Creates:
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      {summary.actions?.CREATE || 0}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Updates:
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      {summary.actions?.UPDATE || 0}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Deletes:
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      {summary.actions?.DELETE || 0}
                    </Typography>
                  </Grid>
                </Grid>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

export default ProfilePage;