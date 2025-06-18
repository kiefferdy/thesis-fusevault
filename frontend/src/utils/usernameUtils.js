// Username validation and utility functions

/**
 * Validates a username according to FuseVault rules
 * @param {string} username - The username to validate
 * @returns {object} - { isValid: boolean, error: string|null }
 */
export const validateUsername = (username) => {
  if (!username) {
    return { isValid: false, error: 'Username is required' };
  }

  // Check length (3-30 characters)
  if (username.length < 3) {
    return { isValid: false, error: 'Username must be at least 3 characters long' };
  }

  if (username.length > 30) {
    return { isValid: false, error: 'Username must be at most 30 characters long' };
  }

  // Check format: alphanumeric, underscores, hyphens (no spaces or special chars)
  const usernameRegex = /^[a-zA-Z0-9_-]+$/;
  if (!usernameRegex.test(username)) {
    return { isValid: false, error: 'Username can only contain letters, numbers, underscores, and hyphens' };
  }

  // Must start and end with alphanumeric character
  const startsAndEndsWithAlphanumeric = /^[a-zA-Z0-9].*[a-zA-Z0-9]$|^[a-zA-Z0-9]$/;
  if (!startsAndEndsWithAlphanumeric.test(username)) {
    return { isValid: false, error: 'Username must start and end with a letter or number' };
  }

  // No consecutive special characters
  if (/__|-{2,}|_-|-_/.test(username)) {
    return { isValid: false, error: 'Username cannot have consecutive underscores or hyphens' };
  }

  // Reserved usernames
  const reservedUsernames = [
    'admin', 'administrator', 'root', 'api', 'www', 'ftp', 'mail', 'email',
    'user', 'users', 'account', 'accounts', 'profile', 'profiles',
    'dashboard', 'settings', 'config', 'configuration', 'system',
    'fusevault', 'support', 'help', 'about', 'contact', 'info',
    'null', 'undefined', 'true', 'false', 'test', 'demo'
  ];

  if (reservedUsernames.includes(username.toLowerCase())) {
    return { isValid: false, error: 'This username is reserved and cannot be used' };
  }

  return { isValid: true, error: null };
};

/**
 * Normalizes a username (converts to lowercase, trims)
 * @param {string} username - The username to normalize
 * @returns {string} - The normalized username
 */
export const normalizeUsername = (username) => {
  if (!username) return '';
  return username.toLowerCase().trim();
};

/**
 * Generates username suggestions based on a base name
 * @param {string} baseName - The base name to generate suggestions from
 * @returns {string[]} - Array of username suggestions
 */
export const generateUsernameSuggestions = (baseName) => {
  if (!baseName) return [];
  
  const normalized = normalizeUsername(baseName.replace(/[^a-zA-Z0-9]/g, ''));
  if (!normalized) return [];

  const suggestions = [];
  
  // Basic variations
  suggestions.push(normalized);
  suggestions.push(`${normalized}_user`);
  suggestions.push(`${normalized}123`);
  suggestions.push(`${normalized}_${new Date().getFullYear()}`);
  
  // Add random numbers
  for (let i = 0; i < 3; i++) {
    const randomNum = Math.floor(Math.random() * 999) + 1;
    suggestions.push(`${normalized}${randomNum}`);
  }
  
  // Add common suffixes
  const suffixes = ['dev', 'pro', 'x', 'tech', 'code'];
  suffixes.forEach(suffix => {
    suggestions.push(`${normalized}_${suffix}`);
  });
  
  // Remove duplicates and filter valid ones
  const uniqueSuggestions = [...new Set(suggestions)];
  return uniqueSuggestions.filter(suggestion => 
    validateUsername(suggestion).isValid
  ).slice(0, 6); // Return max 6 suggestions
};

/**
 * Formats a username for display (with @ prefix option)
 * @param {string} username - The username to format
 * @param {boolean} withAt - Whether to include @ prefix
 * @returns {string} - The formatted username
 */
export const formatUsernameForDisplay = (username, withAt = false) => {
  if (!username) return '';
  const normalized = normalizeUsername(username);
  return withAt ? `@${normalized}` : normalized;
};

/**
 * Extracts username from various input formats (@username, username, etc.)
 * @param {string} input - The input string
 * @returns {string} - The extracted username
 */
export const extractUsernameFromInput = (input) => {
  if (!input) return '';
  
  // Remove @ prefix if present
  const cleaned = input.trim().replace(/^@/, '');
  return normalizeUsername(cleaned);
};

/**
 * Checks if a string looks like a username (basic format check)
 * @param {string} str - The string to check
 * @returns {boolean} - Whether it looks like a username
 */
export const looksLikeUsername = (str) => {
  if (!str) return false;
  const cleaned = extractUsernameFromInput(str);
  return validateUsername(cleaned).isValid;
};