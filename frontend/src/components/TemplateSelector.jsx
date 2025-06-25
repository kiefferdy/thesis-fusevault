import { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Grid,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
  Badge
} from '@mui/material';
import {
  Add,
  Description,
  Palette,
  CardMembership,
  Image,
  VideoLibrary,
  AudioFile,
  Code,
  Science,
  Business,
  School,
  ExpandMore,
  Edit,
  Delete,
  Visibility,
  ContentCopy,
  Download,
  Upload,
  Save,
  Clear
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';

const TemplateSelector = ({
  onCreateAssets,
  currentAccount,
  maxAssets = 50,
  currentAssetCount = 0,
  onCreateTemplateClick
}) => {
  const [createDialog, setCreateDialog] = useState({ open: false, template: null, quantity: 1 });
  const [templateDialog, setTemplateDialog] = useState({ open: false, mode: 'create', template: null });
  const [customTemplates, setCustomTemplates] = useState([]);
  const [previewDialog, setPreviewDialog] = useState({ open: false, template: null });

  // Built-in templates
  const builtInTemplates = useMemo(() => [
    {
      id: 'document',
      name: 'Document',
      description: 'General document template with standard metadata fields',
      icon: <Description color="primary" />,
      category: 'General',
      color: 'primary',
      template: {
        assetId: '', // Will be auto-generated
        criticalMetadata: {
          name: '',
          description: '',
          document_type: '',
          author: '',
          version: '1.0',
          creation_date: new Date().toISOString().split('T')[0],
          language: 'en',
          tags: []
        },
        nonCriticalMetadata: {
          file_size: '',
          format: '',
          keywords: [],
          department: '',
          classification: 'public'
        }
      },
      sampleData: {
        name: 'Sample Document',
        description: 'This is a sample document for demonstration',
        document_type: 'Report',
        author: 'John Doe',
        tags: ['sample', 'demo']
      }
    },
    {
      id: 'artwork',
      name: 'Digital Artwork',
      description: 'Template for digital art and creative works',
      icon: <Palette color="secondary" />,
      category: 'Creative',
      color: 'secondary',
      template: {
        assetId: '',
        criticalMetadata: {
          name: '',
          description: '',
          artist: '',
          medium: 'Digital',
          dimensions: '',
          year_created: new Date().getFullYear(),
          style: '',
          tags: []
        },
        nonCriticalMetadata: {
          resolution: '',
          color_profile: '',
          software_used: '',
          edition_number: '',
          series: '',
          inspiration: ''
        }
      },
      sampleData: {
        name: 'Digital Landscape',
        description: 'A beautiful digital landscape artwork',
        artist: 'Jane Artist',
        medium: 'Digital Painting',
        dimensions: '1920x1080',
        tags: ['landscape', 'digital', 'art']
      }
    },
    {
      id: 'certificate',
      name: 'Certificate',
      description: 'Template for certificates and credentials',
      icon: <CardMembership color="success" />,
      category: 'Academic',
      color: 'success',
      template: {
        assetId: '',
        criticalMetadata: {
          name: '',
          description: '',
          issuer: '',
          recipient: '',
          issue_date: new Date().toISOString().split('T')[0],
          expiration_date: '',
          certificate_type: '',
          credential_level: '',
          tags: []
        },
        nonCriticalMetadata: {
          verification_code: '',
          course_duration: '',
          grade: '',
          instructor: '',
          institution_address: '',
          accreditation: ''
        }
      },
      sampleData: {
        name: 'Blockchain Development Certificate',
        description: 'Certificate of completion for blockchain development course',
        issuer: 'Tech Academy',
        recipient: 'Student Name',
        certificate_type: 'Course Completion',
        tags: ['blockchain', 'certificate', 'development']
      }
    },
    {
      id: 'media',
      name: 'Media Asset',
      description: 'Template for images, videos, and audio files',
      icon: <Image color="info" />,
      category: 'Media',
      color: 'info',
      template: {
        assetId: '',
        criticalMetadata: {
          name: '',
          description: '',
          media_type: '',
          creator: '',
          creation_date: new Date().toISOString().split('T')[0],
          duration: '',
          resolution: '',
          tags: []
        },
        nonCriticalMetadata: {
          file_format: '',
          codec: '',
          bitrate: '',
          fps: '',
          color_space: '',
          camera_model: '',
          location: ''
        }
      },
      sampleData: {
        name: 'Product Photo',
        description: 'High-resolution product photography',
        media_type: 'Image',
        creator: 'Photographer Name',
        resolution: '4K',
        tags: ['product', 'photography', 'commercial']
      }
    },
    {
      id: 'research',
      name: 'Research Data',
      description: 'Template for research papers and scientific data',
      icon: <Science color="warning" />,
      category: 'Academic',
      color: 'warning',
      template: {
        assetId: '',
        criticalMetadata: {
          name: '',
          description: '',
          research_type: '',
          authors: [],
          institution: '',
          publication_date: new Date().toISOString().split('T')[0],
          methodology: '',
          tags: []
        },
        nonCriticalMetadata: {
          funding_source: '',
          peer_reviewed: false,
          journal: '',
          doi: '',
          ethical_approval: '',
          data_availability: ''
        }
      },
      sampleData: {
        name: 'Blockchain Consensus Study',
        description: 'Comparative analysis of blockchain consensus mechanisms',
        research_type: 'Comparative Study',
        authors: ['Dr. Smith', 'Dr. Johnson'],
        institution: 'Research University',
        tags: ['blockchain', 'consensus', 'research']
      }
    },
    {
      id: 'contract',
      name: 'Legal Contract',
      description: 'Template for contracts and legal documents',
      icon: <Business color="error" />,
      category: 'Legal',
      color: 'error',
      template: {
        assetId: '',
        criticalMetadata: {
          name: '',
          description: '',
          contract_type: '',
          parties: [],
          execution_date: new Date().toISOString().split('T')[0],
          jurisdiction: '',
          governing_law: '',
          tags: []
        },
        nonCriticalMetadata: {
          value: '',
          currency: '',
          duration: '',
          renewal_terms: '',
          confidentiality: true,
          dispute_resolution: ''
        }
      },
      sampleData: {
        name: 'Service Agreement',
        description: 'Professional services contract',
        contract_type: 'Service Agreement',
        parties: ['Company A', 'Company B'],
        jurisdiction: 'United States',
        tags: ['contract', 'services', 'legal']
      }
    }
  ], []);

  // All templates combined
  const allTemplates = useMemo(() => [
    ...builtInTemplates,
    ...customTemplates
  ], [builtInTemplates, customTemplates]);

  // Group templates by category
  const templatesByCategory = useMemo(() => {
    const categories = {};
    allTemplates.forEach(template => {
      const category = template.category || 'Custom';
      if (!categories[category]) {
        categories[category] = [];
      }
      categories[category].push(template);
    });
    return categories;
  }, [allTemplates]);

  // Create assets from template
  const handleCreateFromTemplate = useCallback((template, quantity = 1) => {
    if (currentAssetCount + quantity > maxAssets) {
      toast.error(`Cannot create ${quantity} assets. Would exceed maximum of ${maxAssets} assets.`);
      return;
    }

    const newAssets = [];
    for (let i = 0; i < quantity; i++) {
      const assetId = `${template.id}_${Date.now()}_${i + 1}`;
      const asset = {
        ...template.template,
        assetId,
        walletAddress: currentAccount,
        _sourceFile: `Template: ${template.name}`,
        criticalMetadata: {
          ...template.template.criticalMetadata,
          // Apply sample data if fields are empty
          ...Object.fromEntries(
            Object.entries(template.sampleData || {}).map(([key, value]) => [
              key,
              quantity > 1 && key === 'name' ? `${value} ${i + 1}` : value
            ])
          )
        }
      };
      newAssets.push(asset);
    }

    onCreateAssets(newAssets);
    setCreateDialog({ open: false, template: null, quantity: 1 });
    toast.success(`Created ${quantity} asset(s) from ${template.name} template`);
  }, [currentAssetCount, maxAssets, currentAccount, onCreateAssets]);


  // Delete custom template
  const handleDeleteTemplate = useCallback((templateId) => {
    setCustomTemplates(prev => prev.filter(t => t.id !== templateId));
    toast.success('Template deleted');
  }, []);

  // Template preview
  const handlePreviewTemplate = useCallback((template) => {
    setPreviewDialog({ open: true, template });
  }, []);

  // Handle create template click
  const handleCreateTemplateClick = useCallback(() => {
    setTemplateDialog({ open: true, mode: 'create', template: null });
  }, []);

  // Expose create template function to parent
  useEffect(() => {
    if (onCreateTemplateClick) {
      onCreateTemplateClick(handleCreateTemplateClick);
    }
  }, [onCreateTemplateClick, handleCreateTemplateClick]);

  return (
    <Box>
      {/* Templates by Category */}
      {Object.entries(templatesByCategory).map(([category, templates]) => (
        <Accordion key={category} defaultExpanded={category !== 'Custom'}>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6">{category}</Typography>
              <Badge badgeContent={templates.length} color="primary" />
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              {templates.map((template) => (
                <Grid item xs={12} sm={6} md={4} key={template.id}>
                  <Card 
                    variant="outlined"
                    sx={{
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column'
                    }}
                  >
                    <CardContent sx={{ flexGrow: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        {template.icon}
                        <Typography variant="h6" sx={{ ml: 1 }}>
                          {template.name}
                        </Typography>
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary" paragraph>
                        {template.description}
                      </Typography>

                      <Chip 
                        size="small" 
                        label={template.category} 
                        color={template.color || 'default'}
                        variant="outlined"
                      />
                    </CardContent>

                    <Divider />

                    <CardActions>
                      <Button 
                        size="small" 
                        startIcon={<Visibility />}
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePreviewTemplate(template);
                        }}
                      >
                        Preview
                      </Button>
                      <Button 
                        size="small" 
                        startIcon={<Add />}
                        onClick={(e) => {
                          e.stopPropagation();
                          setCreateDialog({ open: true, template, quantity: 1 });
                        }}
                      >
                        Use
                      </Button>
                      {template.isCustom && (
                        <IconButton 
                          size="small"
                          color="error"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteTemplate(template.id);
                          }}
                        >
                          <Delete />
                        </IconButton>
                      )}
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </AccordionDetails>
        </Accordion>
      ))}

      {/* Create Assets Dialog */}
      <Dialog
        open={createDialog.open}
        onClose={() => setCreateDialog({ open: false, template: null, quantity: 1 })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Create Assets from Template
        </DialogTitle>
        <DialogContent>
          {createDialog.template && (
            <Box sx={{ pt: 1 }}>
              <Alert severity="info" sx={{ mb: 2 }}>
                Creating assets from: <strong>{createDialog.template.name}</strong>
              </Alert>
              
              <TextField
                fullWidth
                type="number"
                label="Number of assets to create"
                value={createDialog.quantity}
                onChange={(e) => setCreateDialog(prev => ({
                  ...prev,
                  quantity: Math.max(1, Math.min(maxAssets - currentAssetCount, parseInt(e.target.value) || 1))
                }))}
                inputProps={{ 
                  min: 1, 
                  max: maxAssets - currentAssetCount 
                }}
                helperText={`You can create up to ${maxAssets - currentAssetCount} more assets`}
              />

              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Each asset will be created with sample data that you can modify after creation.
                Asset IDs will be automatically generated.
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialog({ open: false, template: null, quantity: 1 })}>
            Cancel
          </Button>
          <Button 
            variant="contained"
            onClick={() => handleCreateFromTemplate(createDialog.template, createDialog.quantity)}
            disabled={createDialog.quantity < 1 || currentAssetCount + createDialog.quantity > maxAssets}
          >
            Create {createDialog.quantity} Asset{createDialog.quantity > 1 ? 's' : ''}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Template Preview Dialog */}
      <Dialog
        open={previewDialog.open}
        onClose={() => setPreviewDialog({ open: false, template: null })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Template Preview: {previewDialog.template?.name}
        </DialogTitle>
        <DialogContent>
          {previewDialog.template && (
            <Box>
              <Typography variant="body2" color="text.secondary" paragraph>
                {previewDialog.template.description}
              </Typography>
              
              <TextField
                fullWidth
                multiline
                rows={20}
                label="Template Structure"
                value={JSON.stringify(previewDialog.template.template, null, 2)}
                InputProps={{
                  readOnly: true,
                  sx: { fontFamily: 'monospace', fontSize: '0.875rem' }
                }}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialog({ open: false, template: null })}>
            Close
          </Button>
          {previewDialog.template && (
            <Button 
              variant="contained"
              startIcon={<Add />}
              onClick={() => {
                setPreviewDialog({ open: false, template: null });
                setCreateDialog({ open: true, template: previewDialog.template, quantity: 1 });
              }}
            >
              Use Template
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Create/Edit Template Dialog */}
      <Dialog
        open={templateDialog.open}
        onClose={() => setTemplateDialog({ open: false, mode: 'create', template: null })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {templateDialog.mode === 'create' ? 'Create Custom Template' : 'Edit Template'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              Custom templates help you quickly create multiple assets with consistent structure.
              Define the fields you need and save for reuse.
            </Alert>
            
            <TextField
              fullWidth
              label="Template Name"
              margin="normal"
              placeholder="e.g., Product Catalog, Employee Record"
            />
            
            <TextField
              fullWidth
              label="Description"
              multiline
              rows={2}
              margin="normal"
              placeholder="Describe what this template is used for"
            />
            
            <TextField
              fullWidth
              multiline
              rows={15}
              label="Template JSON Structure"
              margin="normal"
              placeholder={JSON.stringify({
                assetId: "",
                criticalMetadata: {
                  name: "",
                  description: "",
                  // Add your fields here
                },
                nonCriticalMetadata: {
                  // Add optional fields here
                }
              }, null, 2)}
              helperText="Define the structure for assets created from this template"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTemplateDialog({ open: false, mode: 'create', template: null })}>
            Cancel
          </Button>
          <Button variant="contained" startIcon={<Save />}>
            Save Template
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TemplateSelector;