import { 
  Typography, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper, 
  Chip,
  Box,
  CircularProgress
} from '@mui/material';
import { formatDate, formatWalletAddress } from '../utils/formatters';

function TransactionsList({ transactions, isLoading }) {
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!transactions || transactions.length === 0) {
    return (
      <Typography variant="body1" sx={{ p: 2 }}>
        No transactions found.
      </Typography>
    );
  }

  // Function to get appropriate color for action with expanded set of actions
  const getActionColor = (action) => {
    // Normalize action by removing any underscores and converting to uppercase
    const normalizedAction = action.toUpperCase().replace(/_/g, '');
    
    // Handle the main action types with darker colors for better contrast with white text
    if (normalizedAction.includes('CREATE')) return 'success';
    if (normalizedAction.includes('UPDATE')) return 'primary';
    if (normalizedAction.includes('DELETE')) return 'error';
    if (normalizedAction.includes('TRANSFER')) return 'secondary';
    if (normalizedAction.includes('INTEGRITY')) return 'secondary';
    if (normalizedAction.includes('RESTORE')) return 'primary';
    
    // Default for unknown actions
    return 'default';
  };
  

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Date</TableCell>
            <TableCell>Asset ID</TableCell>
            <TableCell>Action</TableCell>
            <TableCell>Owner</TableCell>
            <TableCell>Initiator</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {transactions.map((tx) => (
            <TableRow key={tx._id || tx.id}>
              <TableCell>{formatDate(tx.timestamp)}</TableCell>
              <TableCell>
                <Typography variant="body2" noWrap sx={{ maxWidth: 140 }}>
                  {tx.assetId}
                </Typography>
              </TableCell>
              <TableCell>
                <Chip 
                  label={tx.action.toUpperCase()}
                  color={getActionColor(tx.action)}
                  size="small"
                  sx={{ 
                    fontWeight: 'medium',
                    color: 'white',
                    '& .MuiChip-label': {
                      color: 'white'
                    }
                  }}
                />
              </TableCell>
              <TableCell>{formatWalletAddress(tx.walletAddress)}</TableCell>
              <TableCell>
                {tx.performedBy ? 
                  formatWalletAddress(tx.performedBy) : 
                  formatWalletAddress(tx.walletAddress)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export default TransactionsList;