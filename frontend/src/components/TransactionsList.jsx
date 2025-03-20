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
import { formatDate, formatWalletAddress, formatTransactionHash } from '../utils/formatters';

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

  // Function to get appropriate color for action
  const getActionColor = (action) => {
    switch (action) {
      case 'CREATE':
        return 'success';
      case 'UPDATE':
        return 'info';
      case 'DELETE':
        return 'error';
      case 'TRANSFER':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Date</TableCell>
            <TableCell>Asset ID</TableCell>
            <TableCell>Action</TableCell>
            <TableCell>Wallet</TableCell>
            <TableCell>TX Hash</TableCell>
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
                  label={tx.action}
                  color={getActionColor(tx.action)}
                  size="small"
                />
              </TableCell>
              <TableCell>{formatWalletAddress(tx.walletAddress)}</TableCell>
              <TableCell>
                {tx.blockchainTxHash ? (
                  <Typography variant="body2">
                    {formatTransactionHash(tx.blockchainTxHash)}
                  </Typography>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    N/A
                  </Typography>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export default TransactionsList;