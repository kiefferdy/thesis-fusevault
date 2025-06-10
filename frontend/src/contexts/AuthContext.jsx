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


  // Check if MetaMask is installed
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
        
        // Check if user has active session
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