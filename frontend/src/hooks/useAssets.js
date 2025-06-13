import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assetService } from '../services/assetService';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';

export const useAssets = () => {
  const { currentAccount } = useAuth();
  const queryClient = useQueryClient();

  // Query for user's assets
  const userAssetsQuery = useQuery({
    queryKey: ['assets', currentAccount],
    queryFn: () => currentAccount ? assetService.getUserAssets(currentAccount) : { assets: [] },
    enabled: !!currentAccount,
    staleTime: 30000, // 30 seconds
    retry: 3,
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
    deleteAsset: deleteAssetMutation.mutate,
    isUploading: uploadMetadataMutation.isPending || uploadJsonMutation.isPending,
    isDeleting: deleteAssetMutation.isPending
  };
};