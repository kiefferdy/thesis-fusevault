import { createContext, useContext, useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { authService } from '../services/authService';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [currentAccount, setCurrentAccount] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();


  // Check if MetaMask is installed and validate session
  const checkIfWalletIsConnected = async () => {
    try {
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
        
        // Check if localStorage indicates user was authenticated
        const storedAuthState = localStorage.getItem('isAuthenticated') === 'true';
        
        if (storedAuthState) {
          // Validate session with backend
          console.log("Checking for active session...");
          try {
            const sessionData = await authService.validateSession();
            if (sessionData && sessionData.walletAddress.toLowerCase() === account.toLowerCase()) {
              console.log("Valid session found:", sessionData);
              setIsAuthenticated(true);
            } else {
              console.log('Session validation failed or wallet mismatch');
              handleSessionExpired();
            }
          } catch (error) {
            // 401 errors indicate expired/invalid session
            if (error.response && error.response.status === 401) {
              console.log('Session expired or invalid');
              handleSessionExpired();
            } else {
              console.error('Error validating session:', error);
              handleSessionExpired();
            }
          }
        }
      } else {
        // No wallet connected, clear any stored auth state
        if (localStorage.getItem('isAuthenticated')) {
          localStorage.removeItem('isAuthenticated');
          setIsAuthenticated(false);
        }
      }
    } catch (error) {
      console.error("Error during wallet connection check:", error);
      handleSessionExpired();
    }
    setIsLoading(false);
  };

  // Handle expired or invalid sessions
  const handleSessionExpired = (showMessage = true) => {
    // Check if user was previously authenticated before clearing
    const wasAuthenticated = localStorage.getItem('isAuthenticated') === 'true';
    
    setIsAuthenticated(false);
    localStorage.removeItem('isAuthenticated');
    
    // Show message only if requested and user was previously authenticated
    if (showMessage && wasAuthenticated) {
      toast.error('Your session has expired. Please sign in again.');
      
      // Redirect to home if on protected routes
      const protectedRoutes = ['/dashboard', '/profile', '/upload', '/history', '/api-keys'];
      const currentPath = window.location.pathname;
      
      if (protectedRoutes.some(route => currentPath.startsWith(route))) {
        navigate('/');
      }
    }
  };

  // Validate current session immediately (for protected route navigation)
  const validateSessionNow = async () => {
    if (!isAuthenticated) {
      return false;
    }

    try {
      const sessionData = await authService.validateSession();
      if (sessionData && sessionData.walletAddress.toLowerCase() === currentAccount?.toLowerCase()) {
        return true;
      } else {
        handleSessionExpired(true);
        return false;
      }
    } catch (error) {
      if (error.response && error.response.status === 401) {
        handleSessionExpired(true);
      } else {
        console.error('Error validating session:', error);
        handleSessionExpired(true);
      }
      return false;
    }
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
      const account = currentAccount || await connectWallet();
      
      if (!account) return false;
      
      setIsLoading(true);
      
      
      // Get nonce from backend
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
      
      
      // Call logout API
      const response = await authService.logout();
      
      if (response.status === 'success') {
        setIsAuthenticated(false);
        localStorage.removeItem('isAuthenticated');
        toast.success('Logged out successfully');
        navigate('/');
      } else {
        toast.error('Logout failed: ' + response.message);
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
    
    // Listen for auth:unauthorized events from API client
    const handleUnauthorized = (event) => {
      console.log('Received unauthorized event from API client:', event.detail);
      handleSessionExpired(true);
    };

    // Listen for logout in other tabs via localStorage changes
    const handleStorageChange = (event) => {
      // Detect when isAuthenticated is removed in another tab
      if (event.key === 'isAuthenticated' && event.oldValue === 'true' && event.newValue === null) {
        console.log('Logout detected in another tab');
        setIsAuthenticated(false);
        setCurrentAccount(null);
        toast('You have been logged out in another tab.');
        
        // Redirect to home if on protected routes
        const protectedRoutes = ['/dashboard', '/profile', '/upload', '/history', '/api-keys'];
        const currentPath = window.location.pathname;
        
        if (protectedRoutes.some(route => currentPath.startsWith(route))) {
          navigate('/');
        }
      }
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    window.addEventListener('storage', handleStorageChange);
    
    // Cleanup
    return () => {
      if (window.ethereum && window.ethereum.removeListener) {
        window.ethereum.removeListener('accountsChanged', () => {});
      }
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [navigate]);

  return (
    <AuthContext.Provider
      value={{
        currentAccount,
        isAuthenticated,
        isLoading,
        connectWallet,
        signIn,
        signOut,
        validateSessionNow
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);