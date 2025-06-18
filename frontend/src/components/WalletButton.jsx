import { Button } from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { useUser } from '../hooks/useUser';
import { formatWalletAddress } from '../utils/formatters';

function WalletButton() {
  const { 
    currentAccount, 
    isAuthenticated, 
    connectWallet, 
    signIn, 
    signOut, 
    isLoading
  } = useAuth();
  
  const { user } = useUser();

  const handleAction = async () => {
    if (isLoading) return;
    
    if (!currentAccount) {
      // Connect wallet if not connected
      await connectWallet();
    } else if (!isAuthenticated) {
      // Sign in if wallet is connected but not authenticated
      await signIn();
    } else {
      // Sign out if already authenticated
      await signOut();
    }
  };

  // Determine button text based on current state
  const getButtonText = () => {
    if (isLoading) return 'Loading...';
    if (!currentAccount) return 'Connect Wallet';
    if (!isAuthenticated) return 'Sign In';
    
    // Show username if available, otherwise wallet address
    const displayText = user?.username 
      ? `@${user.username}` 
      : formatWalletAddress(currentAccount);
    
    return `${displayText} | Sign Out`;
  };

  return (
    <Button
      variant="contained"
      color={isAuthenticated ? "secondary" : "primary"}
      onClick={handleAction}
      disabled={isLoading}
      size="small"
    >
      {getButtonText()}
    </Button>
  );
}

export default WalletButton;