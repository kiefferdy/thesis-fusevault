import { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  Card,
  CardContent,
  TextField,
  MenuItem,
  InputAdornment,
  CircularProgress,
  Divider
} from '@mui/material';
import { Search, FilterList } from '@mui/icons-material';
import { transactionService } from '../services/transactionService';
import { useAuth } from '../contexts/AuthContext';
import TransactionsList from '../components/TransactionsList';
import { useTransactions } from '../hooks/useTransactions';

function HistoryPage() {
  const { currentAccount } = useAuth();
  const { summary, isSummaryLoading } = useTransactions();
  
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch transaction data
  useEffect(() => {
    const fetchTransactions = async () => {
      if (!currentAccount) return;
      
      setLoading(true);
      try {
        // In a real implementation, you would have a paginated API for this
        const response = await transactionService.getRecentTransactions(currentAccount, 100);
        setTransactions(response.transactions || []);
      } catch (error) {
        console.error('Error fetching transactions:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTransactions();
  }, [currentAccount]);

  // Filter transactions based on action type and search term
  const filteredTransactions = transactions.filter(tx => {
    // Filter by action type
    if (filter !== 'all' && tx.action !== filter) {
      return false;
    }
    
    // Filter by search term (asset ID or transaction hash)
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      return (
        tx.assetId?.toLowerCase().includes(searchLower) ||
        tx.blockchainTxHash?.toLowerCase().includes(searchLower)
      );
    }
    
    return true;
  });

  // Handle filter change
  const handleFilterChange = (event) => {
    setFilter(event.target.value);
  };

  // Handle search term change
  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Transaction History
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Total Transactions
              </Typography>
              <Typography variant="h4">
                {isSummaryLoading ? <CircularProgress size={24} /> : (summary.total_transactions || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Creates
              </Typography>
              <Typography variant="h4">
                {isSummaryLoading ? <CircularProgress size={24} /> : (summary.actions?.CREATE || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Updates
              </Typography>
              <Typography variant="h4">
                {isSummaryLoading ? <CircularProgress size={24} /> : (summary.actions?.UPDATE || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Deletes
              </Typography>
              <Typography variant="h4">
                {isSummaryLoading ? <CircularProgress size={24} /> : (summary.actions?.DELETE || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ mb: 4 }}>
        {/* Filter Controls */}
        <Box sx={{ p: 2 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                placeholder="Search by asset ID or transaction hash"
                value={searchTerm}
                onChange={handleSearchChange}
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
            
            <Grid item xs={12} sm={4}>
              <TextField
                select
                fullWidth
                label="Filter by Action"
                value={filter}
                onChange={handleFilterChange}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <FilterList />
                    </InputAdornment>
                  ),
                }}
                size="small"
              >
                <MenuItem value="all">All Actions</MenuItem>
                <MenuItem value="CREATE">Create</MenuItem>
                <MenuItem value="UPDATE">Update</MenuItem>
                <MenuItem value="DELETE">Delete</MenuItem>
                <MenuItem value="TRANSFER">Transfer</MenuItem>
              </TextField>
            </Grid>
          </Grid>
        </Box>
        
        <Divider />
        
        {/* Transactions List */}
        <Box sx={{ p: 2 }}>
          <TransactionsList 
            transactions={filteredTransactions} 
            isLoading={loading} 
          />
          
          {!loading && filteredTransactions.length === 0 && (
            <Typography sx={{ p: 2, textAlign: 'center' }}>
              No transactions found matching your filters.
            </Typography>
          )}
        </Box>
      </Paper>
    </Container>
  );
}

export default HistoryPage;