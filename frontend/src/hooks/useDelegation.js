import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ethers } from 'ethers';
import { toast } from 'react-hot-toast';
import delegationService from '../services/delegationService';
import { useAuth } from '../contexts/AuthContext';

/**
 * Hook to manage delegation functionality
 * @param {Object} options - Configuration options
 * @param {boolean} options.refetchOnMount - Whether to refetch on component mount
 * @param {number} options.staleTime - How long cached data is considered fresh (ms)
 * @returns {Object} Delegation state and control functions
 */
export const useDelegation = (options = {}) => {
  const { 
    refetchOnMount = true,
    staleTime = 1000 * 60 * 5 // 5 minutes
  } = options;
  
  const { currentAccount, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [signer, setSigner] = useState(null);

  // Initialize signer when wallet is connected
  useEffect(() => {
    const initializeSigner = async () => {
      if (currentAccount && window.ethereum) {
        try {
          const provider = new ethers.BrowserProvider(window.ethereum);
          const walletSigner = await provider.getSigner();
          setSigner(walletSigner);
        } catch (error) {
          console.error('Error initializing signer:', error);
          setSigner(null);
        }
      } else {
        setSigner(null);
      }
    };

    initializeSigner();
  }, [currentAccount]);

  // Get server info (public query)
  const { 
    data: serverInfo, 
    isLoading: serverInfoLoading,
    error: serverInfoError 
  } = useQuery({
    queryKey: ['serverInfo'],
    queryFn: () => delegationService.getServerInfo(),
    staleTime: staleTime * 2, // Server info changes rarely
    retry: 3,
    refetchOnMount
  });

  // Check delegation status (requires authentication)
  const { 
    data: delegationStatus, 
    isLoading: statusLoading,
    error: statusError,
    refetch: refetchStatus 
  } = useQuery({
    queryKey: ['delegationStatus', currentAccount],
    queryFn: () => delegationService.checkDelegationStatus(),
    enabled: !!isAuthenticated && !!currentAccount,
    staleTime,
    retry: 2,
    refetchOnMount
  });

  // Mutation for setting delegation (delegate or revoke)
  const delegateMutation = useMutation({
    mutationFn: async ({ status }) => {
      if (!serverInfo?.server_wallet_address) {
        throw new Error('Server wallet address not available');
      }

      if (!signer) {
        throw new Error('Wallet signer not available. Please ensure MetaMask is connected.');
      }

      // Step 1: Prepare the unsigned transaction
      const txData = await delegationService.prepareDelegationTransaction(
        serverInfo.server_wallet_address,
        status
      );

      if (!txData.success) {
        throw new Error(txData.error || 'Failed to prepare delegation transaction');
      }

      // Step 2: Sign and send the transaction
      const tx = await signer.sendTransaction(txData.transaction);
      
      // Step 3: Wait for confirmation
      const receipt = await tx.wait();
      
      if (receipt.status === 0) {
        throw new Error('Transaction failed on blockchain');
      }

      return { receipt, status, txHash: receipt.hash };
    },
    onMutate: ({ status }) => {
      // Optimistically update UI
      const action = status ? 'delegating' : 'revoking';
      toast.loading(`${action.charAt(0).toUpperCase() + action.slice(1)} permission...`, {
        id: 'delegation-loading'
      });
    },
    onSuccess: ({ status, txHash }) => {
      // Invalidate and refetch delegation status
      queryClient.invalidateQueries(['delegationStatus']);
      
      const action = status ? 'granted' : 'revoked';
      toast.success(
        `Delegation ${action} successfully! Transaction: ${delegationService.formatAddress(txHash)}`, 
        { id: 'delegation-loading', duration: 5000 }
      );
    },
    onError: (error) => {
      console.error('Delegation error:', error);
      
      // Handle specific error types
      let errorMessage = 'Delegation failed';
      
      if (error.code === 4001) {
        errorMessage = 'Transaction rejected by user';
      } else if (error.code === -32603) {
        errorMessage = 'Network error - please check your connection';
      } else if (error.message?.includes('insufficient funds')) {
        errorMessage = 'Insufficient funds for gas fee';
      } else if (error.message?.includes('nonce')) {
        errorMessage = 'Transaction nonce error - please try again';
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      toast.error(errorMessage, { id: 'delegation-loading' });
    }
  });

  // Helper functions
  const delegate = useCallback(() => {
    if (!isAuthenticated) {
      toast.error('Please connect your wallet first');
      return;
    }
    return delegateMutation.mutate({ status: true });
  }, [delegateMutation, isAuthenticated]);

  const revoke = useCallback(() => {
    if (!isAuthenticated) {
      toast.error('Please connect your wallet first');
      return;
    }
    return delegateMutation.mutate({ status: false });
  }, [delegateMutation, isAuthenticated]);

  const refreshStatus = useCallback(async () => {
    if (isAuthenticated) {
      await refetchStatus();
    }
  }, [refetchStatus, isAuthenticated]);

  // Check if delegation is required for API keys
  const isDelegationRequiredForApiKeys = useCallback(() => {
    return serverInfo?.features?.delegation_required_for_api_keys === true;
  }, [serverInfo]);

  // Get formatted delegation info for display
  const getDelegationInfo = useCallback(() => {
    if (!serverInfo || !delegationStatus) return null;

    return {
      serverWallet: serverInfo.server_wallet_address,
      serverWalletFormatted: delegationService.formatAddress(serverInfo.server_wallet_address),
      userWallet: currentAccount,
      userWalletFormatted: delegationService.formatAddress(currentAccount),
      isDelegated: delegationStatus.is_delegated,
      canUpdate: delegationStatus.can_update_assets,
      canDelete: delegationStatus.can_delete_assets,
      network: delegationService.getNetworkInfo(serverInfo.network?.chain_id)
    };
  }, [serverInfo, delegationStatus, currentAccount]);

  return {
    // Server info
    serverInfo,
    serverInfoLoading,
    serverInfoError,
    
    // Delegation status
    delegationStatus,
    isDelegated: delegationStatus?.is_delegated || false,
    canUpdateAssets: delegationStatus?.can_update_assets || false,
    canDeleteAssets: delegationStatus?.can_delete_assets || false,
    
    // Loading states
    isLoading: serverInfoLoading || statusLoading,
    statusLoading,
    isDelegating: delegateMutation.isPending,
    
    // Error states
    error: serverInfoError || statusError,
    delegationError: delegateMutation.error,
    
    // Actions
    delegate,
    revoke,
    refreshStatus,
    
    // Helper functions
    isDelegationRequiredForApiKeys,
    getDelegationInfo,
    
    // Wallet state
    hasWallet: !!currentAccount && !!signer,
    walletAddress: currentAccount
  };
};

export default useDelegation;