import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userService } from '../services/userService';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';

export const useUser = () => {
  const { currentAccount, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();

  // Query for user profile
  const userQuery = useQuery({
    queryKey: ['user', currentAccount],
    queryFn: () => currentAccount ? userService.getUser(currentAccount) : null,
    enabled: !!currentAccount && isAuthenticated,
    staleTime: 300000, // 5 minutes
    select: (data) => {
      // Make sure we return the actual user object correctly
      return data?.user || data;
    }
  });

  // Mutation for registering a user
  const registerMutation = useMutation({
    mutationFn: (userData) => userService.registerUser({
      ...userData,
      wallet_address: currentAccount
    }),
    onSuccess: () => {
      queryClient.invalidateQueries(['user', currentAccount]);
      toast.success('Registration successful!');
    },
    onError: (error) => {
      toast.error(`Registration failed: ${error.message}`);
    }
  });

  // Mutation for updating a user
  const updateMutation = useMutation({
    mutationFn: (updateData) => userService.updateUser(currentAccount, updateData),
    onSuccess: () => {
      // Force refetch to update the UI immediately
      queryClient.invalidateQueries(['user', currentAccount]);
      queryClient.refetchQueries(['user', currentAccount]);
      toast.success('Profile updated successfully!');
    },
    onError: (error) => {
      toast.error(`Update failed: ${error.message}`);
    }
  });

  return {
    user: userQuery.data,
    isLoading: userQuery.isLoading,
    isError: userQuery.isError,
    error: userQuery.error,
    register: registerMutation.mutate,
    update: updateMutation.mutate,
    isRegistering: registerMutation.isPending,
    isUpdating: updateMutation.isPending
  };
};