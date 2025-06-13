import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Container,
    Typography,
    Box,
    Paper,
    Button,
    CircularProgress,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    Alert,
    Card,
    CardContent,
    Grid,
    Divider,
    IconButton,
    Tooltip,
    TextField,
    InputAdornment,
    MenuItem,
    FormControl,
    InputLabel,
    Select
} from '@mui/material';
import {
    ArrowBack,
    History,
    Refresh,
    Download,
    Search,
    FilterList,
    Visibility,
    Edit
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { transactionService } from '../services/transactionService';
import { assetService } from '../services/assetService';
import { formatDate, formatWalletAddress, formatTransactionHash } from '../utils/formatters';

function AssetHistoryPage() {
    const { assetId } = useParams();
    const navigate = useNavigate();

    // State management
    const [history, setHistory] = useState([]);
    const [asset, setAsset] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [actionFilter, setActionFilter] = useState('all');

    // Fetch asset details and history
    useEffect(() => {
        const fetchData = async () => {
            if (!assetId) return;

            setLoading(true);
            try {
                // Fetch asset details and history in parallel
                const [assetData, historyData] = await Promise.all([
                    assetService.retrieveMetadata(assetId).catch(() => null), // Don't fail if asset fetch fails
                    transactionService.getAssetHistory(assetId)
                ]);

                setAsset(assetData);
                setHistory(historyData.transactions || []);
                setError(null);
            } catch (err) {
                console.error('Error fetching asset history:', err);
                setError('Failed to load asset history. Please try again later.');
                toast.error('Error loading asset history');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [assetId]);

    // Refresh history
    const handleRefresh = async () => {
        setRefreshing(true);
        try {
            const historyData = await transactionService.getAssetHistory(assetId);
            setHistory(historyData.transactions || []);
            toast.success('History refreshed');
        } catch (err) {
            console.error('Error refreshing history:', err);
            toast.error('Failed to refresh history');
        } finally {
            setRefreshing(false);
        }
    };

    // Filter transactions based on search and action filter
    const filteredHistory = history.filter(transaction => {
        // Action filter
        if (actionFilter !== 'all' && transaction.action !== actionFilter) {
            return false;
        }

        // Search filter
        if (searchTerm) {
            const searchLower = searchTerm.toLowerCase();
            return (
                transaction.action?.toLowerCase().includes(searchLower) ||
                transaction.walletAddress?.toLowerCase().includes(searchLower) ||
                transaction.blockchainTxHash?.toLowerCase().includes(searchLower) ||
                transaction.metadata?.reason?.toLowerCase().includes(searchLower)
            );
        }

        return true;
    });

    // Get unique actions for filter dropdown
    const availableActions = [...new Set(history.map(tx => tx.action).filter(Boolean))].sort();

    // Get action color for chips
    const getActionColor = (action) => {
        switch (action) {
            case 'CREATE': return 'success';
            case 'VERSION_CREATE': return 'info';
            case 'UPDATE': return 'warning';
            case 'DELETE': return 'error';
            case 'TRANSFER': return 'secondary';
            case 'VERIFY': return 'primary';
            case 'INTEGRITY': return 'default';
            case 'RECREATE': return 'info';
            case 'RESTORE': return 'success';
            default: return 'default';
        }
    };

    // Handle export (placeholder for future implementation)
    const handleExport = () => {
        toast.info('Export functionality coming soon!');
    };

    // Loading state
    if (loading) {
        return (
            <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
                    <Box sx={{ textAlign: 'center' }}>
                        <CircularProgress size={60} />
                        <Typography variant="h6" sx={{ mt: 2 }}>
                            Loading asset history...
                        </Typography>
                    </Box>
                </Box>
            </Container>
        );
    }

    // Error state
    if (error) {
        return (
            <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                </Alert>
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                        variant="outlined"
                        startIcon={<ArrowBack />}
                        onClick={() => navigate('/dashboard')}
                    >
                        Back to Dashboard
                    </Button>
                    <Button
                        variant="contained"
                        startIcon={<Refresh />}
                        onClick={() => window.location.reload()}
                    >
                        Try Again
                    </Button>
                </Box>
            </Container>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            {/* Header */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Button
                    variant="outlined"
                    startIcon={<ArrowBack />}
                    onClick={() => navigate('/dashboard')}
                    sx={{ mr: 2 }}
                >
                    Back
                </Button>
                <History sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h4" sx={{ flexGrow: 1 }}>
                    Asset History
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    <Tooltip title="Refresh History">
                        <IconButton
                            onClick={handleRefresh}
                            disabled={refreshing}
                            color="primary"
                        >
                            <Refresh />
                        </IconButton>
                    </Tooltip>
                    <Tooltip title="Export History">
                        <IconButton
                            onClick={handleExport}
                            color="primary"
                        >
                            <Download />
                        </IconButton>
                    </Tooltip>
                </Box>
            </Box>

            {/* Asset Info Card */}
            {asset && (
                <Card sx={{ mb: 3 }}>
                    <CardContent>
                        <Grid container spacing={2} alignItems="center">
                            <Grid item xs={12} md={8}>
                                <Typography variant="h6" gutterBottom>
                                    {asset.criticalMetadata?.name || 'Untitled Asset'}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" gutterBottom>
                                    Asset ID: {assetId}
                                </Typography>
                                {asset.criticalMetadata?.description && (
                                    <Typography variant="body2" color="text.secondary">
                                        {asset.criticalMetadata.description}
                                    </Typography>
                                )}
                            </Grid>
                            <Grid item xs={12} md={4}>
                                <Box sx={{ display: 'flex', gap: 1, justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
                                    <Button
                                        variant="outlined"
                                        size="small"
                                        startIcon={<Visibility />}
                                        onClick={() => navigate(`/assets/${assetId}`)}
                                    >
                                        View Asset
                                    </Button>
                                    <Button
                                        variant="outlined"
                                        size="small"
                                        startIcon={<Edit />}
                                        onClick={() => navigate(`/assets/${assetId}/edit`)}
                                    >
                                        Edit Asset
                                    </Button>
                                </Box>
                            </Grid>
                        </Grid>
                    </CardContent>
                </Card>
            )}

            {/* Summary Stats */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={4}>
                    <Card>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <Typography variant="h4" color="primary">
                                {history.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Total Transactions
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <Typography variant="h4" color="secondary">
                                {availableActions.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Different Actions
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <Typography variant="h4" color="info.main">
                                {history.filter(tx => tx.action === 'CREATE' || tx.action === 'VERSION_CREATE').length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Versions Created
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Filters */}
            <Paper sx={{ p: 2, mb: 3 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} sm={6} md={4}>
                        <TextField
                            fullWidth
                            placeholder="Search transactions..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            InputProps={{
                                startAdornment: (
                                    <InputAdornment position="start">
                                        <Search />
                                    </InputAdornment>
                                ),
                            }}
                            size="small"
                        />
                    </Grid>
                    <Grid item xs={12} sm={6} md={4}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Filter by Action</InputLabel>
                            <Select
                                value={actionFilter}
                                label="Filter by Action"
                                onChange={(e) => setActionFilter(e.target.value)}
                                startAdornment={
                                    <InputAdornment position="start">
                                        <FilterList />
                                    </InputAdornment>
                                }
                            >
                                <MenuItem value="all">All Actions</MenuItem>
                                {availableActions.map(action => (
                                    <MenuItem key={action} value={action}>
                                        {action}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item xs={12} md={4}>
                        <Typography variant="body2" color="text.secondary">
                            Showing {filteredHistory.length} of {history.length} transactions
                        </Typography>
                    </Grid>
                </Grid>
            </Paper>

            {/* History Table */}
            <Paper>
                <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Date & Time</TableCell>
                                <TableCell>Action</TableCell>
                                <TableCell>Version</TableCell>
                                <TableCell>Wallet Address</TableCell>
                                <TableCell>Transaction Hash</TableCell>
                                <TableCell>Details</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {filteredHistory.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                                        <Typography variant="body2" color="text.secondary">
                                            {history.length === 0
                                                ? 'No transaction history found for this asset.'
                                                : 'No transactions match your current filters.'
                                            }
                                        </Typography>
                                        {history.length > 0 && filteredHistory.length === 0 && (
                                            <Button
                                                variant="text"
                                                onClick={() => {
                                                    setSearchTerm('');
                                                    setActionFilter('all');
                                                }}
                                                sx={{ mt: 1 }}
                                            >
                                                Clear Filters
                                            </Button>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredHistory
                                    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)) // Sort by newest first
                                    .map((transaction, index) => (
                                        <TableRow
                                            key={transaction.id || transaction._id || index}
                                            hover
                                            sx={{ '&:nth-of-type(odd)': { bgcolor: 'action.hover' } }}
                                        >
                                            <TableCell>
                                                <Typography variant="body2">
                                                    {formatDate(transaction.timestamp)}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Chip
                                                    label={transaction.action}
                                                    color={getActionColor(transaction.action)}
                                                    size="small"
                                                    variant="outlined"
                                                />
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2" fontFamily="monospace">
                                                    {transaction.version || 'N/A'}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Tooltip title={transaction.walletAddress}>
                                                    <Typography variant="body2" fontFamily="monospace">
                                                        {formatWalletAddress(transaction.walletAddress)}
                                                    </Typography>
                                                </Tooltip>
                                            </TableCell>
                                            <TableCell>
                                                {transaction.blockchainTxHash ? (
                                                    <Tooltip title={transaction.blockchainTxHash}>
                                                        <Typography variant="body2" fontFamily="monospace" color="primary.main">
                                                            {formatTransactionHash(transaction.blockchainTxHash)}
                                                        </Typography>
                                                    </Tooltip>
                                                ) : (
                                                    <Chip label="Pending" size="small" color="warning" variant="outlined" />
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2">
                                                    {transaction.metadata?.reason ||
                                                        transaction.metadata?.description ||
                                                        'No additional details'}
                                                </Typography>
                                            </TableCell>
                                        </TableRow>
                                    ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>

                {/* Table Footer */}
                {filteredHistory.length > 0 && (
                    <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
                        <Typography variant="caption" color="text.secondary">
                            Last updated: {new Date().toLocaleString()}
                            {refreshing && ' • Refreshing...'}
                        </Typography>
                    </Box>
                )}
            </Paper>

            {/* Action Buttons */}
            <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'center' }}>
                <Button
                    variant="outlined"
                    onClick={() => navigate('/dashboard')}
                >
                    Back to Dashboard
                </Button>
                {asset && (
                    <>
                        <Button
                            variant="outlined"
                            startIcon={<Visibility />}
                            onClick={() => navigate(`/assets/${assetId}`)}
                        >
                            View Asset Details
                        </Button>
                        <Button
                            variant="contained"
                            startIcon={<Edit />}
                            onClick={() => navigate(`/assets/${assetId}/edit`)}
                        >
                            Edit Asset
                        </Button>
                    </>
                )}
            </Box>
        </Container>
    );
}

export default AssetHistoryPage;