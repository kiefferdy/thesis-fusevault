import { useState, useEffect } from 'react';
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
import UploadFormWithSigning from '../components/UploadFormWithSigning';
import { useAuth } from '../contexts/AuthContext';
import { useAssets } from '../hooks/useAssets';
import { toast } from 'react-hot-toast';

// Simple function to check if we're in edit mode and get asset ID
function getEditModeInfo() {
  const pathname = window.location.pathname;
  const isEditMode = pathname.includes('/edit');
  const assetId = isEditMode ? pathname.split('/')[2] : null;
  return { isEditMode, assetId };
}

function UploadPage() {
  const [tabValue, setTabValue] = useState(0);
  const [files, setFiles] = useState([]);
  const [fileType, setFileType] = useState('json'); // 'json' or 'csv'
  const [criticalFields, setCriticalFields] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStep, setUploadStep] = useState(0);

  // Edit mode state
  const [existingAsset, setExistingAsset] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { currentAccount } = useAuth();
  const { uploadJson, isUploading } = useAssets();
  const navigate = useNavigate();

  // Get edit mode info
  const { isEditMode, assetId } = getEditModeInfo();

  // Steps for the upload process
  const uploadSteps = ['Preparing files', 'Uploading to IPFS', 'Storing on blockchain', 'Finalizing'];

  // Fetch existing asset data when in edit mode
  useEffect(() => {
    if (!isEditMode || !assetId) return;

    const fetchAsset = async () => {
      setLoading(true);
      setError(null);

      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/retrieve/${assetId}`, {
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error('Failed to fetch asset');
        }

        const data = await response.json();
        setExistingAsset(data);
      } catch (err) {
        console.error('Error fetching asset:', err);
        setError('Failed to load asset data');
        toast.error('Error loading asset data');
      } finally {
        setLoading(false);
      }
    };

    fetchAsset();
  }, [isEditMode, assetId]);

  const handleTabChange = (event, newValue) => {
    // Don't allow tab changes in edit mode
    if (isEditMode) return;
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

  // Show loading state when fetching asset data for edit
  if (isEditMode && loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4, textAlign: 'center' }}>
        <CircularProgress />
        <Typography variant="body1" mt={2}>
          Loading asset data for editing...
        </Typography>
      </Container>
    );
  }

  // Show error state if asset couldn't be loaded
  if (isEditMode && error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">{error}</Alert>
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Button variant="contained" onClick={() => navigate('/dashboard')}>
            Back to Dashboard
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        {isEditMode ? 'Edit Asset' : 'Upload Assets'}
      </Typography>


      <Paper sx={{ mb: 4 }}>
        {/* Only show tabs when not in edit mode */}
        {!isEditMode && (
          <>
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
          </>
        )}

        {/* Single Asset Form (or Edit Mode) */}
        {(tabValue === 0 || isEditMode) && (
          <Box sx={{ p: 3 }}>
            {isEditMode ? (
              <Alert severity="info" sx={{ mb: 3 }}>
                You are editing an existing asset. Make your changes and click "Update Asset" to save.
              </Alert>
            ) : (
              <Alert severity="info" sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
                <Info sx={{ mr: 1 }} />
                <div>
                  <Typography variant="body2" fontWeight="bold">Creating an asset involves five phases:</Typography>
                  <Typography variant="body2">1. The metadata is parsed and validated.</Typography>
                  <Typography variant="body2">2. Critical metadata is stored on decentralized storage (IPFS).</Typography>
                  <Typography variant="body2">3. The asset is logged on the blockchain.</Typography>
                  <Typography variant="body2">4. The asset is stored on the database.</Typography>
                  <Typography variant="body2">5. The transaction is recorded.</Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>This process can take 1-3 minutes. Please wait for the confirmation.</Typography>
                </div>
              </Alert>
            )}
            <Box data-navigate onClick={() => navigate('/dashboard')} style={{ display: 'none' }} />
            <UploadFormWithSigning 
              existingAsset={isEditMode ? existingAsset : null}
              onUploadSuccess={(result) => {
                // Only show generic success message if it wasn't a non-critical metadata update
                // (non-critical updates already show their own specific message)
                if (!isEditMode || !result || result.status === 'pending_signature' || result.blockchain_tx_hash) {
                  toast.success(isEditMode ? 'Asset updated successfully!' : 'Asset created successfully!');
                }
                setTimeout(() => {
                  navigate('/dashboard');
                }, 1000);
              }}
            />
          </Box>
        )}

        {/* Batch Upload - only show when not in edit mode */}
        {!isEditMode && tabValue === 1 && (
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