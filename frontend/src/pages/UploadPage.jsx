import { useState } from 'react';
import { 
  Container, 
  Typography, 
  Box, 
  Paper, 
  Tabs, 
  Tab,
  Divider,
  Grid,
  Button,
  CircularProgress,
  Alert,
  TextField,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  Card,
  CardContent,
  Backdrop
} from '@mui/material';
import { CloudUpload, Description, Info } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import AssetForm from '../components/AssetForm';
import { useAuth } from '../contexts/AuthContext';
import { useAssets } from '../hooks/useAssets';
import { toast } from 'react-hot-toast';

function UploadPage() {
  const [tabValue, setTabValue] = useState(0);
  const [files, setFiles] = useState([]);
  const [fileType, setFileType] = useState('json'); // 'json' or 'csv'
  const [criticalFields, setCriticalFields] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStep, setUploadStep] = useState(0);
  const { currentAccount } = useAuth();
  const { uploadJson, isUploading } = useAssets();
  const navigate = useNavigate();
  
  // Steps for the upload process
  const uploadSteps = ['Preparing files', 'Uploading to IPFS', 'Storing on blockchain', 'Finalizing'];

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files);
    setFiles(selectedFiles);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      toast.error('Please select files to upload');
      return;
    }
    
    try {
      setUploadProgress(0);
      setUploadStep(0);
      
      // Simulate progress for each step
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = prev + 1;
          
          // Change steps at certain thresholds
          if (newProgress === 25) setUploadStep(1);
          if (newProgress === 50) setUploadStep(2);
          if (newProgress === 75) setUploadStep(3);
          
          return newProgress < 99 ? newProgress : 99;
        });
      }, 150);
      
      if (fileType === 'json') {
        await uploadJson({ files }, {
          onSuccess: () => {
            clearInterval(progressInterval);
            setUploadProgress(100);
            
            // Wait a moment before navigating to give user visual feedback
            setTimeout(() => {
              navigate('/dashboard');
            }, 1000);
          }
        });
      } else {
        // CSV upload would need to be implemented on backend
        clearInterval(progressInterval);
        toast.error('CSV upload not yet implemented');
      }
    } catch (error) {
      setUploadProgress(0);
      toast.error(`Upload failed: ${error.message}`);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Upload Assets
      </Typography>
      
      {/* Upload Progress Backdrop */}
      <Backdrop open={isUploading} sx={{ zIndex: 9999, flexDirection: 'column', color: '#fff' }}>
        <Card sx={{ maxWidth: 400, mb: 3, p: 3, bgcolor: 'background.paper' }}>
          <CardContent>
            <Typography variant="h6" color="primary" gutterBottom textAlign="center">
              Uploading Asset{files.length > 1 ? 's' : ''}
            </Typography>
            
            <Stepper activeStep={uploadStep} alternativeLabel sx={{ mb: 3 }}>
              {uploadSteps.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
            
            <LinearProgress 
              variant="determinate" 
              value={uploadProgress} 
              sx={{ height: 10, borderRadius: 5, mb: 2 }} 
            />
            
            <Typography variant="body2" color="text.secondary" textAlign="center">
              {uploadSteps[uploadStep]}... ({uploadProgress}%)
            </Typography>
            <Typography variant="caption" color="text.secondary" textAlign="center" display="block" mt={1}>
              Please don't close this window. This process may take a few minutes.
            </Typography>
          </CardContent>
        </Card>
      </Backdrop>
      
      <Paper sx={{ mb: 4 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab label="Create Single Asset" />
          <Tab label="Batch Upload" />
        </Tabs>
        
        <Divider />
        
        {/* Single Asset Form */}
        {tabValue === 0 && (
          <Box sx={{ p: 3 }}>
            <Alert severity="info" sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
              <Info sx={{ mr: 1 }} />
              <div>
                <Typography variant="body2" fontWeight="bold">Creating an asset involves two phases:</Typography>
                <Typography variant="body2">1. Data is uploaded to decentralized storage (IPFS)</Typography>
                <Typography variant="body2">2. Unique asset identifiers are stored on the blockchain</Typography>
                <Typography variant="body2" sx={{ mt: 0.5 }}>This process can take 1-3 minutes. Please wait for the confirmation.</Typography>
              </div>
            </Alert>
            <Box data-navigate onClick={() => navigate('/dashboard')} style={{ display: 'none' }} />
            <AssetForm />
          </Box>
        )}
        
        {/* Batch Upload */}
        {tabValue === 1 && (
          <Box sx={{ p: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Alert severity="info" sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
                  <Info sx={{ mr: 1 }} />
                  <div>
                    <Typography variant="body2" fontWeight="bold">
                      Batch upload allows you to create multiple assets at once using JSON or CSV files.
                    </Typography>
                    <Typography variant="body2">
                      Each file should contain the required fields for creating assets.
                    </Typography>
                    <Typography variant="body2" sx={{ mt: 0.5 }}>
                      The upload process can take several minutes depending on file size.
                    </Typography>
                  </div>
                </Alert>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Paper variant="outlined" sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Upload Format
                  </Typography>
                  
                  <Box sx={{ mb: 2 }}>
                    <Tabs
                      value={fileType}
                      onChange={(e, value) => setFileType(value)}
                      indicatorColor="primary"
                      textColor="primary"
                    >
                      <Tab value="json" label="JSON" />
                      <Tab value="csv" label="CSV" disabled />
                    </Tabs>
                  </Box>
                  
                  {fileType === 'json' && (
                    <Box sx={{ bgcolor: 'background.paper', p: 2, borderRadius: 1 }}>
                      <Typography variant="body2" color="text.primary" fontWeight="medium">
                        Each JSON file should include:
                      </Typography>
                      <Box component="pre" sx={{ bgcolor: 'action.hover', p: 2, borderRadius: 1, overflowX: 'auto', fontSize: '0.85rem', mt: 1 }}>
                        {`{
  "asset_id": "unique-id", 
  "wallet_address": "${currentAccount || '0x...'}",
  "critical_metadata": {
    "name": "Asset name",
    "description": "Description",
    "tags": ["tag1", "tag2"]
    // Other user-defined fields as needed
  },
  "non_critical_metadata": {
    // Any additional properties
    "custom_field1": "value1",
    "custom_field2": "value2"
  }
}`}
                      </Box>
                    </Box>
                  )}
                  
                  {fileType === 'csv' && (
                    <>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        Your CSV must include 'asset_id' and 'wallet_address' columns.
                        Specify which other columns should be treated as critical metadata:
                      </Typography>
                      
                      <TextField
                        label="Critical Fields (comma-separated)"
                        value={criticalFields}
                        onChange={(e) => setCriticalFields(e.target.value)}
                        helperText="e.g., name,description,category"
                        fullWidth
                        margin="normal"
                      />
                    </>
                  )}
                </Paper>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Paper
                  variant="outlined"
                  component="label"
                  sx={{
                    p: 3,
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    borderStyle: 'dashed',
                    borderRadius: 2,
                    borderWidth: 2,
                    borderColor: theme => theme.palette.primary.light,
                    bgcolor: theme => theme.palette.primary.lighter || 'rgba(0, 0, 255, 0.03)',
                    '&:hover': {
                      bgcolor: theme => theme.palette.primary.lighter || 'rgba(0, 0, 255, 0.05)',
                      borderColor: 'primary.main'
                    }
                  }}
                >
                  <input
                    type="file"
                    multiple
                    onChange={handleFileChange}
                    accept={fileType === 'json' ? '.json' : '.csv'}
                    style={{ display: 'none' }}
                  />
                  
                  <CloudUpload fontSize="large" color="primary" sx={{ mb: 2, fontSize: 60 }} />
                  
                  <Typography variant="h6" color="primary.main" gutterBottom>
                    Click to select files
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary">
                    or drag and drop here
                  </Typography>
                  
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                    Accepted format: {fileType === 'json' ? '*.json' : '*.csv'}
                  </Typography>
                </Paper>
              </Grid>
              
              {files.length > 0 && (
                <Grid item xs={12}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Selected Files ({files.length})
                    </Typography>
                    
                    {files.map((file, index) => (
                      <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Description fontSize="small" sx={{ mr: 1 }} />
                        <Typography variant="body2">
                          {file.name} ({(file.size / 1024).toFixed(2)} KB)
                        </Typography>
                      </Box>
                    ))}
                  </Paper>
                </Grid>
              )}
              
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleUpload}
                    disabled={isUploading || files.length === 0}
                    startIcon={isUploading ? <CircularProgress size={20} /> : <CloudUpload />}
                    size="large"
                  >
                    {isUploading ? 'Processing...' : 'Upload Files'}
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </Box>
        )}
      </Paper>
    </Container>
  );
}

export default UploadPage;