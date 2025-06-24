import { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  Chip,
  Card,
  CardContent,
  Grid,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  ExpandMore,
  CheckCircle,
  Warning,
  Error,
  Info,
  Refresh,
  AutoAwesome,
  Visibility
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';

const CSVColumnMapper = ({
  csvData,
  csvHeaders,
  onMappingComplete,
  onError,
  currentAccount
}) => {
  const [columnMappings, setColumnMappings] = useState({});
  const [previewExpanded, setPreviewExpanded] = useState(true);
  const [validationResults, setValidationResults] = useState(null);
  const [previewData, setPreviewData] = useState([]);

  // Required and optional asset fields
  const assetFields = {
    required: {
      assetId: { label: 'Asset ID', description: 'Unique identifier for the asset' },
      name: { label: 'Asset Name', description: 'Display name for the asset' }
    },
    optional: {
      description: { label: 'Description', description: 'Asset description' },
      tags: { label: 'Tags', description: 'Comma-separated tags' },
      author: { label: 'Author', description: 'Asset creator' },
      category: { label: 'Category', description: 'Asset category' },
      version: { label: 'Version', description: 'Asset version' },
      created_date: { label: 'Created Date', description: 'Creation date' },
      modified_date: { label: 'Modified Date', description: 'Last modification date' },
      status: { label: 'Status', description: 'Asset status' },
      priority: { label: 'Priority', description: 'Asset priority' },
      owner: { label: 'Owner', description: 'Asset owner' }
    },
    special: {
      walletAddress: { label: 'Wallet Address', description: 'Wallet address (will use current account if not mapped)' },
      skip: { label: '(Skip Column)', description: 'Do not import this column' },
      nonCritical: { label: '(Add to Non-Critical Metadata)', description: 'Add to non-critical metadata with original column name' }
    }
  };

  // Auto-detect column mappings based on header names
  const autoDetectMappings = useCallback(() => {
    if (!csvHeaders || csvHeaders.length === 0) return;

    const newMappings = {};
    
    csvHeaders.forEach(header => {
      const lowerHeader = header.toLowerCase().trim();
      
      // Try to match common patterns
      if (lowerHeader.includes('id') || lowerHeader === 'asset_id' || lowerHeader === 'assetid') {
        newMappings[header] = 'assetId';
      } else if (lowerHeader.includes('name') || lowerHeader === 'title') {
        newMappings[header] = 'name';
      } else if (lowerHeader.includes('description') || lowerHeader.includes('desc')) {
        newMappings[header] = 'description';
      } else if (lowerHeader.includes('tag')) {
        newMappings[header] = 'tags';
      } else if (lowerHeader.includes('author') || lowerHeader.includes('creator')) {
        newMappings[header] = 'author';
      } else if (lowerHeader.includes('category') || lowerHeader.includes('type')) {
        newMappings[header] = 'category';
      } else if (lowerHeader.includes('version')) {
        newMappings[header] = 'version';
      } else if (lowerHeader.includes('date') && lowerHeader.includes('creat')) {
        newMappings[header] = 'created_date';
      } else if (lowerHeader.includes('date') && lowerHeader.includes('modif')) {
        newMappings[header] = 'modified_date';
      } else if (lowerHeader.includes('status')) {
        newMappings[header] = 'status';
      } else if (lowerHeader.includes('priority')) {
        newMappings[header] = 'priority';
      } else if (lowerHeader.includes('owner')) {
        newMappings[header] = 'owner';
      } else if (lowerHeader.includes('wallet') || lowerHeader.includes('address')) {
        newMappings[header] = 'walletAddress';
      } else {
        // Default to adding to non-critical metadata
        newMappings[header] = 'nonCritical';
      }
    });

    setColumnMappings(newMappings);
    toast.success('Auto-detection completed. Please review and adjust mappings as needed.');
  }, [csvHeaders]);

  // Handle mapping change
  const handleMappingChange = useCallback((csvColumn, assetField) => {
    setColumnMappings(prev => ({
      ...prev,
      [csvColumn]: assetField
    }));
  }, []);

  // Validate current mappings
  const validateMappings = useCallback(() => {
    const errors = [];
    const warnings = [];
    
    // Check for required fields
    const mappedFields = Object.values(columnMappings);
    
    if (!mappedFields.includes('assetId')) {
      errors.push('Asset ID field is required but not mapped');
    }
    
    if (!mappedFields.includes('name')) {
      warnings.push('Asset Name is recommended but not mapped');
    }

    // Check for duplicate mappings (except skip and nonCritical)
    const duplicates = {};
    Object.entries(columnMappings).forEach(([csvCol, assetField]) => {
      if (assetField !== 'skip' && assetField !== 'nonCritical') {
        if (!duplicates[assetField]) {
          duplicates[assetField] = [];
        }
        duplicates[assetField].push(csvCol);
      }
    });

    Object.entries(duplicates).forEach(([field, columns]) => {
      if (columns.length > 1) {
        errors.push(`Field "${field}" is mapped to multiple columns: ${columns.join(', ')}`);
      }
    });

    // Check unmapped columns
    const unmappedColumns = csvHeaders.filter(header => !columnMappings[header]);
    if (unmappedColumns.length > 0) {
      warnings.push(`${unmappedColumns.length} columns are not mapped: ${unmappedColumns.join(', ')}`);
    }

    const results = {
      isValid: errors.length === 0,
      errors,
      warnings
    };

    setValidationResults(results);
    return results;
  }, [columnMappings, csvHeaders]);

  // Generate preview data
  const generatePreview = useCallback(() => {
    if (!csvData || csvData.length === 0) return [];

    return csvData.slice(0, 5).map((row, index) => {
      const asset = {
        _csvRowIndex: index + 1,
        assetId: '',
        walletAddress: currentAccount,
        criticalMetadata: {},
        nonCriticalMetadata: {}
      };

      // Apply mappings
      Object.entries(columnMappings).forEach(([csvColumn, assetField]) => {
        const value = Array.isArray(row) ? row[csvHeaders.indexOf(csvColumn)] : row[csvColumn];
        
        if (!value || value.toString().trim() === '' || assetField === 'skip') return;

        switch (assetField) {
          case 'assetId':
            asset.assetId = value.toString().trim();
            break;
          case 'walletAddress':
            asset.walletAddress = value.toString().trim();
            break;
          case 'tags':
            // Split comma-separated tags
            asset.criticalMetadata.tags = value.toString().split(',').map(tag => tag.trim()).filter(Boolean);
            break;
          case 'nonCritical':
            asset.nonCriticalMetadata[csvColumn] = value;
            break;
          default:
            // Add to critical metadata
            asset.criticalMetadata[assetField] = value;
            break;
        }
      });

      return asset;
    });
  }, [csvData, csvHeaders, columnMappings, currentAccount]);

  // Update preview when mappings change
  useEffect(() => {
    const preview = generatePreview();
    setPreviewData(preview);
    validateMappings();
  }, [generatePreview, validateMappings]);

  // Handle mapping completion
  const handleComplete = useCallback(() => {
    const validation = validateMappings();
    
    if (!validation.isValid) {
      toast.error('Please fix mapping errors before proceeding');
      return;
    }

    // Generate all assets
    const allAssets = csvData.map((row, index) => {
      const asset = {
        assetId: '',
        walletAddress: currentAccount,
        criticalMetadata: {},
        nonCriticalMetadata: {},
        _sourceFile: 'CSV Import',
        _csvRowIndex: index + 1
      };

      // Apply mappings
      Object.entries(columnMappings).forEach(([csvColumn, assetField]) => {
        const value = Array.isArray(row) ? row[csvHeaders.indexOf(csvColumn)] : row[csvColumn];
        
        if (!value || value.toString().trim() === '' || assetField === 'skip') return;

        switch (assetField) {
          case 'assetId':
            asset.assetId = value.toString().trim();
            break;
          case 'walletAddress':
            asset.walletAddress = value.toString().trim();
            break;
          case 'tags':
            asset.criticalMetadata.tags = value.toString().split(',').map(tag => tag.trim()).filter(Boolean);
            break;
          case 'nonCritical':
            asset.nonCriticalMetadata[csvColumn] = value;
            break;
          default:
            asset.criticalMetadata[assetField] = value;
            break;
        }
      });

      return asset;
    });

    onMappingComplete?.(allAssets, validation);
    toast.success(`Successfully mapped ${allAssets.length} assets from CSV`);
  }, [csvData, csvHeaders, columnMappings, currentAccount, validateMappings, onMappingComplete]);

  // Auto-detect on mount
  useEffect(() => {
    if (csvHeaders && csvHeaders.length > 0 && Object.keys(columnMappings).length === 0) {
      autoDetectMappings();
    }
  }, [csvHeaders, columnMappings, autoDetectMappings]);

  if (!csvHeaders || csvHeaders.length === 0) {
    return (
      <Alert severity="info">
        No CSV data to map. Please parse a CSV file first.
      </Alert>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Column Mapping ({csvHeaders.length} columns)
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            size="small"
            startIcon={<AutoAwesome />}
            onClick={autoDetectMappings}
          >
            Auto-Detect
          </Button>
          <Button
            size="small"
            startIcon={<Refresh />}
            onClick={() => setColumnMappings({})}
          >
            Reset
          </Button>
        </Box>
      </Box>

      {/* Validation Results */}
      {validationResults && (
        <Box sx={{ mb: 2 }}>
          {validationResults.errors.length > 0 && (
            <Alert severity="error" sx={{ mb: 1 }}>
              <Typography variant="body2" fontWeight="bold">Errors:</Typography>
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                {validationResults.errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </Alert>
          )}
          
          {validationResults.warnings.length > 0 && (
            <Alert severity="warning" sx={{ mb: 1 }}>
              <Typography variant="body2" fontWeight="bold">Warnings:</Typography>
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                {validationResults.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </Alert>
          )}
        </Box>
      )}

      {/* Mapping Configuration */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {csvHeaders.map((header, index) => (
          <Grid item xs={12} sm={6} md={4} key={index}>
            <Card variant="outlined">
              <CardContent sx={{ pb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  CSV Column: <strong>{header}</strong>
                </Typography>
                
                <FormControl fullWidth size="small">
                  <InputLabel>Map to Asset Field</InputLabel>
                  <Select
                    value={columnMappings[header] || ''}
                    onChange={(e) => handleMappingChange(header, e.target.value)}
                    label="Map to Asset Field"
                  >
                    <MenuItem value="">
                      <em>Select field...</em>
                    </MenuItem>
                    
                    {/* Required fields */}
                    <Typography variant="overline" sx={{ px: 2, color: 'text.secondary' }}>
                      Required Fields
                    </Typography>
                    {Object.entries(assetFields.required).map(([key, field]) => (
                      <MenuItem key={key} value={key}>
                        <Box>
                          <Typography variant="body2">{field.label}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {field.description}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                    
                    <Divider />
                    
                    {/* Optional fields */}
                    <Typography variant="overline" sx={{ px: 2, color: 'text.secondary' }}>
                      Optional Fields
                    </Typography>
                    {Object.entries(assetFields.optional).map(([key, field]) => (
                      <MenuItem key={key} value={key}>
                        <Box>
                          <Typography variant="body2">{field.label}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {field.description}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                    
                    <Divider />
                    
                    {/* Special options */}
                    <Typography variant="overline" sx={{ px: 2, color: 'text.secondary' }}>
                      Special Options
                    </Typography>
                    {Object.entries(assetFields.special).map(([key, field]) => (
                      <MenuItem key={key} value={key}>
                        <Box>
                          <Typography variant="body2">{field.label}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {field.description}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Show sample value */}
                {csvData && csvData.length > 0 && (
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    Sample: {(Array.isArray(csvData[0]) ? csvData[0][index] : csvData[0][header]) || '(empty)'}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Preview */}
      <Accordion 
        expanded={previewExpanded}
        onChange={() => setPreviewExpanded(!previewExpanded)}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">
            Preview ({previewData.length} of {csvData.length} assets)
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell><strong>Row</strong></TableCell>
                  <TableCell><strong>Asset ID</strong></TableCell>
                  <TableCell><strong>Name</strong></TableCell>
                  <TableCell><strong>Description</strong></TableCell>
                  <TableCell><strong>Tags</strong></TableCell>
                  <TableCell><strong>Other Fields</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {previewData.map((asset, index) => (
                  <TableRow key={index}>
                    <TableCell>{asset._csvRowIndex}</TableCell>
                    <TableCell>
                      {asset.assetId || <em style={{ color: 'red' }}>Missing</em>}
                    </TableCell>
                    <TableCell>
                      {asset.criticalMetadata.name || <em style={{ color: 'orange' }}>Not set</em>}
                    </TableCell>
                    <TableCell>
                      {asset.criticalMetadata.description?.substring(0, 30) || <em>Not set</em>}
                      {asset.criticalMetadata.description?.length > 30 && '...'}
                    </TableCell>
                    <TableCell>
                      {asset.criticalMetadata.tags?.map((tag, i) => (
                        <Chip key={i} label={tag} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                      ))}
                    </TableCell>
                    <TableCell>
                      <Tooltip title={JSON.stringify({ 
                        ...asset.criticalMetadata, 
                        ...asset.nonCriticalMetadata 
                      }, null, 2)}>
                        <IconButton size="small">
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </AccordionDetails>
      </Accordion>

      {/* Action Buttons */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
        <Button
          variant="outlined"
          onClick={() => setColumnMappings({})}
        >
          Reset Mappings
        </Button>
        <Button
          variant="contained"
          onClick={handleComplete}
          disabled={!validationResults?.isValid}
          startIcon={validationResults?.isValid ? <CheckCircle /> : <Error />}
        >
          Import {csvData.length} Assets
        </Button>
      </Box>
    </Box>
  );
};

export default CSVColumnMapper;