import { useState, useCallback, useRef, forwardRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Collapse,
  Tabs,
  Tab,
  Stepper,
  Step,
  StepLabel
} from '@mui/material';
import {
  CloudUpload,
  Description,
  ExpandMore,
  ExpandLess,
  Delete,
  Visibility,
  ContentPaste,
  FileUpload,
  Error,
  CheckCircle,
  Warning,
  TableChart
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import CSVParser from './CSVParser';
import CSVColumnMapper from './CSVColumnMapper';

const BatchUploadZone = ({
  onFilesChange,
  onAssetsChange,
  acceptedFormats = ['.json'],
  maxFiles = 50,
  currentFiles = [],
  currentAssets = [],
  currentAccount
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadMethod, setUploadMethod] = useState(0); // 0: Files, 1: JSON Paste, 2: CSV Upload
  const [jsonInput, setJsonInput] = useState('');
  const [previewDialog, setPreviewDialog] = useState({ open: false, content: null, fileName: '' });
  const [expandedFiles, setExpandedFiles] = useState(new Set());
  const [fileValidation, setFileValidation] = useState({});
  const fileInputRef = useRef(null);
  const csvParserRef = useRef(null);

  // CSV-specific state
  const [csvWorkflow, setCsvWorkflow] = useState({
    step: 0, // 0: upload, 1: parse, 2: map
    file: null,
    parsedData: null,
    mappedAssets: null
  });

  // Validate JSON content
  const validateJsonContent = useCallback((content, fileName = 'input') => {
    try {
      const parsed = JSON.parse(content);
      
      // Check if it's an array (multiple assets) or single asset
      const assets = Array.isArray(parsed) ? parsed : [parsed];
      const errors = [];
      const warnings = [];

      assets.forEach((asset, index) => {
        const assetNum = assets.length > 1 ? ` (Asset ${index + 1})` : '';
        
        // Required fields validation
        if (!asset.assetId && !asset.asset_id) {
          errors.push(`Missing asset ID${assetNum}`);
        }
        if (!asset.criticalMetadata && !asset.critical_metadata) {
          errors.push(`Missing critical metadata${assetNum}`);
        }

        // Check for common fields in critical metadata
        const criticalMeta = asset.criticalMetadata || asset.critical_metadata || {};
        if (!criticalMeta.name) {
          warnings.push(`Missing name in critical metadata${assetNum}`);
        }
        if (!criticalMeta.description) {
          warnings.push(`Missing description in critical metadata${assetNum}`);
        }
      });

      return {
        isValid: errors.length === 0,
        assets,
        assetCount: assets.length,
        errors,
        warnings,
        fileName
      };
    } catch (error) {
      return {
        isValid: false,
        assets: [],
        assetCount: 0,
        errors: [`Invalid JSON format: ${error.message}`],
        warnings: [],
        fileName
      };
    }
  }, []);

  // Process files
  const handleFiles = useCallback(async (files) => {
    if (files.length === 0) return;

    // Check file count limit
    if (currentFiles.length + files.length > maxFiles) {
      toast.error(`Cannot add ${files.length} files. Maximum ${maxFiles} files allowed.`);
      return;
    }

    // Validate file types
    const validFiles = files.filter(file => {
      const isValid = acceptedFormats.some(format => 
        file.name.toLowerCase().endsWith(format.toLowerCase())
      );
      if (!isValid) {
        toast.error(`${file.name}: Invalid file type. Accepted formats: ${acceptedFormats.join(', ')}`);
      }
      return isValid;
    });

    if (validFiles.length === 0) return;

    // Process files and validate content
    const newValidation = { ...fileValidation };
    const allAssets = [...currentAssets];
    const newFiles = [];

    for (const file of validFiles) {
      try {
        const content = await file.text();
        const validation = validateJsonContent(content, file.name);
        
        newValidation[file.name] = validation;
        
        if (validation.isValid) {
          // Add assets to collection
          allAssets.push(...validation.assets.map(asset => ({
            ...asset,
            // Normalize field names
            assetId: asset.assetId || asset.asset_id,
            criticalMetadata: asset.criticalMetadata || asset.critical_metadata,
            nonCriticalMetadata: asset.nonCriticalMetadata || asset.non_critical_metadata || {},
            _sourceFile: file.name
          })));
          newFiles.push(file);
        }
      } catch (error) {
        newValidation[file.name] = {
          isValid: false,
          assets: [],
          assetCount: 0,
          errors: [`Failed to read file: ${error.message}`],
          warnings: [],
          fileName: file.name
        };
      }
    }

    setFileValidation(newValidation);
    onFilesChange([...currentFiles, ...newFiles]);
    onAssetsChange(allAssets);

    // Show summary
    const validCount = Object.values(newValidation).filter(v => v.isValid).length;
    const totalAssets = Object.values(newValidation).reduce((sum, v) => sum + v.assetCount, 0);
    
    if (validCount > 0) {
      toast.success(`Added ${validCount} file(s) with ${totalAssets} asset(s)`);
    }
  }, [currentFiles, currentAssets, maxFiles, acceptedFormats, fileValidation, onFilesChange, onAssetsChange, validateJsonContent]);

  // Handle file drop
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  }, [handleFiles]);

  // Handle file input change
  const handleFileInput = useCallback((e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
  }, [handleFiles]);

  // Handle JSON paste
  const handleJsonPaste = useCallback(() => {
    if (!jsonInput.trim()) {
      toast.error('Please enter JSON content');
      return;
    }

    const validation = validateJsonContent(jsonInput, 'Pasted JSON');
    
    if (!validation.isValid) {
      toast.error(`Invalid JSON: ${validation.errors[0]}`);
      return;
    }

    // Add to assets
    const normalizedAssets = validation.assets.map(asset => ({
      ...asset,
      assetId: asset.assetId || asset.asset_id,
      criticalMetadata: asset.criticalMetadata || asset.critical_metadata,
      nonCriticalMetadata: asset.nonCriticalMetadata || asset.non_critical_metadata || {},
      _sourceFile: 'Pasted JSON'
    }));

    onAssetsChange([...currentAssets, ...normalizedAssets]);
    setJsonInput('');
    toast.success(`Added ${validation.assetCount} asset(s) from JSON`);
  }, [jsonInput, currentAssets, onAssetsChange, validateJsonContent]);

  // CSV workflow handlers
  const handleCSVFileSelect = useCallback((file) => {
    if (!file) {
      toast.error('No file selected');
      return;
    }

    if (!file.name.toLowerCase().endsWith('.csv')) {
      toast.error('Please select a CSV file');
      return;
    }

    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      toast.error('CSV file is too large. Maximum size is 5MB');
      return;
    }

    setCsvWorkflow({
      step: 1,
      file: file,
      parsedData: null,
      mappedAssets: null
    });
  }, []);

  const handleCSVParsed = useCallback((parsedData) => {
    setCsvWorkflow(prev => ({
      ...prev,
      step: 2,
      parsedData
    }));
    
    toast.success(`CSV parsed successfully: ${parsedData.rowCount} rows, ${parsedData.columnCount} columns`);
  }, []);

  const handleCSVMapped = useCallback((mappedAssets, validation) => {
    // Add mapped assets to the existing assets
    onAssetsChange([...currentAssets, ...mappedAssets]);
    toast.success(`Added ${mappedAssets.length} assets from CSV`);

    // Reset CSV workflow
    setCsvWorkflow({
      step: 0,
      file: null,
      parsedData: null,
      mappedAssets: null
    });

    // Switch back to files tab to show added assets
    setUploadMethod(0);
  }, [currentAssets, onAssetsChange]);

  const resetCSVWorkflow = useCallback(() => {
    setCsvWorkflow({
      step: 0,
      file: null,
      parsedData: null,
      mappedAssets: null
    });
  }, []);

  // Remove file
  const removeFile = useCallback((fileName) => {
    const newFiles = currentFiles.filter(f => f.name !== fileName);
    const newAssets = currentAssets.filter(a => a._sourceFile !== fileName);
    const newValidation = { ...fileValidation };
    delete newValidation[fileName];

    setFileValidation(newValidation);
    onFilesChange(newFiles);
    onAssetsChange(newAssets);
    toast.success(`Removed ${fileName}`);
  }, [currentFiles, currentAssets, fileValidation, onFilesChange, onAssetsChange]);

  // Toggle file expansion
  const toggleFileExpansion = useCallback((fileName) => {
    const newExpanded = new Set(expandedFiles);
    if (newExpanded.has(fileName)) {
      newExpanded.delete(fileName);
    } else {
      newExpanded.add(fileName);
    }
    setExpandedFiles(newExpanded);
  }, [expandedFiles]);

  // Preview file content
  const previewFile = useCallback(async (file) => {
    try {
      const content = await file.text();
      setPreviewDialog({ open: true, content, fileName: file.name });
    } catch (error) {
      toast.error(`Failed to read ${file.name}: ${error.message}`);
    }
  }, []);

  // Get validation status icon
  const getValidationIcon = (validation) => {
    if (!validation) return null;
    if (validation.errors.length > 0) return <Error color="error" />;
    if (validation.warnings.length > 0) return <Warning color="warning" />;
    return <CheckCircle color="success" />;
  };

  const totalAssets = currentAssets.length;
  const hasFiles = currentFiles.length > 0;

  return (
    <Box>
      {/* Upload Method Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={uploadMethod} onChange={(e, value) => setUploadMethod(value)}>
          <Tab icon={<FileUpload />} label="Upload JSON" />
          <Tab icon={<ContentPaste />} label="Paste JSON" />
          <Tab icon={<TableChart />} label="CSV Import" />
        </Tabs>
      </Box>

      {/* File Upload Tab */}
      {uploadMethod === 0 && (
        <Paper
          variant="outlined"
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          sx={{
            p: 4,
            textAlign: 'center',
            cursor: 'pointer',
            borderStyle: 'dashed',
            borderWidth: 2,
            borderColor: isDragOver ? 'primary.main' : 'divider',
            bgcolor: isDragOver ? 'action.hover' : 'background.paper',
            transition: 'all 0.2s ease',
            '&:hover': {
              borderColor: 'primary.main',
              bgcolor: 'action.hover'
            }
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={acceptedFormats.join(',')}
            onChange={handleFileInput}
            style={{ display: 'none' }}
          />

          <CloudUpload 
            sx={{ 
              fontSize: 64, 
              color: isDragOver ? 'primary.main' : 'text.secondary',
              mb: 2 
            }} 
          />
          
          <Typography variant="h6" gutterBottom>
            {isDragOver ? 'Drop files here' : 'Drag and drop JSON files here'}
          </Typography>
          
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            or click to select files
          </Typography>

          <Button variant="outlined" component="span">
            Select Files
          </Button>

          <Typography variant="caption" display="block" sx={{ mt: 2 }}>
            Accepted formats: .json • Max {maxFiles} files
          </Typography>
        </Paper>
      )}

      {/* JSON Paste Tab */}
      {uploadMethod === 1 && (
        <Box>
          <TextField
            fullWidth
            multiline
            rows={8}
            label="Paste JSON content here"
            placeholder={`Paste single asset or array of assets:\n\n[\n  {\n    "asset_id": "example-1",\n    "critical_metadata": {\n      "name": "Example Asset",\n      "description": "Description here"\n    }\n  }\n]`}
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
            sx={{ mb: 2 }}
          />
          <Button
            variant="contained"
            onClick={handleJsonPaste}
            disabled={!jsonInput.trim()}
            startIcon={<ContentPaste />}
          >
            Add from JSON
          </Button>
        </Box>
      )}

      {/* CSV Import Tab */}
      {uploadMethod === 2 && (
        <Box>
          {/* CSV Workflow Steps */}
          <Box sx={{ mb: 3 }}>
            <Stepper activeStep={csvWorkflow.step} alternativeLabel>
              <Step>
                <StepLabel>Upload CSV</StepLabel>
              </Step>
              <Step>
                <StepLabel>Parse Data</StepLabel>
              </Step>
              <Step>
                <StepLabel>Map Columns</StepLabel>
              </Step>
            </Stepper>
          </Box>

          {/* Step 0: File Upload */}
          {csvWorkflow.step === 0 && (
            <Paper
              variant="outlined"
              sx={{
                p: 4,
                textAlign: 'center',
                borderStyle: 'dashed',
                borderWidth: 2,
                borderColor: 'divider',
                bgcolor: 'background.paper',
                transition: 'all 0.2s ease'
              }}
            >
              <TableChart sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
              
              <Typography variant="h6" gutterBottom>
                Select CSV File to Import
              </Typography>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Upload a CSV file with asset data to import multiple assets at once
              </Typography>

              <Button 
                variant="outlined" 
                component="label"
                sx={{
                  cursor: 'pointer',
                  '&:hover': {
                    bgcolor: 'action.hover'
                  }
                }}
              >
                Choose CSV File
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => handleCSVFileSelect(e.target.files[0])}
                  style={{ display: 'none' }}
                />
              </Button>

              <Typography variant="caption" display="block" sx={{ mt: 2 }}>
                Maximum file size: 5MB • Maximum 50 rows
              </Typography>
            </Paper>
          )}

          {/* Step 1: CSV Parser */}
          {csvWorkflow.step === 1 && csvWorkflow.file && (
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Parse CSV File: {csvWorkflow.file.name}
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={resetCSVWorkflow}
                >
                  Start Over
                </Button>
              </Box>
              
              <CSVParser
                ref={csvParserRef}
                file={csvWorkflow.file}
                onParsedData={handleCSVParsed}
                maxRows={maxFiles}
                showPreview={true}
              />
            </Paper>
          )}

          {/* Step 2: Column Mapping */}
          {csvWorkflow.step === 2 && csvWorkflow.parsedData && (
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Map CSV Columns to Asset Fields
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={resetCSVWorkflow}
                >
                  Start Over
                </Button>
              </Box>
              
              <CSVColumnMapper
                csvData={csvWorkflow.parsedData.data}
                csvHeaders={csvWorkflow.parsedData.meta.fields}
                onMappingComplete={handleCSVMapped}
                currentAccount={currentAccount}
              />
            </Paper>
          )}
        </Box>
      )}

      {/* Files Summary */}
      {hasFiles && (
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Selected Files ({currentFiles.length})
            </Typography>
            <Chip 
              label={`${totalAssets} assets total`} 
              color={totalAssets > maxFiles ? 'error' : 'primary'}
              variant="outlined"
            />
          </Box>

          {totalAssets > maxFiles && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Too many assets ({totalAssets}/{maxFiles}). Please remove some files or assets.
            </Alert>
          )}

          <List>
            {currentFiles.map((file) => {
              const validation = fileValidation[file.name];
              const isExpanded = expandedFiles.has(file.name);
              
              return (
                <Box key={file.name}>
                  <ListItem
                    sx={{
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      mb: 1
                    }}
                  >
                    <ListItemIcon>
                      {getValidationIcon(validation)}
                    </ListItemIcon>
                    
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body1">{file.name}</Typography>
                          {validation && (
                            <Chip 
                              size="small" 
                              label={`${validation.assetCount} assets`}
                              color={validation.isValid ? 'success' : 'error'}
                            />
                          )}
                        </Box>
                      }
                      secondary={`${(file.size / 1024).toFixed(2)} KB`}
                    />

                    <IconButton onClick={() => previewFile(file)} size="small">
                      <Visibility />
                    </IconButton>
                    
                    <IconButton 
                      onClick={() => toggleFileExpansion(file.name)} 
                      size="small"
                    >
                      {isExpanded ? <ExpandLess /> : <ExpandMore />}
                    </IconButton>
                    
                    <IconButton 
                      onClick={() => removeFile(file.name)} 
                      size="small"
                      color="error"
                    >
                      <Delete />
                    </IconButton>
                  </ListItem>

                  {/* Validation Details */}
                  <Collapse in={isExpanded}>
                    <Box sx={{ pl: 4, pr: 2, pb: 2 }}>
                      {validation?.errors.length > 0 && (
                        <Alert severity="error" sx={{ mb: 1 }}>
                          <Typography variant="body2" fontWeight="bold">Errors:</Typography>
                          <ul style={{ margin: 0, paddingLeft: 16 }}>
                            {validation.errors.map((error, i) => (
                              <li key={i}>{error}</li>
                            ))}
                          </ul>
                        </Alert>
                      )}
                      
                      {validation?.warnings.length > 0 && (
                        <Alert severity="warning" sx={{ mb: 1 }}>
                          <Typography variant="body2" fontWeight="bold">Warnings:</Typography>
                          <ul style={{ margin: 0, paddingLeft: 16 }}>
                            {validation.warnings.map((warning, i) => (
                              <li key={i}>{warning}</li>
                            ))}
                          </ul>
                        </Alert>
                      )}
                      
                      {validation?.isValid && (
                        <Alert severity="success">
                          File is valid and ready for upload
                        </Alert>
                      )}
                    </Box>
                  </Collapse>
                </Box>
              );
            })}
          </List>
        </Box>
      )}

      {/* Preview Dialog */}
      <Dialog 
        open={previewDialog.open} 
        onClose={() => setPreviewDialog({ open: false, content: null, fileName: '' })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Description sx={{ mr: 1 }} />
          Preview: {previewDialog.fileName}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            rows={20}
            value={previewDialog.content || ''}
            InputProps={{
              readOnly: true,
              sx: { fontFamily: 'monospace', fontSize: '0.875rem' }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialog({ open: false, content: null, fileName: '' })}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BatchUploadZone;