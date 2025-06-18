// Format wallet address to display the beginning and end with ellipsis in the middle
export const formatWalletAddress = (address, startChars = 4, endChars = 4) => {
  if (!address) return '';
  if (address.length <= startChars + endChars) return address;
  
  return `${address.slice(0, startChars)}...${address.slice(-endChars)}`;
};

// Format date to readable string
export const formatDate = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric', 
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
};

// Format transaction hash to display the beginning and end with ellipsis in the middle
export const formatTransactionHash = (hash, startChars = 6, endChars = 6) => {
  if (!hash) return '';
  if (hash.length <= startChars + endChars) return hash;
  
  return `${hash.slice(0, startChars)}...${hash.slice(-endChars)}`;
};

// Function to determine if an object is empty
export const isEmptyObject = (obj) => {
  return Object.keys(obj).length === 0;
};

// Format user display name (username or wallet address)
export const formatUserDisplayName = (user, walletAddress, options = {}) => {
  const {
    preferUsername = true,
    withAt = false,
    fallbackToWallet = true
  } = options;

  if (preferUsername && user?.username) {
    return withAt ? `@${user.username}` : user.username;
  }

  if (user?.name && !preferUsername) {
    return user.name;
  }

  if (fallbackToWallet && walletAddress) {
    return formatWalletAddress(walletAddress);
  }

  return 'Anonymous User';
};

// Get user display name with multiple fallbacks
export const getUserDisplayName = (user, walletAddress) => {
  if (user?.name) return user.name;
  if (user?.username) return `@${user.username}`;
  if (walletAddress) return formatWalletAddress(walletAddress);
  return 'Anonymous User';
};