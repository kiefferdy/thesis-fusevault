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
      queryClient.invalidateQueries(['assets', currentAccount]);
      toast.success('Asset metadata uploaded successfully!');
      
      // Call onSuccess callback if provided
      if (context?.onSuccess) {
        context.onSuccess(data);
      }
    },
    onError: (error) => {
      toast.error(`Error uploading metadata: ${error.message}`);
    }
  });

  // Mutation for uploading JSON files
  const uploadJsonMutation = useMutation({
    mutationFn: ({ files }) => assetService.uploadJsonFiles(files, currentAccount),
    onSuccess: (data, variables, context) => {
      queryClient.invalidateQueries(['assets', currentAccount]);
      queryClient.refetchQueries(['assets', currentAccount]);
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