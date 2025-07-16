import React from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Tooltip,
  Avatar
} from '@mui/material';
import {
  History,
  Timeline
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { formatDate, formatWalletAddress } from '../utils/formatters';

function RecentActivityFeed({ transactions, isLoading, maxItems = 5 }) {
  const navigate = useNavigate();

  // Get action color for chips (same as HistoryPage)
  const getActionColor = (action) => {
    switch (action) {
      case 'CREATE': return 'success';
      case 'VERSION_CREATE': return 'info';
      case 'UPDATE': return 'info';
      case 'DELETE': return 'error';
      case 'RECREATE_DELETED': return 'success';
      case 'INTEGRITY_RECOVERY': return 'warning';
      case 'TRANSFER_INITIATED': return 'secondary';
      case 'TRANSFER_COMPLETED': return 'success';
      case 'TRANSFER_CANCELLED': return 'error';
      case 'DELETION_STATUS_RESTORED': return 'warning';
      default: return 'default';
    }
  };

  // Limit transactions to maxItems
  const displayTransactions = transactions?.slice(0, maxItems) || [];

  return (
    <Card sx={{ height: '100%' }}>
      <CardHeader
        title={
          <Typography variant="subtitle1" sx={{ fontSize: '0.9rem', fontWeight: 600 }}>
            Recent Activity
          </Typography>
        }
        action={
          transactions?.length > 0 && (
            <Button
              size="small"
              endIcon={<Timeline fontSize="small" />}
              onClick={() => navigate('/history')}
              sx={{ fontSize: '0.75rem', minWidth: 'auto', px: 1 }}
            >
              View All
            </Button>
          )
        }
        sx={{ pb: 0.5, pt: 1, px: 2 }}
      />
      
      <CardContent sx={{ pt: 0, pb: 0.5 }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={32} />
          </Box>
        ) : displayTransactions.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 3 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              No recent activity found.
            </Typography>
            <Button
              variant="outlined"
              size="small"
              onClick={() => navigate('/upload')}
            >
              Create Your First Asset
            </Button>
          </Box>
        ) : (
          <TableContainer sx={{ maxHeight: 150 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ py: 0.5, fontSize: '0.75rem', fontWeight: 600, border: 0 }}>Asset</TableCell>
                  <TableCell sx={{ py: 0.5, fontSize: '0.75rem', fontWeight: 600, border: 0 }}>Action</TableCell>
                  <TableCell sx={{ py: 0.5, fontSize: '0.75rem', fontWeight: 600, border: 0 }}>Owner</TableCell>
                  <TableCell sx={{ py: 0.5, fontSize: '0.75rem', fontWeight: 600, border: 0 }}>Date</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {displayTransactions.map((transaction, index) => (
                  <TableRow
                    key={transaction.id || transaction._id || index}
                    hover
                    sx={{ 
                      cursor: 'pointer',
                      '&:hover': { bgcolor: 'action.hover' }
                    }}
                    onClick={() => navigate(`/assets/${transaction.assetId}/history`)}
                  >
                    <TableCell sx={{ py: 0.5, border: 0 }}>
                      <Tooltip title={`View ${transaction.assetId} history`}>
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            fontFamily: 'monospace',
                            fontSize: '0.75rem',
                            color: 'primary.main'
                          }}
                        >
                          {transaction.assetId?.slice(0, 12)}...
                        </Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell sx={{ py: 0.5, border: 0 }}>
                      <Chip
                        label={transaction.action}
                        color={getActionColor(transaction.action)}
                        size="small"
                        variant="outlined"
                        sx={{ 
                          height: 20,
                          fontSize: '0.65rem',
                          '& .MuiChip-label': { px: 0.75 }
                        }}
                      />
                    </TableCell>
                    <TableCell sx={{ py: 0.5, border: 0 }}>
                      <Tooltip title={transaction.walletAddress}>
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            fontFamily: 'monospace',
                            fontSize: '0.75rem'
                          }}
                        >
                          {formatWalletAddress(transaction.walletAddress)}
                        </Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell sx={{ py: 0.5, border: 0 }}>
                      <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                        {formatDate(transaction.timestamp)}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CardContent>
    </Card>
  );
}

export default RecentActivityFeed;