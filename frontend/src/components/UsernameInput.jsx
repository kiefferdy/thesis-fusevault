import { useState, useEffect, useCallback } from 'react';
import {
  TextField,
  InputAdornment,
  CircularProgress,
  Chip,
  Box,
  Typography,
  Collapse,
  Alert
} from '@mui/material';
import {
  Person,
  Check,
  Close,
  Warning
} from '@mui/icons-material';
import { validateUsername, normalizeUsername, generateUsernameSuggestions } from '../utils/usernameUtils';
import { useUser } from '../hooks/useUser';

// Debounce hook for username checking
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

function UsernameInput({ 
  value = '', 
  onChange, 
  onValidationChange,
  error: externalError,
  helperText,
  required = false,
  disabled = false,
  label = 'Username',
  placeholder = 'Enter your username',
  showSuggestions = true,
  fullWidth = true,
  margin = 'normal',
  variant = 'outlined',
  currentUserUsername = null, // Add prop to skip checking current user's username
  ...textFieldProps 
}) {
  const [inputValue, setInputValue] = useState(value);
  const [validationState, setValidationState] = useState({
    isValid: null,
    error: null,
    isChecking: false
  });
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestionBox, setShowSuggestionBox] = useState(false);

  const { 
    checkUsernameAvailability, 
    isCheckingUsername, 
    usernameCheckResult, 
    usernameCheckError 
  } = useUser();

  // Sync internal value with external value prop
  useEffect(() => {
    setInputValue(value || '');
  }, [value]);

  // Debounce the input value for server-side checking
  const debouncedValue = useDebounce(inputValue.trim(), 800);

  // Handle input changes
  const handleInputChange = useCallback((event) => {
    const newValue = event.target.value;
    setInputValue(newValue);
    
    // Call parent onChange
    if (onChange) {
      onChange(newValue);
    }

    // Reset validation state when typing
    if (validationState.isValid !== null) {
      setValidationState({
        isValid: null,
        error: null,
        isChecking: false
      });
    }
  }, [onChange, validationState.isValid]);

  // Validate and check availability when debounced value changes
  useEffect(() => {
    if (!debouncedValue) {
      setValidationState({
        isValid: required ? false : null,
        error: required ? 'Username is required' : null,
        isChecking: false
      });
      setSuggestions([]);
      setShowSuggestionBox(false);
      
      if (onValidationChange) {
        onValidationChange({
          isValid: !required,
          error: required ? 'Username is required' : null
        });
      }
      return;
    }

    const normalizedValue = normalizeUsername(debouncedValue);
    
    // Client-side validation first
    const clientValidation = validateUsername(normalizedValue);
    
    if (!clientValidation.isValid) {
      setValidationState({
        isValid: false,
        error: clientValidation.error,
        isChecking: false
      });
      
      // Generate suggestions for invalid usernames
      if (showSuggestions) {
        const usernameSuggestions = generateUsernameSuggestions(normalizedValue);
        setSuggestions(usernameSuggestions);
        setShowSuggestionBox(usernameSuggestions.length > 0);
      }
      
      if (onValidationChange) {
        onValidationChange({
          isValid: false,
          error: clientValidation.error
        });
      }
      return;
    }

    // If client validation passes, check server availability
    // Skip server check if this is the user's current username
    if (currentUserUsername && normalizedValue.toLowerCase() === currentUserUsername.toLowerCase()) {
      setValidationState({
        isValid: true,
        error: null,
        isChecking: false
      });
      
      if (onValidationChange) {
        onValidationChange({
          isValid: true,
          error: null
        });
      }
      return;
    }

    setValidationState(prev => ({
      ...prev,
      isChecking: true
    }));

    checkUsernameAvailability(normalizedValue);
  }, [debouncedValue, required, checkUsernameAvailability, showSuggestions, onValidationChange, currentUserUsername]);

  // Handle server response
  useEffect(() => {
    if (usernameCheckResult) {
      const isAvailable = usernameCheckResult.available;
      setValidationState({
        isValid: isAvailable,
        error: isAvailable ? null : 'Username is already taken',
        isChecking: false
      });
      
      // Generate suggestions if username is taken
      if (!isAvailable && showSuggestions) {
        const usernameSuggestions = generateUsernameSuggestions(usernameCheckResult.username);
        setSuggestions(usernameSuggestions);
        setShowSuggestionBox(true);
      } else {
        setSuggestions([]);
        setShowSuggestionBox(false);
      }
      
      if (onValidationChange) {
        onValidationChange({
          isValid: isAvailable,
          error: isAvailable ? null : 'Username is already taken'
        });
      }
    }
  }, [usernameCheckResult, showSuggestions, onValidationChange]);

  // Handle server errors
  useEffect(() => {
    if (usernameCheckError) {
      setValidationState({
        isValid: false,
        error: 'Unable to check username availability',
        isChecking: false
      });
      
      if (onValidationChange) {
        onValidationChange({
          isValid: false,
          error: 'Unable to check username availability'
        });
      }
    }
  }, [usernameCheckError, onValidationChange]);

  // Handle suggestion click
  const handleSuggestionClick = (suggestion) => {
    setInputValue(suggestion);
    if (onChange) {
      onChange(suggestion);
    }
    setShowSuggestionBox(false);
  };

  // Determine the current state
  const isChecking = validationState.isChecking || isCheckingUsername;
  const currentError = externalError || validationState.error;
  const isValid = validationState.isValid;

  // Get the appropriate adornment icon
  const getEndAdornment = () => {
    if (isChecking) {
      return <CircularProgress size={20} />;
    }
    
    if (isValid === true) {
      return <Check color="success" />;
    }
    
    if (isValid === false) {
      return <Close color="error" />;
    }
    
    return null;
  };

  return (
    <Box>
      <TextField
        {...textFieldProps}
        label={label}
        value={inputValue}
        onChange={handleInputChange}
        error={!!currentError}
        helperText={currentError || helperText}
        required={required}
        disabled={disabled}
        placeholder={placeholder}
        fullWidth={fullWidth}
        margin={margin}
        variant={variant}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Person />
            </InputAdornment>
          ),
          endAdornment: getEndAdornment() && (
            <InputAdornment position="end">
              {getEndAdornment()}
            </InputAdornment>
          ),
        }}
      />
      
      {/* Username Suggestions */}
      <Collapse in={showSuggestionBox && suggestions.length > 0}>
        <Box sx={{ mt: 1 }}>
          <Alert severity="info" icon={<Warning />}>
            <Typography variant="body2" gutterBottom>
              Try these available alternatives:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {suggestions.map((suggestion, index) => (
                <Chip
                  key={index}
                  label={suggestion}
                  variant="outlined"
                  size="small"
                  clickable
                  onClick={() => handleSuggestionClick(suggestion)}
                  sx={{ fontSize: '0.75rem' }}
                />
              ))}
            </Box>
          </Alert>
        </Box>
      </Collapse>
    </Box>
  );
}

export default UsernameInput;