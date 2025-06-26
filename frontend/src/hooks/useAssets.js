import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assetService } from '../services/assetService';
import { transactionFlow } from '../services/blockchainService';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';

export const useAssets = () => {
  const { currentAccount, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();

  // Query for user's assets
  const userAssetsQuery = useQuery({
    queryKey: ['assets', currentAccount],
    queryFn: () => currentAccount ? assetService.getUserAssets(currentAccount) : { assets: [] },
    enabled: !!currentAccount && isAuthenticated,
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: true
  });

  // Mutation for uploading metadata
  const uploadMetadataMutation = useMutation({
    mutationFn: (data) => assetService.uploadMetadata(data),
    onSuccess: (data, variables, context) => {
      // Invalidate and refetch to update the asset list
      queryClient.invalidateQueries(['assets', currentAccount]);
      queryClient.refetchQueries(['assets', currentAccount]);
      
      // Invalidate transaction data to reflect the new transaction
      queryClient.invalidateQueries(['transactions', 'all', currentAccount]);
      queryClient.invalidateQueries(['transactions', 'recent', currentAccount]);
      queryClient.invalidateQueries(['transactions', 'summary', currentAccount]);
      
      // Determine if this is an update based on the presence of existing data
      // We'll check if the assetId already existed in our assets list
      const existingAssets = queryClient.getQueryData(['assets', currentAccount]);
      const isUpdate = existingAssets?.assets?.some(asset => asset.assetId === variables.assetId);
      
      toast.success(isUpdate ? 'Asset updated successfully!' : 'Asset created successfully!');
      
      // Call onSuccess callback if provided
      if (context?.onSuccess) {
        context.onSuccess(data);
      }
    },
    onError: (error, variables, context) => {
      // Determine if this is an update based on the presence of existing data
      const existingAssets = queryClient.getQueryData(['assets', currentAccount]);
      const isUpdate = existingAssets?.assets?.some(asset => asset.assetId === variables.assetId);
      
      toast.error(`Error ${isUpdate ? 'updating' : 'creating'} asset: ${error.message}`);
      
      // Call onError callback if provided
      if (context?.onError) {
        context.onError(error);
      }
    }
  });
  
  // Mutation for uploading JSON files
  const uploadJsonMutation = useMutation({
    mutationFn: ({ files }) => assetService.uploadJsonFiles(files, currentAccount),
    onSuccess: (data, variables, context) => {
      // Invalidate and refetch asset data
      queryClient.invalidateQueries(['assets', currentAccount]);
      queryClient.refetchQueries(['assets', currentAccount]);
      
      // Invalidate transaction data to reflect the new transactions
      queryClient.invalidateQueries(['transactions', 'all', currentAccount]);
      queryClient.invalidateQueries(['transactions', 'recent', currentAccount]);
      queryClient.invalidateQueries(['transactions', 'summary', currentAccount]);
      
      toast.success('JSON files uploaded successfully!');
      
      // Call onSuccess callback if provided
      if (context?.onSuccess) {
        context.onSuccess(data);
      }
    },
    onError: (error) => {
      toast.error(`Error uploading JSON files: ${error.message}`);
    }
  });

  // Mutation for batch uploads with single MetaMask signature
  const uploadBatchMutation = useMutation({
    mutationFn: ({ assets, onProgress }) => 
      transactionFlow.batchUploadWithSigning({ assets, walletAddress: currentAccount }, onProgress),
    onSuccess: (data, variables, context) => {
      // Invalidate and refetch asset data
      queryClient.invalidateQueries(['assets', currentAccount]);
      queryClient.refetchQueries(['assets', currentAccount]);
      
      // Invalidate transaction data to reflect the new transactions
      queryClient.invalidateQueries(['transactions', 'all', currentAccount]);
      queryClient.invalidateQueries(['transactions', 'recent', currentAccount]);
      queryClient.invalidateQueries(['transactions', 'summary', currentAccount]);
      
      // Show detailed success message with counts
      const successCount = data.successfulCount || data.results?.filter(r => r.status === 'success').length || 0;
      const totalCount = data.assetCount || data.results?.length || 0;
      
      if (successCount === totalCount) {
        toast.success(`Batch upload completed! ${successCount} assets created successfully.`);
      } else {
        toast.success(`Batch upload completed! ${successCount}/${totalCount} assets created successfully.`);
        if (totalCount - successCount > 0) {
          toast.error(`${totalCount - successCount} assets failed to upload. Check the results for details.`);
        }
      }
      
      // Call onSuccess callback if provided
      if (context?.onSuccess) {
        context.onSuccess(data);
      }
    },
    onError: (error, variables, context) => {
      toast.error(`Error in batch upload: ${error.message}`);
      
      // Call onError callback if provided
      if (context?.onError) {
        context.onError(error);
      }
    }
  });

  // Mutation for deleting an asset
  const deleteAssetMutation = useMutation({
    mutationFn: ({ assetId, reason }) => 
      assetService.deleteAsset(assetId, currentAccount, reason),
    onSuccess: () => {
      queryClient.invalidateQueries(['assets', currentAccount]);
      toast.success('Asset deleted successfully!');
    },
    onError: (error) => {
      toast.error(`Error deleting asset: ${error.message}`);
    }
  });

  return {
    assets: userAssetsQuery.data?.assets || [],
    isLoading: userAssetsQuery.isLoading,
    isError: userAssetsQuery.isError,
    error: userAssetsQuery.error,
    uploadMetadata: uploadMetadataMutation.mutate,
    uploadJson: uploadJsonMutation.mutate,
    uploadBatch: uploadBatchMutation.mutate,
    deleteAsset: deleteAssetMutation.mutate,
    isUploading: uploadMetadataMutation.isPending || uploadJsonMutation.isPending || uploadBatchMutation.isPending,
    isBatchUploading: uploadBatchMutation.isPending,
    isDeleting: deleteAssetMutation.isPending,
    batchUploadError: uploadBatchMutation.error
  };
};