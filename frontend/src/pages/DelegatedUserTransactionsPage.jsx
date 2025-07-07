import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  CircularProgress,
  Alert
} from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import delegationService from '../services/delegationService';
import TransactionsList from '../components/TransactionsList';

function DelegatedUserTransactionsPage() {
  const { ownerAddress } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch delegated user transactions
  useEffect(() => {
    const fetchTransactions = async () => {
      if (!ownerAddress || !isAuthenticated) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const response = await delegationService.getDelegatedUserTransactions(ownerAddress);
        setTransactions(response.transactions || []);
      } catch (error) {
        console.error('Error fetching delegated user transactions:', error);
        setError('Failed to load transaction history. You may not have permission to view this user\'s transactions.');
      } finally {
        setLoading(false);
      }
    };

    fetchTransactions();
  }, [ownerAddress, isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Alert severity="warning">
            Please connect your wallet to view transaction history.
          </Alert>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/delegation')}
            variant="outlined"
          >
            Back to Delegation
          </Button>
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              Transaction History
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Viewing transactions for: {ownerAddress ? `${ownerAddress.slice(0, 6)}...${ownerAddress.slice(-4)}` : ''}
            </Typography>
          </Box>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Paper sx={{ p: 3 }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Transaction History ({transactions.length} transactions)
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  This shows the transaction history for assets owned by the user who delegated management rights to you.
                </Typography>
              </Box>
              
              <TransactionsList 
                transactions={transactions} 
                isLoading={loading} 
              />
            </>
          )}
        </Paper>
      </Box>
    </Container>
  );
}

export default DelegatedUserTransactionsPage;