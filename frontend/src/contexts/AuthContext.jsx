import { createContext, useContext, useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { authService } from '../services/authService';
import axios from 'axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [currentAccount, setCurrentAccount] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [backendAvailable, setBackendAvailable] = useState(true);
  const navigate = useNavigate();

  // Check if backend is available
  const checkBackendAvailability = async () => {
    try {
      console.log("Checking backend availability...");
      
      // Make a simple request to the backend without showing errors
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      console.log("Using API URL:", API_URL);
      
      // We use a direct axios call to avoid our error interceptor
      // Important: withCredentials is set to false to avoid sending cookies
      // This ensures the request is treated as completely public
      const response = await axios.get(`${API_URL}/auth/nonce/0x0000000000000000000000000000000000000000`, { 
        timeout: 5000, // Increased timeout for reliability
        withCredentials: false // Do NOT include credentials for this check
      });
      
      console.log("Backend response received:", response.status);
      
      // If we reach here, the backend is available
      setBackendAvailable(true);
      sessionStorage.removeItem('hasShownBackendError');
      return true;
    } catch (error) {
      console.log("Error during backend availability check:", error.name);
      
      if (error.response) {
        // If we get any response, even an error, the backend is available
        console.log("Received error response from backend:", error.response.status);
        setBackendAvailable(true);
        sessionStorage.removeItem('hasShownBackendError');
        return true;
      } else if (error.request) {
        // Request was made but no response received
        console.log("No response received from backend");
        setBackendAvailable(false);
        const hasShownError = sessionStorage.getItem('hasShownBackendError');
        if (!hasShownError) {
          toast.error('Backend server is not available. Running in demo mode.');
          sessionStorage.setItem('hasShownBackendError', 'true');
        }
        return false;
      } else {
        // Something happened in setting up the request
        console.log("Request setup error:", error.message);
        setBackendAvailable(false);
        const hasShownError = sessionStorage.getItem('hasShownBackendError');
        if (!hasShownError) {
          toast.error('Backend server is not available. Running in demo mode.');
          sessionStorage.setItem('hasShownBackendError', 'true');
        }
        return false;
      }
    }
  };

  // Check if MetaMask is installed
  const checkIfWalletIsConnected = async () => {
    try {
      // First check if backend is available
      const isBackendAvailable = await checkBackendAvailability();
      console.log("Backend availability check result:", isBackendAvailable);
      
      const { ethereum } = window;
      
      if (!ethereum) {
        toast.error('Please install MetaMask to use this app');
        setIsLoading(false);
        return;
      }

      // Check if we're authorized to access the user's wallet
      const accounts = await ethereum.request({ method: 'eth_accounts' });
      
      if (accounts.length !== 0) {
        const account = accounts[0];
        setCurrentAccount(account);
        
        // Check if user has active session (only if backend is available)
        if (isBackendAvailable) {
          console.log("Checking for active session...");
          try {
            const sessionData = await authService.validateSession();
            if (sessionData) {
              console.log("Valid session found:", sessionData);
              setIsAuthenticated(true);
              // Store auth state in localStorage for persistence
              localStorage.setItem('isAuthenticated', 'true');
            }
          } catch (error) {
            // 401 errors are expected when not logged in
            if (error.response && error.response.status === 401) {
              console.log('No active session found');
            } else {
              console.error('Error validating session:', error);
            }
          }
        } else {
          console.log("Skipping session validation since backend is unavailable");
        }
      }
    } catch (error) {
      console.error("Error during wallet connection check:", error);
      // Don't show errors during initial load
    }
    setIsLoading(false);
  };

  // Connect wallet
  const connectWallet = async () => {
    try {
      const { ethereum } = window;
      
      if (!ethereum) {
        toast.error('Please install MetaMask to use this app');
        return;
      }
      
      setIsLoading(true);
      
      // Request account access
      const accounts = await ethereum.request({ method: 'eth_requestAccounts' });
      const account = accounts[0];
      
      setCurrentAccount(account);
      toast.success('Wallet connected successfully!');
      
      setIsLoading(false);
      return account;
    } catch (error) {
      console.error(error);
      setIsLoading(false);
      toast.error('Failed to connect wallet');
      return null;
    }
  };

  // Sign in with MetaMask
  const signIn = async () => {
    try {
      // Check backend availability before attempting to sign in
      const isAvailable = await checkBackendAvailability();
      
      const account = currentAccount || await connectWallet();
      
      if (!account) return false;
      
      setIsLoading(true);
      
      if (!isAvailable) {
        // Mock authentication for demo purposes when backend is not available
        setIsAuthenticated(true);
        localStorage.setItem('isAuthenticated', 'true');
        toast.success('Demo mode: Authentication successful!');
        toast.info('Note: This is demo mode. Connect to backend for full features.');
        navigate('/dashboard');
        setIsLoading(false);
        return true;
      }
      
      // Get nonce from backend
      try {
        const { nonce } = await authService.getNonce(account);
        
        // Create provider
        const { ethereum } = window;
        const provider = new ethers.BrowserProvider(ethereum);
        const signer = await provider.getSigner();
        
        // Create message to sign
        const message = `Sign this message to authenticate with FuseVault.\n\nNonce: ${nonce}`;
        
        // Sign the message
        const signature = await signer.signMessage(message);
        
        // Authenticate with backend
        const authResponse = await authService.authenticate(account, signature);
        
        if (authResponse.status === 'success') {
          setIsAuthenticated(true);
          localStorage.setItem('isAuthenticated', 'true');
          toast.success('Authentication successful!');
          navigate('/dashboard');
        } else {
          toast.error('Authentication failed: ' + authResponse.message);
        }
        
        setIsLoading(false);
        return authResponse.status === 'success';
      } catch (error) {
        console.error('Backend error during authentication:', error);
        if (!error.response) {
          // Connection error means backend went down during authentication
          setBackendAvailable(false);
          toast.warning('Backend server is not available. Switching to demo mode.');
          setIsAuthenticated(true);
          localStorage.setItem('isAuthenticated', 'true');
          navigate('/dashboard');
          setIsLoading(false);
          return true;
        } else {
          throw error;
        }
      }
    } catch (error) {
      console.error('Error during authentication:', error);
      setIsLoading(false);
      toast.error(error.message || 'Authentication failed');
      return false;
    }
  };

  // Sign out
  const signOut = async () => {
    try {
      setIsLoading(true);
      
      // Check if backend is available
      const isAvailable = await checkBackendAvailability();
      
      if (!isAvailable) {
        // Mock logout for demo purposes
        setIsAuthenticated(false);
        localStorage.removeItem('isAuthenticated');
        toast.success('Logged out successfully');
        navigate('/');
        setIsLoading(false);
        return;
      }
      
      // Call logout API
      try {
        const response = await authService.logout();
        
        if (response.status === 'success') {
          setIsAuthenticated(false);
          localStorage.removeItem('isAuthenticated');
          toast.success('Logged out successfully');
          navigate('/');
        } else {
          toast.error('Logout failed: ' + response.message);
        }
      } catch (error) {
        if (!error.response) {
          // Connection error means backend went down during logout
          setBackendAvailable(false);
          toast.warning('Backend server is not available. Performing local logout.');
          setIsAuthenticated(false);
          localStorage.removeItem('isAuthenticated');
          navigate('/');
        } else {
          throw error;
        }
      }
      
      setIsLoading(false);
    } catch (error) {
      console.error('Error during logout:', error);
      setIsLoading(false);
      toast.error('Logout failed');
    }
  };

  // Check wallet connection on initial load
  useEffect(() => {
    checkIfWalletIsConnected();
    
    // Check localStorage for persistent auth state
    const storedAuthState = localStorage.getItem('isAuthenticated') === 'true';
    if (storedAuthState) {
      setIsAuthenticated(true);
    }
    
    // Handle account changes
    if (window.ethereum) {
      window.ethereum.on('accountsChanged', (accounts) => {
        if (accounts.length === 0) {
          // User disconnected their wallet
          setCurrentAccount(null);
          setIsAuthenticated(false);
          localStorage.removeItem('isAuthenticated');
          toast.error('Wallet disconnected');
          navigate('/');
        } else {
          // User switched accounts
          setCurrentAccount(accounts[0]);
          setIsAuthenticated(false);
          localStorage.removeItem('isAuthenticated');
          toast.info('Account changed. Please sign in again.');
          navigate('/');
        }
      });
    }
    
    // Cleanup
    return () => {
      if (window.ethereum && window.ethereum.removeListener) {
        window.ethereum.removeListener('accountsChanged', () => {});
      }
    };
  }, [navigate]);

  return (
    <AuthContext.Provider
      value={{
        currentAccount,
        isAuthenticated,
        isLoading,
        backendAvailable,
        connectWallet,
        signIn,
        signOut
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);