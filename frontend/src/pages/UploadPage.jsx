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
  TextField
} from '@mui/material';
import { CloudUpload, Description } from '@mui/icons-material';
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
  const { currentAccount } = useAuth();
  const { uploadJson, isUploading } = useAssets();
  const navigate = useNavigate();

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
      if (fileType === 'json') {
        await uploadJson({ files }, {
          onSuccess: () => {
            navigate('/dashboard');
          }
        });
      } else {
        // CSV upload would need to be implemented on backend
        toast.error('CSV upload not yet implemented');
      }
    } catch (error) {
      toast.error(`Upload failed: ${error.message}`);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Upload Assets
      </Typography>
      
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
            <AssetForm />
          </Box>
        )}
        
        {/* Batch Upload */}
        {tabValue === 1 && (
          <Box sx={{ p: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Alert severity="info" sx={{ mb: 3 }}>
                  Batch upload allows you to create multiple assets at once using JSON or CSV files.
                  Each file should contain the required fields for creating assets.
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
                    <Typography variant="body2" color="text.secondary">
                      Each JSON file should contain an object with: <br />
                      <code>asset_id</code>: Unique identifier for the asset<br />
                      <code>wallet_address</code>: Owner's wallet address<br />
                      <code>critical_metadata</code>: Object with required fields<br />
                      <code>non_critical_metadata</code>: Optional additional data
                    </Typography>
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
                    borderStyle: 'dashed'
                  }}
                >
                  <input
                    type="file"
                    multiple
                    onChange={handleFileChange}
                    accept={fileType === 'json' ? '.json' : '.csv'}
                    style={{ display: 'none' }}
                  />
                  
                  <CloudUpload fontSize="large" color="primary" sx={{ mb: 2 }} />
                  
                  <Typography variant="body1" gutterBottom>
                    Click to select files or drag and drop
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary">
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
                  >
                    {isUploading ? 'Uploading...' : 'Upload Files'}
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