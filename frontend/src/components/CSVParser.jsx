import { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Divider,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  ExpandMore,
  Warning,
  CheckCircle,
  Error,
  Info,
  FileUpload
} from '@mui/icons-material';
import Papa from 'papaparse';
import { toast } from 'react-hot-toast';

const CSVParser = ({
  onParsedData,
  maxRows = 50,
  onError,
  showPreview = true
}) => {
  const [parseStatus, setParseStatus] = useState('idle'); // idle, parsing, success, error
  const [csvData, setCsvData] = useState(null);
  const [parseResults, setParseResults] = useState(null);
  const [selectedDelimiter, setSelectedDelimiter] = useState('auto');
  const [customDelimiter, setCustomDelimiter] = useState('');
  const [hasHeader, setHasHeader] = useState(true);
  const [encoding, setEncoding] = useState('UTF-8');
  const [previewExpanded, setPreviewExpanded] = useState(true);

  // CSV parsing configuration
  const delimiters = {
    auto: 'Auto-detect',
    ',': 'Comma (,)',
    ';': 'Semicolon (;)',
    '\t': 'Tab',
    '|': 'Pipe (|)',
    custom: 'Custom'
  };

  // Parse CSV file
  const parseCSV = useCallback((file, config = {}) => {
    setParseStatus('parsing');
    
    const parseConfig = {
      header: hasHeader,
      skipEmptyLines: true,
      delimiter: selectedDelimiter === 'auto' ? '' : selectedDelimiter === 'custom' ? customDelimiter : selectedDelimiter,
      encoding: encoding,
      transformHeader: (header) => header.trim(),
      transform: (value) => value.trim(),
      complete: (results) => {
        try {
          validateAndProcessResults(results, file);
        } catch (error) {
          handleParseError(error);
        }
      },
      error: (error) => {
        handleParseError(error);
      },
      ...config
    };

    Papa.parse(file, parseConfig);
  }, [hasHeader, selectedDelimiter, customDelimiter, encoding]);

  // Validate and process parse results
  const validateAndProcessResults = useCallback((results, file) => {
    const errors = [];
    const warnings = [];
    
    // Basic validation
    if (!results.data || results.data.length === 0) {
      errors.push('CSV file is empty or contains no valid data');
    }

    // Check for parsing errors
    if (results.errors && results.errors.length > 0) {
      results.errors.forEach(error => {
        if (error.type === 'Delimiter') {
          warnings.push(`Delimiter detection issue on row ${error.row}: ${error.message}`);
        } else {
          errors.push(`Parse error on row ${error.row}: ${error.message}`);
        }
      });
    }

    // Validate data structure
    if (results.data.length > 0) {
      const firstRow = results.data[0];
      const columnCount = Array.isArray(firstRow) ? firstRow.length : Object.keys(firstRow).length;
      
      if (columnCount === 0) {
        errors.push('No columns detected in CSV file');
      } else if (columnCount === 1) {
        warnings.push('Only one column detected - check if delimiter is correct');
      }

      // Check for too many rows
      if (results.data.length > maxRows) {
        warnings.push(`CSV contains ${results.data.length} rows, but only first ${maxRows} will be processed`);
        results.data = results.data.slice(0, maxRows);
      }
    }

    // Check for headers
    if (hasHeader && results.meta.fields) {
      const duplicateHeaders = results.meta.fields.filter((field, index, arr) => 
        arr.indexOf(field) !== index
      );
      
      if (duplicateHeaders.length > 0) {
        warnings.push(`Duplicate column headers found: ${duplicateHeaders.join(', ')}`);
      }

      const emptyHeaders = results.meta.fields.filter(field => !field || field.trim() === '');
      if (emptyHeaders.length > 0) {
        warnings.push(`${emptyHeaders.length} empty column header(s) found`);
      }
    }

    const processedResults = {
      ...results,
      fileName: file.name,
      fileSize: file.size,
      rowCount: results.data.length,
      columnCount: results.meta.fields ? results.meta.fields.length : 0,
      errors,
      warnings,
      isValid: errors.length === 0
    };

    setParseResults(processedResults);
    setCsvData(results.data);
    setParseStatus(errors.length === 0 ? 'success' : 'error');

    if (errors.length === 0) {
      onParsedData?.(processedResults);
      toast.success(`CSV parsed successfully: ${processedResults.rowCount} rows, ${processedResults.columnCount} columns`);
    } else {
      onError?.(errors);
    }
  }, [maxRows, hasHeader, onParsedData, onError]);

  // Handle parse errors
  const handleParseError = useCallback((error) => {
    setParseStatus('error');
    const errorMessage = error.message || 'Failed to parse CSV file';
    setParseResults({
      errors: [errorMessage],
      warnings: [],
      isValid: false
    });
    onError?.([errorMessage]);
    toast.error(`CSV parse error: ${errorMessage}`);
  }, [onError]);

  // Handle file selection
  const handleFileSelect = useCallback((file) => {
    if (!file) return;

    // Validate file type
    if (!file.name.toLowerCase().endsWith('.csv')) {
      toast.error('Please select a CSV file');
      return;
    }

    // Validate file size (5MB limit)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('CSV file is too large. Maximum size is 5MB');
      return;
    }

    parseCSV(file);
  }, [parseCSV]);

  // Get preview data (first 10 rows)
  const previewData = useMemo(() => {
    if (!csvData || !Array.isArray(csvData)) return null;
    return csvData.slice(0, 10);
  }, [csvData]);

  // Get status icon and color
  const getStatusDisplay = () => {
    switch (parseStatus) {
      case 'parsing':
        return { icon: <LinearProgress />, color: 'info', text: 'Parsing CSV...' };
      case 'success':
        return { icon: <CheckCircle />, color: 'success', text: 'CSV parsed successfully' };
      case 'error':
        return { icon: <Error />, color: 'error', text: 'Parse errors found' };
      default:
        return { icon: <Info />, color: 'info', text: 'Select a CSV file to begin' };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <Box>
      {/* Configuration Section */}
      <Paper variant="outlined" sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          CSV Parser Configuration
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Delimiter</InputLabel>
            <Select
              value={selectedDelimiter}
              onChange={(e) => setSelectedDelimiter(e.target.value)}
              label="Delimiter"
            >
              {Object.entries(delimiters).map(([value, label]) => (
                <MenuItem key={value} value={value}>{label}</MenuItem>
              ))}
            </Select>
          </FormControl>

          {selectedDelimiter === 'custom' && (
            <TextField
              size="small"
              label="Custom Delimiter"
              value={customDelimiter}
              onChange={(e) => setCustomDelimiter(e.target.value)}
              sx={{ width: 120 }}
              placeholder="Enter delimiter"
            />
          )}

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Headers</InputLabel>
            <Select
              value={hasHeader}
              onChange={(e) => setHasHeader(e.target.value)}
              label="Headers"
            >
              <MenuItem value={true}>First row is headers</MenuItem>
              <MenuItem value={false}>No headers</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Encoding</InputLabel>
            <Select
              value={encoding}
              onChange={(e) => setEncoding(e.target.value)}
              label="Encoding"
            >
              <MenuItem value="UTF-8">UTF-8</MenuItem>
              <MenuItem value="ISO-8859-1">Latin-1</MenuItem>
              <MenuItem value="Windows-1252">Windows-1252</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <Button
          variant="outlined"
          component="label"
          startIcon={<FileUpload />}
          disabled={parseStatus === 'parsing'}
        >
          {parseStatus === 'parsing' ? 'Parsing...' : 'Select CSV File'}
          <input
            type="file"
            accept=".csv"
            onChange={(e) => handleFileSelect(e.target.files[0])}
            style={{ display: 'none' }}
          />
        </Button>
      </Paper>

      {/* Status Display */}
      {parseStatus !== 'idle' && (
        <Alert 
          severity={statusDisplay.color} 
          icon={statusDisplay.icon}
          sx={{ mb: 2 }}
        >
          {statusDisplay.text}
          {parseResults && (
            <Box sx={{ mt: 1 }}>
              {parseResults.fileName && (
                <Typography variant="body2">
                  File: {parseResults.fileName} ({(parseResults.fileSize / 1024).toFixed(2)} KB)
                </Typography>
              )}
              {parseResults.rowCount !== undefined && (
                <Typography variant="body2">
                  Rows: {parseResults.rowCount} | Columns: {parseResults.columnCount}
                </Typography>
              )}
            </Box>
          )}
        </Alert>
      )}

      {/* Errors and Warnings */}
      {parseResults?.errors?.length > 0 && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="body2" fontWeight="bold">Errors:</Typography>
          <ul style={{ margin: 0, paddingLeft: 16 }}>
            {parseResults.errors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </Alert>
      )}

      {parseResults?.warnings?.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <Typography variant="body2" fontWeight="bold">Warnings:</Typography>
          <ul style={{ margin: 0, paddingLeft: 16 }}>
            {parseResults.warnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))}
          </ul>
        </Alert>
      )}

      {/* Data Preview */}
      {showPreview && previewData && parseResults?.isValid && (
        <Accordion 
          expanded={previewExpanded}
          onChange={() => setPreviewExpanded(!previewExpanded)}
        >
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">
              Data Preview ({previewData.length} of {parseResults.rowCount} rows)
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell><strong>#</strong></TableCell>
                    {parseResults.meta.fields?.map((field, index) => (
                      <TableCell key={index}>
                        <strong>{field || `Column ${index + 1}`}</strong>
                      </TableCell>
                    )) || Object.keys(previewData[0] || {}).map((key, index) => (
                      <TableCell key={index}>
                        <strong>{key}</strong>
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {previewData.map((row, index) => (
                    <TableRow key={index}>
                      <TableCell>{index + 1}</TableCell>
                      {Array.isArray(row) 
                        ? row.map((cell, cellIndex) => (
                            <TableCell key={cellIndex}>
                              {cell?.toString().substring(0, 50)}
                              {cell?.toString().length > 50 && '...'}
                            </TableCell>
                          ))
                        : Object.values(row).map((cell, cellIndex) => (
                            <TableCell key={cellIndex}>
                              {cell?.toString().substring(0, 50)}
                              {cell?.toString().length > 50 && '...'}
                            </TableCell>
                          ))
                      }
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Summary Stats */}
      {parseResults?.isValid && (
        <Box sx={{ display: 'flex', gap: 1, mt: 2, flexWrap: 'wrap' }}>
          <Chip 
            icon={<CheckCircle />} 
            label={`${parseResults.rowCount} rows`} 
            color="success" 
            size="small" 
          />
          <Chip 
            icon={<Info />} 
            label={`${parseResults.columnCount} columns`} 
            color="primary" 
            size="small" 
          />
          {parseResults.warnings.length > 0 && (
            <Chip 
              icon={<Warning />} 
              label={`${parseResults.warnings.length} warnings`} 
              color="warning" 
              size="small" 
            />
          )}
        </Box>
      )}
    </Box>
  );
};

export default CSVParser;