import { useQuery } from '@tanstack/react-query';
import { transactionService } from '../services/transactionService';
import { useAuth } from '../contexts/AuthContext';

export const useTransactions = () => {
  const { currentAccount, isAuthenticated } = useAuth();

  // Query for transaction summary
  const summaryQuery = useQuery({
    queryKey: ['transactions', 'summary', currentAccount],
    queryFn: () => currentAccount ? transactionService.getTransactionSummary(currentAccount) : null,
    enabled: !!currentAccount && isAuthenticated,
    staleTime: 300000 // 5 minutes
  });

  // Query for recent transactions
  const recentQuery = useQuery({
    queryKey: ['transactions', 'recent', currentAccount],
    queryFn: () => currentAccount ? transactionService.getRecentTransactions(currentAccount) : null,
    enabled: !!currentAccount && isAuthenticated,
    staleTime: 60000 // 1 minute
  });

  // Function to get asset history (called on demand)
  const getAssetHistory = async (assetId, version = null) => {
    if (!isAuthenticated) return null;
    return await transactionService.getAssetHistory(assetId, version);
  };

  return {
    summary: summaryQuery.data?.summary || {},
    recentTransactions: recentQuery.data?.transactions || [],
    isSummaryLoading: summaryQuery.isLoading,
    isRecentLoading: recentQuery.isLoading,
    isSummaryError: summaryQuery.isError,
    isRecentError: recentQuery.isError,
    summaryError: summaryQuery.error,
    recentError: recentQuery.error,
    getAssetHistory
  };
};