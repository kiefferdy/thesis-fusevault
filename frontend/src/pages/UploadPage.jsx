import { useState, useEffect, useRef } from 'react';
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
  Backdrop,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip
} from '@mui/material';
import { CloudUpload, Description, Info, Palette, ExpandMore, CheckCircle, Storage, Cloud, Add } from '@mui/icons-material';
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
    currentStage: -1,
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
  
  // Template creation ref
  const createTemplateRef = useRef(null);
  
  // Progress tracker ref for auto-scroll
  const progressTrackerRef = useRef(null);

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
      // Auto-scroll will happen on first progress update
      let hasScrolled = false;
      
      // Use enhanced batch upload with detailed progress tracking
      uploadBatch({
        assets: batchAssets,
        onProgress: (message, progress, additionalData = {}) => {
          setBatchProgress(prev => ({
            ...prev,
            uploadProgress: progress,
            currentStage: additionalData.stage || prev.currentStage,
            assetProgress: (additionalData.assetProgress && Object.keys(additionalData.assetProgress).length > 0) 
              ? additionalData.assetProgress 
              : prev.assetProgress,
            errors: additionalData.errors || prev.errors,
            warnings: additionalData.warnings || prev.warnings,
            estimatedTimeRemaining: additionalData.estimatedTimeRemaining || prev.estimatedTimeRemaining,
            blockchainTxHash: additionalData.blockchainTxHash || prev.blockchainTxHash,
            networkStatus: additionalData.networkStatus || prev.networkStatus
          }));
          
          // Auto-scroll to progress tracker on first progress update
          if (!hasScrolled && progressTrackerRef.current) {
            hasScrolled = true;
            // Small delay to ensure component is rendered
            setTimeout(() => {
              progressTrackerRef.current?.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
              });
            }, 100);
          }
        }
      }, {
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
            ) : tabValue === 0 ? (
              <Alert severity="info" sx={{ mb: 3 }}>
                <Box>
                  <Typography variant="body2" fontWeight="bold" gutterBottom>
                    Creating an asset involves five phases:
                  </Typography>
                  <Box component="ol" sx={{ pl: 2, m: 0 }}>
                    <li>
                      <Typography variant="body2">The metadata is parsed and validated.</Typography>
                    </li>
                    <li>
                      <Typography variant="body2">Critical metadata is stored on decentralized storage (IPFS).</Typography>
                    </li>
                    <li>
                      <Typography variant="body2">The asset is logged on the blockchain.</Typography>
                    </li>
                    <li>
                      <Typography variant="body2">The asset is stored on the database.</Typography>
                    </li>
                    <li>
                      <Typography variant="body2">The transaction is recorded.</Typography>
                    </li>
                  </Box>
                  <Typography variant="body2" sx={{ mt: 1.5, fontStyle: 'italic' }}>
                    This process can take 1-3 minutes. Please wait for the confirmation.
                  </Typography>
                </Box>
              </Alert>
            ) : null}
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

        {/* Enhanced Batch Upload - only show when not in edit mode and on batch tab */}
        {!isEditMode && tabValue === 1 && (
          <Box sx={{ p: 3 }}>
            <Alert severity="info" sx={{ mb: 3 }}>
              <div>
                <Typography variant="body2" fontWeight="bold">
                  Batch upload supports templates, JSON files, CSV imports, and direct JSON input.
                </Typography>
                <Typography variant="body2">
                  Use templates for quick asset creation, upload JSON files, import CSV files, or paste JSON content directly.
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  Maximum 50 assets per batch. Preview and edit assets before uploading.
                </Typography>
              </div>
            </Alert>

            <Grid container spacing={2}>
              {/* Data Structure Requirements - Expandable */}
              <Grid item xs={12}>
                <Accordion sx={{ mb: 0, border: '1px solid', borderColor: 'grey.300', borderRadius: 2, boxShadow: 1 }}>
                  <AccordionSummary 
                    expandIcon={<ExpandMore />}
                    sx={{ 
                      bgcolor: 'blue.50', 
                      color: 'primary.main',
                      '&:hover': { bgcolor: 'blue.100' },
                      borderRadius: '8px 8px 0 0'
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Info />
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Data Structure & Formatting Requirements
                      </Typography>
                      <Tooltip title="Click to expand/collapse this section">
                        <Typography variant="caption" sx={{ opacity: 0.8 }}>
                          (Important - Read Before Uploading)
                        </Typography>
                      </Tooltip>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails sx={{ p: 4, bgcolor: 'background.paper' }}>
                    
                    {/* Overview */}
                    <Alert severity="info" sx={{ mb: 3 }}>
                      <Typography variant="body2" fontWeight="bold" gutterBottom>
                        Overview: Every asset needs an <code>assetId</code>. <code>criticalMetadata</code>, and <code>nonCriticalMetadata</code> objects must also be present but can be left empty.
                      </Typography>
                      <Typography variant="body2">
                        Critical metadata is stored on blockchain/IPFS for extra security. Updating these fields take longer and require signing.
                      </Typography>
                    </Alert>

                    {/* Required vs Recommended Fields */}
                    <Box sx={{ mb: 4 }}>
                      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'error.main' }}>
                        <CheckCircle />
                        Required Fields
                      </Typography>
                      <Card variant="outlined" sx={{ p: 2, bgcolor: 'red.50', border: '1px solid', borderColor: 'red.200' }}>
                        <Box component="ul" sx={{ m: 0, pl: 2 }}>
                          <li><Typography variant="body2"><code>assetId</code> - Unique identifier for your asset (must be unique across all your assets)</Typography></li>
                          <li><Typography variant="body2"><code>criticalMetadata</code> - Object for blockchain-secured data (can be empty <code>{'{'}{'}'}</code>)</Typography></li>
                          <li><Typography variant="body2"><code>nonCriticalMetadata</code> - Object for readily-editable data (can be empty <code>{'{'}{'}'}</code>)</Typography></li>
                        </Box>
                      </Card>
                      
                      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'warning.main', mt: 3 }}>
                        <Info />
                        Highly Recommended Fields
                      </Typography>
                      <Card variant="outlined" sx={{ p: 2, bgcolor: 'orange.50', border: '1px solid', borderColor: 'orange.200' }}>
                        <Box component="ul" sx={{ m: 0, pl: 2 }}>
                          <li><Typography variant="body2"><code>criticalMetadata.name</code> - Asset name displayed in dashboard and asset cards</Typography></li>
                          <li><Typography variant="body2"><code>criticalMetadata.description</code> - Helps users understand what the asset represents</Typography></li>
                          <li><Typography variant="body2"><code>criticalMetadata.tags</code> - Array of tags for filtering and organizing assets</Typography></li>
                        </Box>
                      </Card>
                      
                      <Alert severity="warning" sx={{ mt: 2 }}>
                        <Typography variant="body2">
                          <strong>Note:</strong> While technically optional, <code>name</code>, <code>description</code>, and <code>tags</code> are strongly recommended as they greatly improve asset discoverability and management in the dashboard.
                        </Typography>
                      </Alert>
                    </Box>

                    {/* Metadata Types */}
                    <Box sx={{ mb: 4 }}>
                      <Typography variant="h6" gutterBottom>
                        🔐 Understanding Metadata Types
                      </Typography>
                      <Grid container spacing={3}>
                        <Grid item xs={12} md={6}>
                          <Card variant="outlined" sx={{ p: 3, height: '100%', bgcolor: 'orange.50', border: '1px solid', borderColor: 'orange.200' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                              <Cloud color="primary" />
                              <Typography variant="h6" color="primary">Critical Metadata</Typography>
                            </Box>
                            <Typography variant="body2" paragraph>
                              <strong>Stored on:</strong> Blockchain + IPFS (decentralized)
                            </Typography>
                            <Typography variant="body2" paragraph>
                              <strong>Characteristics:</strong> Permanent, immutable, publicly verifiable
                            </Typography>
                            <Typography variant="body2" paragraph>
                              <strong>Use for:</strong> Asset name, description, tags, crucial ownership details, information requiring tamper protection
                            </Typography>
                            <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                              💡 Once uploaded, this data can be changed but will require re-upload and MetaMask signing
                            </Typography>
                          </Card>
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <Card variant="outlined" sx={{ p: 3, height: '100%', bgcolor: 'green.50', border: '1px solid', borderColor: 'green.200' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                              <Storage color="primary" />
                              <Typography variant="h6" color="primary">Non-Critical Metadata</Typography>
                            </Box>
                            <Typography variant="body2" paragraph>
                              <strong>Stored on:</strong> Database (centralized)
                            </Typography>
                            <Typography variant="body2" paragraph>
                              <strong>Characteristics:</strong> Instantly editable, private, faster access
                            </Typography>
                            <Typography variant="body2" paragraph>
                              <strong>Use for:</strong> Internal notes, file sizes, processing status, temporary flags, comments
                            </Typography>
                            <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                              💡 This data can be instantly edited anytime after upload
                            </Typography>
                          </Card>
                        </Grid>
                      </Grid>
                    </Box>

                    {/* Format Examples */}
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="h6" gutterBottom>
                        📝 Format Examples
                      </Typography>
                      <Grid container spacing={3}>
                        <Grid item xs={12} md={6}>
                          <Typography variant="subtitle1" gutterBottom color="primary" sx={{ fontWeight: 600 }}>
                            JSON Format (Array of Objects):
                          </Typography>
                          <Box sx={{ 
                            bgcolor: 'grey.100', 
                            color: 'grey.800', 
                            p: 2, 
                            borderRadius: 2, 
                            border: '1px solid',
                            borderColor: 'grey.300',
                            fontFamily: 'monospace', 
                            fontSize: '0.8rem',
                            overflow: 'auto'
                          }}>
                            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
{`[
  {
    "assetId": "document-001",
    "walletAddress": "0x1234...abcd",
    "criticalMetadata": {
      "name": "Project Proposal",
      "description": "Q4 marketing proposal", 
      "tags": ["proposal", "marketing", "q4"],
      "author": "John Doe",
      "created_date": "2024-01-15",
      "document_type": "proposal"
    },
    "nonCriticalMetadata": {
      "file_size": "2.5MB",
      "department": "Marketing",
      "status": "draft",
      "internal_notes": "Needs review"
    }
  }
]`}
                            </pre>
                          </Box>
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <Typography variant="subtitle1" gutterBottom color="primary" sx={{ fontWeight: 600 }}>
                            CSV Format Example:
                          </Typography>
                          <Box sx={{ 
                            bgcolor: 'grey.100', 
                            color: 'grey.800', 
                            p: 2, 
                            borderRadius: 2, 
                            border: '1px solid',
                            borderColor: 'grey.300',
                            fontFamily: 'monospace', 
                            fontSize: '0.8rem',
                            overflow: 'auto'
                          }}>
                            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
{`assetId,name,description,author,tags,file_size
document-001,Project Proposal,Q4 marketing proposal,John Doe,"proposal,marketing",2.5MB
image-002,Company Logo,Updated brand logo,Jane Smith,"logo,brand",500KB`}
                            </pre>
                          </Box>
                          <Alert severity="warning" sx={{ mt: 2 }}>
                            <Typography variant="body2">
                              <strong>CSV Note:</strong> Use the column mapping tool after upload to assign CSV columns to critical/non-critical metadata fields.
                            </Typography>
                          </Alert>
                        </Grid>
                      </Grid>
                    </Box>

                    {/* Common Mistakes */}
                    <Alert severity="error" sx={{ mb: 2 }}>
                      <Typography variant="body2" fontWeight="bold" gutterBottom>
                        ⚠️ Common Mistakes to Avoid:
                      </Typography>
                      <Box component="ul" sx={{ m: 0, pl: 2 }}>
                        <li><Typography variant="body2">Missing <code>assetId</code> field (the only truly required field)</Typography></li>
                        <li><Typography variant="body2">Not including <code>name</code>, <code>description</code>, or <code>tags</code> (makes assets hard to find in dashboard)</Typography></li>
                        <li><Typography variant="body2">Using duplicate <code>assetId</code> values within the same batch</Typography></li>
                        <li><Typography variant="body2">Putting sensitive data in critical metadata (it's publicly visible on blockchain and IPFS)</Typography></li>
                        <li><Typography variant="body2">Forgetting to include empty <code>criticalMetadata: {'{'}{'}'}</code> or <code>nonCriticalMetadata: {'{'}{'}'}</code> objects if you have no custom fields</Typography></li>
                      </Box>
                    </Alert>

                    <Alert severity="success">
                      <Typography variant="body2" fontWeight="bold">
                        💡 Pro Tip: Start with templates below if you're unsure about the structure!
                      </Typography>
                    </Alert>

                  </AccordionDetails>
                </Accordion>
              </Grid>

              {/* Enhanced Progress Tracking */}
              <Grid item xs={12}>
                <Box ref={progressTrackerRef}>
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
              </Grid>

              {/* File Upload Zone */}
              <Grid item xs={12}>
                <Paper variant="outlined" sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Upload JSON, Import CSV, or Paste JSON
                  </Typography>
                  <BatchUploadZone
                    onFilesChange={handleBatchFilesChange}
                    onAssetsChange={handleBatchAssetsChange}
                    acceptedFormats={['.json']}
                    maxFiles={50}
                    currentFiles={batchFiles}
                    currentAssets={batchAssets}
                    currentAccount={currentAccount}
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

              {/* Template Selector - Moved to Bottom */}
              <Grid item xs={12}>
                <Paper variant="outlined" sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Box>
                      <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Palette />
                        Asset Templates
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Use pre-built templates to quickly create assets with consistent structure and sample data.
                      </Typography>
                    </Box>
                    <Button
                      variant="outlined"
                      startIcon={<Add />}
                      onClick={() => createTemplateRef.current?.()}
                    >
                      Create Template
                    </Button>
                  </Box>
                  <TemplateSelector
                    onCreateAssets={handleCreateAssetsFromTemplate}
                    currentAccount={currentAccount}
                    maxAssets={50}
                    currentAssetCount={batchAssets.length}
                    onCreateTemplateClick={(fn) => { createTemplateRef.current = fn; }}
                  />
                </Paper>
              </Grid>
            </Grid>

          </Box>
        )}
      </Paper>
    </Container>
  );
}

export default UploadPage;