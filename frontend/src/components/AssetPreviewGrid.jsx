import { useState, useMemo, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  IconButton,
  Chip,
  TextField,
  InputAdornment,
  Checkbox,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  Alert,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import {
  Search,
  Edit,
  Delete,
  ContentCopy,
  MoreVert,
  Visibility,
  Error,
  Warning,
  CheckCircle,
  ExpandMore,
  SelectAll,
  Clear,
  FilterList,
  Add,
  Close,
  HelpOutline,
  Info
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';

const AssetPreviewGrid = ({
  assets = [],
  onAssetsChange,
  onAssetDelete,
  showBulkActions = true,
  maxAssets = 50
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAssets, setSelectedAssets] = useState(new Set());
  const [sortBy, setSortBy] = useState('name');
  const [filterBy, setFilterBy] = useState('all');
  const [bulkMenu, setBulkMenu] = useState(null);
  const [editDialog, setEditDialog] = useState({ open: false, asset: null, index: -1 });
  const [newCriticalFieldName, setNewCriticalFieldName] = useState('');
  const [newCriticalFieldValue, setNewCriticalFieldValue] = useState('');
  const [newNonCriticalFieldName, setNewNonCriticalFieldName] = useState('');
  const [newNonCriticalFieldValue, setNewNonCriticalFieldValue] = useState('');
  const [viewDialog, setViewDialog] = useState({ open: false, asset: null });

  // Validate individual asset
  const validateAsset = useCallback((asset) => {
    const errors = [];
    const warnings = [];

    // Required fields
    if (!asset.assetId) errors.push('Missing asset ID');
    if (!asset.criticalMetadata) {
      errors.push('Missing critical metadata');
    } else {
      if (!asset.criticalMetadata.name) warnings.push('Missing name');
      if (!asset.criticalMetadata.description) warnings.push('Missing description');
    }

    // Check for duplicates
    const duplicateCount = assets.filter(a => a.assetId === asset.assetId).length;
    if (duplicateCount > 1) errors.push('Duplicate asset ID');

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      status: errors.length > 0 ? 'error' : warnings.length > 0 ? 'warning' : 'success'
    };
  }, [assets]);

  // Filter and sort assets
  const filteredAndSortedAssets = useMemo(() => {
    let filtered = assets.filter(asset => {
      // Search filter
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch = !searchTerm || 
        asset.assetId?.toLowerCase().includes(searchLower) ||
        asset.criticalMetadata?.name?.toLowerCase().includes(searchLower) ||
        asset.criticalMetadata?.description?.toLowerCase().includes(searchLower);

      // Status filter
      if (filterBy !== 'all') {
        const validation = validateAsset(asset);
        if (filterBy === 'valid' && validation.status !== 'success') return false;
        if (filterBy === 'warning' && validation.status !== 'warning') return false;
        if (filterBy === 'error' && validation.status !== 'error') return false;
      }

      return matchesSearch;
    });

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return (a.criticalMetadata?.name || '').localeCompare(b.criticalMetadata?.name || '');
        case 'assetId':
          return (a.assetId || '').localeCompare(b.assetId || '');
        case 'source':
          return (a._sourceFile || '').localeCompare(b._sourceFile || '');
        default:
          return 0;
      }
    });

    return filtered;
  }, [assets, searchTerm, filterBy, sortBy, validateAsset]);

  // Handle asset selection
  const handleAssetSelection = useCallback((assetId, checked) => {
    const newSelected = new Set(selectedAssets);
    if (checked) {
      newSelected.add(assetId);
    } else {
      newSelected.delete(assetId);
    }
    setSelectedAssets(newSelected);
  }, [selectedAssets]);

  // Select all/none
  const handleSelectAll = useCallback(() => {
    if (selectedAssets.size === filteredAndSortedAssets.length) {
      setSelectedAssets(new Set());
    } else {
      setSelectedAssets(new Set(filteredAndSortedAssets.map(a => a.assetId)));
    }
  }, [selectedAssets.size, filteredAndSortedAssets]);

  // Duplicate asset
  const duplicateAsset = useCallback((asset, index) => {
    const newAsset = {
      ...asset,
      assetId: `${asset.assetId}_copy_${Date.now()}`,
      _sourceFile: 'Duplicated'
    };
    const newAssets = [...assets];
    newAssets.splice(index + 1, 0, newAsset);
    onAssetsChange(newAssets);
    toast.success('Asset duplicated');
  }, [assets, onAssetsChange]);

  // Edit asset
  const openEditDialog = useCallback((asset, index) => {
    // Ensure both metadata sections exist
    const editableAsset = {
      ...asset,
      criticalMetadata: asset.criticalMetadata || {},
      nonCriticalMetadata: asset.nonCriticalMetadata || {}
    };
    setEditDialog({ open: true, asset: editableAsset, index });
    // Clear any pending field additions
    setNewCriticalFieldName('');
    setNewCriticalFieldValue('');
    setNewNonCriticalFieldName('');
    setNewNonCriticalFieldValue('');
  }, []);

  const saveAssetEdit = useCallback(() => {
    const { asset, index } = editDialog;
    const newAssets = [...assets];
    newAssets[index] = asset;
    onAssetsChange(newAssets);
    setEditDialog({ open: false, asset: null, index: -1 });
    toast.success('Asset updated');
  }, [editDialog, assets, onAssetsChange]);

  // Bulk operations
  const handleBulkDelete = useCallback(() => {
    const newAssets = assets.filter(a => !selectedAssets.has(a.assetId));
    onAssetsChange(newAssets);
    setSelectedAssets(new Set());
    setBulkMenu(null);
    toast.success(`Deleted ${selectedAssets.size} assets`);
  }, [assets, selectedAssets, onAssetsChange]);

  const handleBulkDuplicate = useCallback(() => {
    const selectedAssetObjects = assets.filter(a => selectedAssets.has(a.assetId));
    const duplicates = selectedAssetObjects.map(asset => ({
      ...asset,
      assetId: `${asset.assetId}_copy_${Date.now()}`,
      _sourceFile: 'Bulk Duplicated'
    }));
    onAssetsChange([...assets, ...duplicates]);
    setSelectedAssets(new Set());
    setBulkMenu(null);
    toast.success(`Duplicated ${selectedAssets.size} assets`);
  }, [assets, selectedAssets, onAssetsChange]);

  // Dynamic metadata field management
  const addMetadataField = useCallback((type) => {
    if (type === 'critical') {
      if (!newCriticalFieldName.trim()) return;
      
      const fieldName = newCriticalFieldName.trim();
      // Prevent adding reserved field names
      if (['name', 'description', 'tags'].includes(fieldName)) {
        toast.error(`"${fieldName}" is reserved and managed in the Basic Information section`);
        return;
      }
      
      setEditDialog(prev => ({
        ...prev,
        asset: {
          ...prev.asset,
          criticalMetadata: {
            ...prev.asset.criticalMetadata,
            [fieldName]: newCriticalFieldValue
          }
        }
      }));
      setNewCriticalFieldName('');
      setNewCriticalFieldValue('');
    } else {
      if (!newNonCriticalFieldName.trim()) return;
      setEditDialog(prev => ({
        ...prev,
        asset: {
          ...prev.asset,
          nonCriticalMetadata: {
            ...prev.asset.nonCriticalMetadata,
            [newNonCriticalFieldName.trim()]: newNonCriticalFieldValue
          }
        }
      }));
      setNewNonCriticalFieldName('');
      setNewNonCriticalFieldValue('');
    }
  }, [newCriticalFieldName, newCriticalFieldValue, newNonCriticalFieldName, newNonCriticalFieldValue]);

  const removeMetadataField = useCallback((type, fieldName) => {
    setEditDialog(prev => {
      const asset = { ...prev.asset };
      if (type === 'critical') {
        const { [fieldName]: _, ...remaining } = asset.criticalMetadata;
        asset.criticalMetadata = remaining;
      } else {
        const { [fieldName]: _, ...remaining } = asset.nonCriticalMetadata;
        asset.nonCriticalMetadata = remaining;
      }
      return { ...prev, asset };
    });
  }, []);

  const updateMetadataFieldKey = useCallback((type, oldKey, newKey) => {
    if (!newKey.trim() || oldKey === newKey.trim()) return;
    
    // Prevent renaming to reserved field names in critical metadata
    if (type === 'critical' && ['name', 'description', 'tags'].includes(newKey.trim())) {
      toast.error(`"${newKey.trim()}" is reserved and managed in the Basic Information section`);
      return;
    }
    
    setEditDialog(prev => {
      const asset = { ...prev.asset };
      if (type === 'critical') {
        const value = asset.criticalMetadata[oldKey];
        const { [oldKey]: _, ...remaining } = asset.criticalMetadata;
        asset.criticalMetadata = { ...remaining, [newKey.trim()]: value };
      } else {
        const value = asset.nonCriticalMetadata[oldKey];
        const { [oldKey]: _, ...remaining } = asset.nonCriticalMetadata;
        asset.nonCriticalMetadata = { ...remaining, [newKey.trim()]: value };
      }
      return { ...prev, asset };
    });
  }, []);

  const updateMetadataFieldValue = useCallback((type, key, value) => {
    setEditDialog(prev => ({
      ...prev,
      asset: {
        ...prev.asset,
        [type === 'critical' ? 'criticalMetadata' : 'nonCriticalMetadata']: {
          ...prev.asset[type === 'critical' ? 'criticalMetadata' : 'nonCriticalMetadata'],
          [key]: value
        }
      }
    }));
  }, []);

  // Get validation status icon
  const getValidationIcon = (validation) => {
    switch (validation.status) {
      case 'error': return <Error color="error" />;
      case 'warning': return <Warning color="warning" />;
      case 'success': return <CheckCircle color="success" />;
      default: return null;
    }
  };

  // Get status chip color
  const getStatusColor = (status) => {
    switch (status) {
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'success': return 'success';
      default: return 'default';
    }
  };

  const hasAssets = assets.length > 0;
  const isOverLimit = assets.length > maxAssets;

  return (
    <Box>
      {/* Header Controls */}
      {hasAssets && (
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            {/* Search */}
            <TextField
              size="small"
              placeholder="Search assets..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                )
              }}
              sx={{ minWidth: 200 }}
            />

            {/* Sort */}
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Sort by</InputLabel>
              <Select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                label="Sort by"
              >
                <MenuItem value="name">Name</MenuItem>
                <MenuItem value="assetId">Asset ID</MenuItem>
                <MenuItem value="source">Source</MenuItem>
              </Select>
            </FormControl>

            {/* Filter */}
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Filter</InputLabel>
              <Select
                value={filterBy}
                onChange={(e) => setFilterBy(e.target.value)}
                label="Filter"
                startAdornment={<FilterList />}
              >
                <MenuItem value="all">All</MenuItem>
                <MenuItem value="valid">Valid</MenuItem>
                <MenuItem value="warning">Warnings</MenuItem>
                <MenuItem value="error">Errors</MenuItem>
              </Select>
            </FormControl>

            {/* Bulk Actions */}
            {showBulkActions && (
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <Button
                  size="small"
                  startIcon={selectedAssets.size === filteredAndSortedAssets.length ? <Clear /> : <SelectAll />}
                  onClick={handleSelectAll}
                >
                  {selectedAssets.size === filteredAndSortedAssets.length ? 'None' : 'All'}
                </Button>
                
                {selectedAssets.size > 0 && (
                  <>
                    <Chip 
                      label={`${selectedAssets.size} selected`}
                      size="small"
                      onDelete={() => setSelectedAssets(new Set())}
                    />
                    <Button
                      size="small"
                      onClick={(e) => setBulkMenu(e.currentTarget)}
                      endIcon={<MoreVert />}
                    >
                      Actions
                    </Button>
                  </>
                )}
              </Box>
            )}
          </Box>

          {/* Status Summary */}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              {filteredAndSortedAssets.length} of {assets.length} assets
            </Typography>
            <Chip 
              size="small"
              label={`${assets.length}/${maxAssets}`}
              color={isOverLimit ? 'error' : 'default'}
            />
            {isOverLimit && (
              <Chip 
                size="small"
                label="Over limit"
                color="error"
              />
            )}
          </Box>
        </Box>
      )}

      {/* Over Limit Warning */}
      {isOverLimit && (
        <Alert severity="error" sx={{ mb: 2 }}>
          You have {assets.length} assets, but the maximum is {maxAssets}. 
          Please remove {assets.length - maxAssets} assets before uploading.
        </Alert>
      )}

      {/* Assets Grid */}
      {hasAssets ? (
        <Grid container spacing={2}>
          {filteredAndSortedAssets.map((asset) => {
            const validation = validateAsset(asset);
            const realIndex = assets.findIndex(a => a.assetId === asset.assetId);
            
            return (
              <Grid item xs={12} sm={6} md={4} key={`${asset.assetId}-${realIndex}`}>
                <Card 
                  variant="outlined"
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    border: selectedAssets.has(asset.assetId) ? 2 : 1,
                    borderColor: selectedAssets.has(asset.assetId) ? 'primary.main' : 'divider'
                  }}
                >
                  <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                    {/* Header with checkbox and status */}
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
                      {showBulkActions && (
                        <Checkbox
                          size="small"
                          checked={selectedAssets.has(asset.assetId)}
                          onChange={(e) => handleAssetSelection(asset.assetId, e.target.checked)}
                          sx={{ mt: -0.5, mr: 1 }}
                        />
                      )}
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography variant="h6" component="div" noWrap>
                          {asset.criticalMetadata?.name || 'Unnamed Asset'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" noWrap>
                          ID: {asset.assetId}
                        </Typography>
                      </Box>
                      <Tooltip title={`Status: ${validation.status}`}>
                        {getValidationIcon(validation)}
                      </Tooltip>
                    </Box>

                    {/* Description */}
                    <Typography 
                      variant="body2" 
                      color="text.secondary"
                      sx={{ 
                        mb: 1,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical'
                      }}
                    >
                      {asset.criticalMetadata?.description || 'No description'}
                    </Typography>

                    {/* Tags */}
                    {asset.criticalMetadata?.tags && asset.criticalMetadata.tags.length > 0 && (
                      <Box sx={{ mb: 1 }}>
                        {asset.criticalMetadata.tags.slice(0, 2).map((tag, tagIndex) => (
                          <Chip
                            key={tagIndex}
                            label={tag}
                            size="small"
                            sx={{ mr: 0.5, mb: 0.5 }}
                          />
                        ))}
                        {asset.criticalMetadata.tags.length > 2 && (
                          <Chip
                            label={`+${asset.criticalMetadata.tags.length - 2}`}
                            size="small"
                            variant="outlined"
                          />
                        )}
                      </Box>
                    )}

                    {/* Source File */}
                    {asset._sourceFile && (
                      <Typography variant="caption" color="text.secondary">
                        Source: {asset._sourceFile}
                      </Typography>
                    )}

                    {/* Validation Issues */}
                    {(validation.errors.length > 0 || validation.warnings.length > 0) && (
                      <Accordion sx={{ mt: 1 }} disableGutters>
                        <AccordionSummary
                          expandIcon={<ExpandMore />}
                          sx={{ 
                            minHeight: 32,
                            '& .MuiAccordionSummary-content': { margin: '4px 0' }
                          }}
                        >
                          <Chip
                            size="small"
                            label={`${validation.errors.length + validation.warnings.length} issues`}
                            color={getStatusColor(validation.status)}
                          />
                        </AccordionSummary>
                        <AccordionDetails sx={{ pt: 0 }}>
                          {validation.errors.map((error, i) => (
                            <Typography key={i} variant="caption" color="error" display="block">
                              • {error}
                            </Typography>
                          ))}
                          {validation.warnings.map((warning, i) => (
                            <Typography key={i} variant="caption" color="warning.main" display="block">
                              • {warning}
                            </Typography>
                          ))}
                        </AccordionDetails>
                      </Accordion>
                    )}
                  </CardContent>

                  <Divider />
                  
                  <CardActions sx={{ p: 1 }}>
                    <Button 
                      size="small" 
                      startIcon={<Visibility />}
                      onClick={() => setViewDialog({ open: true, asset })}
                    >
                      View
                    </Button>
                    <Button 
                      size="small" 
                      startIcon={<Edit />}
                      onClick={() => openEditDialog(asset, realIndex)}
                    >
                      Edit
                    </Button>
                    <IconButton 
                      size="small"
                      onClick={() => duplicateAsset(asset, realIndex)}
                    >
                      <ContentCopy />
                    </IconButton>
                    <IconButton 
                      size="small"
                      color="error"
                      onClick={() => onAssetDelete(realIndex)}
                    >
                      <Delete />
                    </IconButton>
                  </CardActions>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      ) : (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No assets to display
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Upload JSON files or paste JSON content to see asset previews here
          </Typography>
        </Box>
      )}

      {/* Bulk Actions Menu */}
      <Menu
        anchorEl={bulkMenu}
        open={Boolean(bulkMenu)}
        onClose={() => setBulkMenu(null)}
      >
        <MenuItem onClick={handleBulkDuplicate}>
          <ContentCopy sx={{ mr: 1 }} />
          Duplicate Selected
        </MenuItem>
        <MenuItem onClick={handleBulkDelete} sx={{ color: 'error.main' }}>
          <Delete sx={{ mr: 1 }} />
          Delete Selected
        </MenuItem>
      </Menu>

      {/* Edit Asset Dialog */}
      <Dialog 
        open={editDialog.open} 
        onClose={() => setEditDialog({ open: false, asset: null, index: -1 })}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: { height: '90vh', maxHeight: '90vh' }
        }}
      >
        <DialogTitle>Edit Asset</DialogTitle>
        <DialogContent>
          {editDialog.asset && (
            <Box sx={{ pt: 1 }}>
              {/* Top Level Fields */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  Basic Information
                </Typography>
                
                <TextField
                  fullWidth
                  label="Asset ID"
                  value={editDialog.asset.assetId || ''}
                  onChange={(e) => setEditDialog(prev => ({
                    ...prev,
                    asset: { ...prev.asset, assetId: e.target.value }
                  }))}
                  margin="normal"
                  required
                  helperText="Unique identifier for your asset"
                />
                
                <TextField
                  fullWidth
                  label="Wallet Address"
                  value={editDialog.asset.walletAddress || ''}
                  onChange={(e) => setEditDialog(prev => ({
                    ...prev,
                    asset: { ...prev.asset, walletAddress: e.target.value }
                  }))}
                  margin="normal"
                  helperText="Optional. If left blank, defaults to your connected wallet"
                  placeholder="0x..."
                />
                
                <TextField
                  fullWidth
                  label="Name"
                  value={editDialog.asset.criticalMetadata?.name || ''}
                  onChange={(e) => setEditDialog(prev => ({
                    ...prev,
                    asset: {
                      ...prev.asset,
                      criticalMetadata: {
                        ...prev.asset.criticalMetadata,
                        name: e.target.value
                      }
                    }
                  }))}
                  margin="normal"
                  helperText="Highly recommended - displayed in dashboard and asset cards for easy identification"
                />
                
                <TextField
                  fullWidth
                  label="Description"
                  multiline
                  rows={3}
                  value={editDialog.asset.criticalMetadata?.description || ''}
                  onChange={(e) => setEditDialog(prev => ({
                    ...prev,
                    asset: {
                      ...prev.asset,
                      criticalMetadata: {
                        ...prev.asset.criticalMetadata,
                        description: e.target.value
                      }
                    }
                  }))}
                  margin="normal"
                  helperText="Highly recommended - helps users understand what this asset represents"
                />
                
                <TextField
                  fullWidth
                  label="Tags (comma-separated)"
                  value={editDialog.asset.criticalMetadata?.tags?.join(', ') || ''}
                  onChange={(e) => setEditDialog(prev => ({
                    ...prev,
                    asset: {
                      ...prev.asset,
                      criticalMetadata: {
                        ...prev.asset.criticalMetadata,
                        tags: e.target.value.split(',').map(tag => tag.trim()).filter(Boolean)
                      }
                    }
                  }))}
                  margin="normal"
                  helperText="Highly recommended - used for filtering and organizing assets in the dashboard"
                />
              </Box>

              <Divider sx={{ my: 3 }} />

              {/* Critical Metadata Section */}
              <Box sx={{ mb: 3, p: 2, border: '1px solid', borderColor: 'primary.main', borderRadius: 1, bgcolor: 'primary.50' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ flexGrow: 1 }}>
                    Additional Critical Metadata
                  </Typography>
                  <Tooltip title="Critical metadata is stored on blockchain and IPFS with high security verification">
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <HelpOutline fontSize="small" color="primary" sx={{ mr: 1 }} />
                      <Typography variant="caption" color="text.secondary">
                        High Security
                      </Typography>
                    </Box>
                  </Tooltip>
                </Box>

                {(!editDialog.asset.criticalMetadata || 
                  Object.keys(editDialog.asset.criticalMetadata).filter(key => !['name', 'description', 'tags'].includes(key)).length === 0) && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
                    No additional critical metadata fields yet. Add your first custom field below.
                  </Typography>
                )}

                {/* Dynamic Critical Metadata Fields */}
                {editDialog.asset.criticalMetadata && Object.entries(editDialog.asset.criticalMetadata)
                  .filter(([key]) => !['name', 'description', 'tags'].includes(key))
                  .map(([key, value]) => (
                  <Box key={key} sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <TextField
                      label="Field Name"
                      value={key}
                      onChange={(e) => updateMetadataFieldKey('critical', key, e.target.value)}
                      sx={{ mr: 2, minWidth: 150 }}
                      size="small"
                    />
                    <TextField
                      label="Value"
                      value={Array.isArray(value) ? value.join(', ') : (value || '')}
                      onChange={(e) => {
                        const newValue = key === 'tags' ? 
                          e.target.value.split(',').map(tag => tag.trim()).filter(Boolean) : 
                          e.target.value;
                        updateMetadataFieldValue('critical', key, newValue);
                      }}
                      sx={{ flexGrow: 1, mr: 1 }}
                      size="small"
                      multiline={key === 'description'}
                      rows={key === 'description' ? 2 : 1}
                      helperText={key === 'tags' ? 'Comma-separated values' : ''}
                    />
                    <IconButton 
                      onClick={() => removeMetadataField('critical', key)}
                      color="error"
                      size="small"
                    >
                      <Close />
                    </IconButton>
                  </Box>
                ))}

                {/* Add New Critical Field */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
                  <TextField
                    label="New Field Name"
                    value={newCriticalFieldName}
                    onChange={(e) => setNewCriticalFieldName(e.target.value)}
                    size="small"
                    sx={{ minWidth: 150 }}
                  />
                  <TextField
                    label="Value"
                    value={newCriticalFieldValue}
                    onChange={(e) => setNewCriticalFieldValue(e.target.value)}
                    size="small"
                    sx={{ flexGrow: 1 }}
                  />
                  <Button
                    startIcon={<Add />}
                    onClick={() => addMetadataField('critical')}
                    variant="outlined"
                    size="small"
                    disabled={!newCriticalFieldName.trim()}
                  >
                    Add
                  </Button>
                </Box>
              </Box>

              <Divider sx={{ my: 3 }} />

              {/* Non-Critical Metadata Section */}
              <Box sx={{ mb: 2, p: 2, border: '1px solid', borderColor: 'info.main', borderRadius: 1, bgcolor: 'info.50' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ flexGrow: 1 }}>
                    Non-Critical Metadata
                  </Typography>
                  <Tooltip title="Non-critical metadata is stored in database with standard security">
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Info fontSize="small" color="info" sx={{ mr: 1 }} />
                      <Typography variant="caption" color="text.secondary">
                        Standard Security
                      </Typography>
                    </Box>
                  </Tooltip>
                </Box>

                {(!editDialog.asset.nonCriticalMetadata || Object.keys(editDialog.asset.nonCriticalMetadata).length === 0) && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
                    No non-critical metadata fields yet. Add your first field below.
                  </Typography>
                )}

                {/* Dynamic Non-Critical Metadata Fields */}
                {editDialog.asset.nonCriticalMetadata && Object.entries(editDialog.asset.nonCriticalMetadata).map(([key, value]) => (
                  <Box key={key} sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <TextField
                      label="Field Name"
                      value={key}
                      onChange={(e) => updateMetadataFieldKey('nonCritical', key, e.target.value)}
                      sx={{ mr: 2, minWidth: 150 }}
                      size="small"
                    />
                    <TextField
                      label="Value"
                      value={Array.isArray(value) ? value.join(', ') : (value || '')}
                      onChange={(e) => updateMetadataFieldValue('nonCritical', key, e.target.value)}
                      sx={{ flexGrow: 1, mr: 1 }}
                      size="small"
                    />
                    <IconButton 
                      onClick={() => removeMetadataField('nonCritical', key)}
                      color="error"
                      size="small"
                    >
                      <Close />
                    </IconButton>
                  </Box>
                ))}

                {/* Add New Non-Critical Field */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
                  <TextField
                    label="New Field Name"
                    value={newNonCriticalFieldName}
                    onChange={(e) => setNewNonCriticalFieldName(e.target.value)}
                    size="small"
                    sx={{ minWidth: 150 }}
                  />
                  <TextField
                    label="Value"
                    value={newNonCriticalFieldValue}
                    onChange={(e) => setNewNonCriticalFieldValue(e.target.value)}
                    size="small"
                    sx={{ flexGrow: 1 }}
                  />
                  <Button
                    startIcon={<Add />}
                    onClick={() => addMetadataField('nonCritical')}
                    variant="outlined"
                    size="small"
                    disabled={!newNonCriticalFieldName.trim()}
                  >
                    Add
                  </Button>
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setEditDialog({ open: false, asset: null, index: -1 });
            setNewCriticalFieldName('');
            setNewCriticalFieldValue('');
            setNewNonCriticalFieldName('');
            setNewNonCriticalFieldValue('');
          }}>
            Cancel
          </Button>
          <Button onClick={saveAssetEdit} variant="contained">
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* View Asset Dialog */}
      <Dialog 
        open={viewDialog.open} 
        onClose={() => setViewDialog({ open: false, asset: null })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Asset Details</DialogTitle>
        <DialogContent>
          {viewDialog.asset && (
            <Box sx={{ pt: 1 }}>
              <TextField
                fullWidth
                multiline
                rows={20}
                value={JSON.stringify(viewDialog.asset, null, 2)}
                InputProps={{
                  readOnly: true,
                  sx: { fontFamily: 'monospace', fontSize: '0.875rem' }
                }}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialog({ open: false, asset: null })}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AssetPreviewGrid;