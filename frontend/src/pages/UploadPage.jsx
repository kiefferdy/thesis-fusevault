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
import BatchUploadZone from '../components/BatchUploadZone';
import AssetPreviewGrid from '../components/AssetPreviewGrid';
import BatchProgressTracker from '../components/BatchProgressTracker';
import TemplateSelector from '../components/TemplateSelector';
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
  
  // Batch upload state
  const [batchFiles, setBatchFiles] = useState([]);
  const [batchAssets, setBatchAssets] = useState([]);
  const [batchProgress, setBatchProgress] = useState({
    uploadProgress: 0,
    currentStage: 0,
    assetProgress: {},
    errors: {},
    warnings: {},
    estimatedTimeRemaining: null,
    blockchainTxHash: null,
    networkStatus: null
  });


  // Edit mode state
  const [existingAsset, setExistingAsset] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { currentAccount } = useAuth();
  const { uploadBatch, isBatchUploading } = useAssets();
  const navigate = useNavigate();

  // Get edit mode info
  const { isEditMode, assetId } = getEditModeInfo();

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

  // Enhanced batch upload handlers
  const handleBatchFilesChange = (newFiles) => {
    setBatchFiles(newFiles);
  };

  const handleBatchAssetsChange = (newAssets) => {
    setBatchAssets(newAssets);
  };

  const handleAssetEdit = (assetIndex, updatedAsset) => {
    const newAssets = [...batchAssets];
    newAssets[assetIndex] = updatedAsset;
    setBatchAssets(newAssets);
  };

  const handleAssetDelete = (assetIndex) => {
    const newAssets = batchAssets.filter((_, index) => index !== assetIndex);
    setBatchAssets(newAssets);
    toast.success('Asset removed from batch');
  };

  const handleCreateAssetsFromTemplate = (newAssets) => {
    setBatchAssets(prev => [...prev, ...newAssets]);
  };

  const handleBatchUpload = async () => {
    if (batchAssets.length === 0) {
      toast.error('Please add assets to upload');
      return;
    }

    if (batchAssets.length > 50) {
      toast.error(`Too many assets (${batchAssets.length}). Maximum 50 assets per batch.`);
      return;
    }

    // Reset progress
    setBatchProgress({
      uploadProgress: 0,
      currentStage: 0,
      assetProgress: {},
      errors: {},
      warnings: {},
      estimatedTimeRemaining: null,
      blockchainTxHash: null,
      networkStatus: null
    });

    try {
      // Use enhanced batch upload with detailed progress tracking
      uploadBatch({
        assets: batchAssets
      }, {
        onProgress: (message, progress, additionalData = {}) => {
          setBatchProgress(prev => ({
            ...prev,
            uploadProgress: progress,
            currentStage: additionalData.stage || prev.currentStage,
            assetProgress: additionalData.assetProgress || prev.assetProgress,
            errors: additionalData.errors || prev.errors,
            warnings: additionalData.warnings || prev.warnings,
            estimatedTimeRemaining: additionalData.estimatedTimeRemaining || prev.estimatedTimeRemaining,
            blockchainTxHash: additionalData.blockchainTxHash || prev.blockchainTxHash,
            networkStatus: additionalData.networkStatus || prev.networkStatus
          }));
        },
        onSuccess: (result) => {
          setBatchProgress(prev => ({
            ...prev,
            uploadProgress: 100,
            currentStage: 4,
            blockchainTxHash: result.blockchainTxHash || prev.blockchainTxHash
          }));
          
          // Navigate after showing completion
          setTimeout(() => {
            navigate('/dashboard');
          }, 2000);
        },
        onError: (error) => {
          setBatchProgress(prev => ({
            ...prev,
            errors: { general: error.message, ...prev.errors }
          }));
        }
      });
    } catch (error) {
      setBatchProgress(prev => ({
        ...prev,
        errors: { general: error.message }
      }));
      toast.error(`Upload failed: ${error.message}`);
    }
  };

  const handleRetryUpload = () => {
    handleBatchUpload();
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
                if (!isEditMode) {
                  // Asset creation
                  toast.success('Asset created successfully!');
                } else {
                  // Asset editing - use the explicit flag we added
                  if (result && result.criticalMetadataUpdated === false) {
                    // Only non-critical metadata changed
                    toast.success('Asset updated successfully! (Only non-critical metadata changed)');
                  } else {
                    // Critical metadata changed or regular asset creation
                    toast.success('Asset updated successfully!');
                  }
                }
                setTimeout(() => {
                  navigate('/dashboard');
                }, 1000);
              }}
            />
          </Box>
        )}

        {/* Enhanced Batch Upload - only show when not in edit mode */}
        {!isEditMode && tabValue === 1 && (
          <Box sx={{ p: 3 }}>
            <Alert severity="info" sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
              <Info sx={{ mr: 1 }} />
              <div>
                <Typography variant="body2" fontWeight="bold">
                  Enhanced batch upload allows you to create multiple assets using templates, file uploads, or JSON input.
                </Typography>
                <Typography variant="body2">
                  Use templates for quick asset creation, upload JSON files, or paste JSON content directly.
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  Maximum 50 assets per batch. Preview and edit assets before uploading.
                </Typography>
              </div>
            </Alert>

            <Grid container spacing={3}>
              {/* Template Selector */}
              <Grid item xs={12}>
                <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
                  <TemplateSelector
                    onCreateAssets={handleCreateAssetsFromTemplate}
                    currentAccount={currentAccount}
                    maxAssets={50}
                    currentAssetCount={batchAssets.length}
                  />
                </Paper>
              </Grid>

              {/* File Upload Zone */}
              <Grid item xs={12}>
                <Paper variant="outlined" sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Upload Files or Paste JSON
                  </Typography>
                  <BatchUploadZone
                    onFilesChange={handleBatchFilesChange}
                    onAssetsChange={handleBatchAssetsChange}
                    acceptedFormats={['.json']}
                    maxFiles={50}
                    currentFiles={batchFiles}
                    currentAssets={batchAssets}
                  />
                </Paper>
              </Grid>

              {/* Asset Preview and Management */}
              {batchAssets.length > 0 && (
                <Grid item xs={12}>
                  <Paper variant="outlined" sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      Asset Management
                    </Typography>
                    <AssetPreviewGrid
                      assets={batchAssets}
                      onAssetsChange={handleBatchAssetsChange}
                      onAssetEdit={handleAssetEdit}
                      onAssetDelete={handleAssetDelete}
                      showBulkActions={true}
                      maxAssets={50}
                    />
                  </Paper>
                </Grid>
              )}

              {/* Upload Controls */}
              {batchAssets.length > 0 && (
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                    <Button
                      variant="outlined"
                      onClick={() => {
                        setBatchAssets([]);
                        setBatchFiles([]);
                        setBatchProgress({
                          uploadProgress: 0,
                          currentStage: 0,
                          assetProgress: {},
                          errors: {},
                          warnings: {},
                          estimatedTimeRemaining: null,
                          blockchainTxHash: null,
                          networkStatus: null
                        });
                      }}
                      disabled={isBatchUploading}
                    >
                      Clear All
                    </Button>
                    <Button
                      variant="contained"
                      size="large"
                      onClick={handleBatchUpload}
                      disabled={isBatchUploading || batchAssets.length === 0 || batchAssets.length > 50}
                      startIcon={isBatchUploading ? <CircularProgress size={20} /> : <CloudUpload />}
                    >
                      {isBatchUploading ? 'Uploading...' : `Upload ${batchAssets.length} Asset${batchAssets.length > 1 ? 's' : ''}`}
                    </Button>
                  </Box>
                </Grid>
              )}
            </Grid>

            {/* Enhanced Progress Tracking */}
            <BatchProgressTracker
              isUploading={isBatchUploading}
              uploadProgress={batchProgress.uploadProgress}
              currentStage={batchProgress.currentStage}
              assets={batchAssets}
              assetProgress={batchProgress.assetProgress}
              errors={batchProgress.errors}
              warnings={batchProgress.warnings}
              onRetry={handleRetryUpload}
              estimatedTimeRemaining={batchProgress.estimatedTimeRemaining}
              blockchainTxHash={batchProgress.blockchainTxHash}
              networkStatus={batchProgress.networkStatus}
            />
          </Box>
        )}
      </Paper>
    </Container>
  );
}

export default UploadPage;