import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userService } from '../services/userService';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';
import { validateUsername, normalizeUsername } from '../utils/usernameUtils';

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

  // Mutation for onboarding a user (authenticated users completing their profile)
  const onboardMutation = useMutation({
    mutationFn: (userData) => userService.onboardUser({
      ...userData,
      wallet_address: currentAccount
    }),
    onSuccess: () => {
      queryClient.invalidateQueries(['user', currentAccount]);
      toast.success('Profile setup completed successfully!');
    },
    onError: (error) => {
      toast.error(`Profile setup failed: ${error.message}`);
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

  // Username availability checking query
  const usernameAvailabilityQuery = useQuery({
    queryKey: ['username-availability'],
    queryFn: () => null, // This will be manually triggered
    enabled: false, // Don't auto-fetch
    staleTime: 30000, // Cache for 30 seconds
  });

  // Mutation for checking username availability
  const checkUsernameAvailability = useMutation({
    mutationFn: async (username) => {
      const normalizedUsername = normalizeUsername(username);
      
      // First validate client-side
      const validation = validateUsername(normalizedUsername);
      if (!validation.isValid) {
        throw new Error(validation.error);
      }

      // Then check server-side availability
      const result = await userService.checkUsernameAvailability(normalizedUsername);
      return { ...result, username: normalizedUsername };
    },
    onSuccess: (data) => {
      // Cache the result
      queryClient.setQueryData(['username-availability', data.username], data);
    },
    onError: (error) => {
      console.error('Username availability check failed:', error);
    }
  });

  // Mutation for updating username specifically
  const updateUsernameMutation = useMutation({
    mutationFn: async (newUsername) => {
      const normalizedUsername = normalizeUsername(newUsername);
      
      // Validate before sending
      const validation = validateUsername(normalizedUsername);
      if (!validation.isValid) {
        throw new Error(validation.error);
      }

      return userService.updateUsername(currentAccount, normalizedUsername);
    },
    onSuccess: () => {
      // Invalidate and refetch user data
      queryClient.invalidateQueries(['user', currentAccount]);
      queryClient.refetchQueries(['user', currentAccount]);
      toast.success('Username updated successfully!');
    },
    onError: (error) => {
      const errorMessage = error.response?.data?.message || error.message || 'Failed to update username';
      toast.error(`Username update failed: ${errorMessage}`);
    }
  });

  return {
    user: userQuery.data,
    isLoading: userQuery.isLoading,
    isError: userQuery.isError,
    error: userQuery.error,
    register: registerMutation.mutate,
    onboard: onboardMutation.mutate,
    update: updateMutation.mutate,
    isRegistering: registerMutation.isPending,
    isOnboarding: onboardMutation.isPending,
    isUpdating: updateMutation.isPending,
    
    // Username-specific functionality
    checkUsernameAvailability: checkUsernameAvailability.mutate,
    isCheckingUsername: checkUsernameAvailability.isPending,
    usernameCheckResult: checkUsernameAvailability.data,
    usernameCheckError: checkUsernameAvailability.error,
    
    updateUsername: updateUsernameMutation.mutate,
    isUpdatingUsername: updateUsernameMutation.isPending,
    
    // Helper function to get cached availability result
    getCachedUsernameAvailability: (username) => {
      const normalizedUsername = normalizeUsername(username);
      return queryClient.getQueryData(['username-availability', normalizedUsername]);
    }
  };
};