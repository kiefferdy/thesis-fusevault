import { useQuery } from '@tanstack/react-query';
import { transactionService } from '../services/transactionService';
import { useAuth } from '../contexts/AuthContext';

export const useTransactions = () => {
  const { currentAccount, isAuthenticated } = useAuth();

  // Query for transaction summary
  const summaryQuery = useQuery({
    queryKey: ['transactions', 'summary', currentAccount],
    queryFn: () => currentAccount ? transactionService.getTransactionSummary(currentAccount) : { summary: {} },
    enabled: !!currentAccount && isAuthenticated,
    staleTime: 60000, // 1 minute
    retry: 3
  });

  // Query for recent transactions
  const recentQuery = useQuery({
    queryKey: ['transactions', 'recent', currentAccount],
    queryFn: () => currentAccount ? transactionService.getRecentTransactions(currentAccount) : { transactions: [] },
    enabled: !!currentAccount && isAuthenticated,
    staleTime: 30000, // 30 seconds
    retry: 3
  });
  
  // Query for all transactions (normally not executed automatically)
  const allTransactionsQuery = useQuery({
    queryKey: ['transactions', 'all', currentAccount],
    queryFn: () => currentAccount ? transactionService.getAllTransactions(currentAccount) : { transactions: [] },
    enabled: false, // Not automatically executed
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
    getAssetHistory,
    // Add methods for all transactions
    getAllTransactions: () => allTransactionsQuery.refetch(),
    allTransactions: allTransactionsQuery.data?.transactions || [],
    isAllTransactionsLoading: allTransactionsQuery.isLoading,
    isAllTransactionsError: allTransactionsQuery.isError
  };
};