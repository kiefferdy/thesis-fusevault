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