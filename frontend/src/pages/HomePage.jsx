import { 
  Box, 
  Container, 
  Typography, 
  Button, 
  Paper, 
  Grid,
  Card,
  CardContent,
  CardMedia
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Security, Storage, VerifiedUser } from '@mui/icons-material';

function HomePage() {
  const { isAuthenticated, signIn } = useAuth();
  const navigate = useNavigate();

  return (
    <Box>
      {/* Hero Section */}
      <Paper
        sx={{
          py: 6,
          px: 4,
          mb: 4,
          bgcolor: 'primary.main',
          color: 'white',
          textAlign: 'center'
        }}
      >
        <Container maxWidth="md">
          <Typography variant="h3" component="h1" gutterBottom fontWeight="bold">
            FuseVault: Secure Digital Asset Management
          </Typography>
          <Typography variant="h6" paragraph>
            Store, verify, and manage your digital assets with blockchain-backed security and IPFS decentralized storage
          </Typography>
          
          {isAuthenticated ? (
            <Button 
              variant="contained" 
              color="secondary" 
              size="large"
              onClick={() => navigate('/dashboard')}
            >
              Go to Dashboard
            </Button>
          ) : (
            <Button 
              variant="contained" 
              color="secondary" 
              size="large"
              onClick={signIn}
            >
              Connect with MetaMask
            </Button>
          )}
        </Container>
      </Paper>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ mb: 6 }}>
        <Typography variant="h4" component="h2" textAlign="center" gutterBottom>
          Key Features
        </Typography>
        
        <Grid container spacing={4} mt={2}>
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%' }}>
              <CardContent sx={{ textAlign: 'center', py: 4 }}>
                <Security fontSize="large" color="primary" sx={{ fontSize: 60, mb: 2 }} />
                <Typography variant="h5" component="h3" gutterBottom>
                  Blockchain Security
                </Typography>
                <Typography variant="body1">
                  Every asset is secured with Ethereum blockchain verification, ensuring immutable proof of ownership and authenticity.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%' }}>
              <CardContent sx={{ textAlign: 'center', py: 4 }}>
                <Storage fontSize="large" color="primary" sx={{ fontSize: 60, mb: 2 }} />
                <Typography variant="h5" component="h3" gutterBottom>
                  Decentralized Storage
                </Typography>
                <Typography variant="body1">
                  Assets are stored on IPFS (InterPlanetary File System), providing decentralized and content-addressed storage with high availability.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%' }}>
              <CardContent sx={{ textAlign: 'center', py: 4 }}>
                <VerifiedUser fontSize="large" color="primary" sx={{ fontSize: 60, mb: 2 }} />
                <Typography variant="h5" component="h3" gutterBottom>
                  Asset Verification
                </Typography>
                <Typography variant="body1">
                  Automatic verification of asset integrity ensures your data remains tamper-proof with built-in recovery mechanisms.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>

      {/* How It Works */}
      <Box sx={{ bgcolor: 'grey.100', py: 6 }}>
        <Container maxWidth="lg">
          <Typography variant="h4" component="h2" textAlign="center" gutterBottom>
            How It Works
          </Typography>
          
          <Grid container spacing={3} mt={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <Box sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  1. Connect your Ethereum wallet
                </Typography>
                <Typography paragraph>
                  Sign in securely using MetaMask without sharing passwords or sensitive information.
                </Typography>
                
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  2. Upload your assets
                </Typography>
                <Typography paragraph>
                  Store metadata for any digital asset with customizable fields for both critical and non-critical information.
                </Typography>
                
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  3. Verify & manage your assets
                </Typography>
                <Typography paragraph>
                  Track version history, verify integrity, and manage access - all backed by blockchain technology.
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Box sx={{ textAlign: 'center' }}>
                {/* You can add an image or diagram here */}
                <Paper 
                  sx={{ 
                    height: 300, 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    bgcolor: 'background.paper' 
                  }}
                >
                  <Typography variant="h5" color="text.secondary">
                    [Process Diagram]
                  </Typography>
                </Paper>
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Call to Action */}
      <Box sx={{ textAlign: 'center', py: 6 }}>
        <Container maxWidth="md">
          <Typography variant="h4" gutterBottom>
            Ready to Secure Your Digital Assets?
          </Typography>
          <Typography variant="body1" paragraph>
            Start using FuseVault today and experience the future of secure asset management.
          </Typography>
          
          {isAuthenticated ? (
            <Button 
              variant="contained" 
              color="primary" 
              size="large"
              onClick={() => navigate('/dashboard')}
            >
              Go to Dashboard
            </Button>
          ) : (
            <Button 
              variant="contained" 
              color="primary" 
              size="large"
              onClick={signIn}
            >
              Get Started
            </Button>
          )}
        </Container>
      </Box>
    </Box>
  );
}

export default HomePage;