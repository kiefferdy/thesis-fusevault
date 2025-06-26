import { toast } from 'react-hot-toast';

/**
 * Comprehensive validation and error handling utilities for batch upload functionality
 */

// Asset validation rules
export const VALIDATION_RULES = {
  ASSET_ID: {
    required: true,
    pattern: /^[a-zA-Z0-9_-]+$/,
    minLength: 1,
    maxLength: 100,
    errorMessage: 'Asset ID must be 1-100 characters and contain only letters, numbers, hyphens, and underscores'
  },
  NAME: {
    required: true,
    minLength: 1,
    maxLength: 200,
    errorMessage: 'Name must be 1-200 characters'
  },
  DESCRIPTION: {
    required: false,
    maxLength: 1000,
    errorMessage: 'Description must be less than 1000 characters'
  },
  TAGS: {
    required: false,
    maxItems: 20,
    maxLength: 50,
    errorMessage: 'Maximum 20 tags, each tag must be less than 50 characters'
  }
};

// Batch validation limits
export const BATCH_LIMITS = {
  MAX_ASSETS: 50,
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  MAX_FILES: 50,
  SUPPORTED_FORMATS: ['.json'],
  MIN_ASSETS: 1
};

/**
 * Validate a single asset object
 * @param {Object} asset - Asset to validate
 * @param {number} index - Asset index in batch (for error reporting)
 * @returns {Object} Validation result with errors and warnings
 */
export const validateAsset = (asset, index = 0) => {
  const errors = [];
  const warnings = [];

  // Check if asset is an object
  if (!asset || typeof asset !== 'object') {
    errors.push(`Asset ${index + 1}: Invalid asset format`);
    return { isValid: false, errors, warnings };
  }

  // Validate asset ID
  if (!asset.assetId) {
    errors.push(`Asset ${index + 1}: Missing asset ID`);
  } else {
    const { pattern, minLength, maxLength } = VALIDATION_RULES.ASSET_ID;
    if (typeof asset.assetId !== 'string') {
      errors.push(`Asset ${index + 1}: Asset ID must be a string`);
    } else if (asset.assetId.length < minLength || asset.assetId.length > maxLength) {
      errors.push(`Asset ${index + 1}: ${VALIDATION_RULES.ASSET_ID.errorMessage}`);
    } else if (!pattern.test(asset.assetId)) {
      errors.push(`Asset ${index + 1}: ${VALIDATION_RULES.ASSET_ID.errorMessage}`);
    }
  }

  // Validate critical metadata
  if (!asset.criticalMetadata) {
    errors.push(`Asset ${index + 1}: Missing critical metadata`);
  } else {
    if (typeof asset.criticalMetadata !== 'object') {
      errors.push(`Asset ${index + 1}: Critical metadata must be an object`);
    } else {
      // Validate name
      if (!asset.criticalMetadata.name) {
        warnings.push(`Asset ${index + 1}: Missing name in critical metadata`);
      } else if (typeof asset.criticalMetadata.name !== 'string') {
        errors.push(`Asset ${index + 1}: Name must be a string`);
      } else if (
        asset.criticalMetadata.name.length < VALIDATION_RULES.NAME.minLength ||
        asset.criticalMetadata.name.length > VALIDATION_RULES.NAME.maxLength
      ) {
        errors.push(`Asset ${index + 1}: ${VALIDATION_RULES.NAME.errorMessage}`);
      }

      // Validate description
      if (asset.criticalMetadata.description) {
        if (typeof asset.criticalMetadata.description !== 'string') {
          errors.push(`Asset ${index + 1}: Description must be a string`);
        } else if (asset.criticalMetadata.description.length > VALIDATION_RULES.DESCRIPTION.maxLength) {
          errors.push(`Asset ${index + 1}: ${VALIDATION_RULES.DESCRIPTION.errorMessage}`);
        }
      } else {
        warnings.push(`Asset ${index + 1}: Missing description in critical metadata`);
      }

      // Validate tags
      if (asset.criticalMetadata.tags) {
        if (!Array.isArray(asset.criticalMetadata.tags)) {
          errors.push(`Asset ${index + 1}: Tags must be an array`);
        } else {
          if (asset.criticalMetadata.tags.length > VALIDATION_RULES.TAGS.maxItems) {
            errors.push(`Asset ${index + 1}: ${VALIDATION_RULES.TAGS.errorMessage}`);
          }
          
          asset.criticalMetadata.tags.forEach((tag, tagIndex) => {
            if (typeof tag !== 'string') {
              errors.push(`Asset ${index + 1}: Tag ${tagIndex + 1} must be a string`);
            } else if (tag.length > VALIDATION_RULES.TAGS.maxLength) {
              errors.push(`Asset ${index + 1}: Tag "${tag}" is too long (max ${VALIDATION_RULES.TAGS.maxLength} characters)`);
            }
          });
        }
      }
    }
  }

  // Validate wallet address
  if (!asset.walletAddress) {
    warnings.push(`Asset ${index + 1}: Missing wallet address`);
  } else if (typeof asset.walletAddress !== 'string' || !asset.walletAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
    errors.push(`Asset ${index + 1}: Invalid wallet address format`);
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

/**
 * Validate an entire batch of assets
 * @param {Array} assets - Array of assets to validate
 * @returns {Object} Batch validation result
 */
export const validateBatch = (assets) => {
  const result = {
    isValid: true,
    errors: [],
    warnings: [],
    assetErrors: {},
    assetWarnings: {},
    duplicateAssetIds: [],
    stats: {
      totalAssets: assets.length,
      validAssets: 0,
      assetsWithWarnings: 0,
      assetsWithErrors: 0
    }
  };

  // Check batch size
  if (assets.length === 0) {
    result.errors.push('Batch is empty. Please add at least one asset.');
    result.isValid = false;
    return result;
  }

  if (assets.length > BATCH_LIMITS.MAX_ASSETS) {
    result.errors.push(`Too many assets (${assets.length}). Maximum ${BATCH_LIMITS.MAX_ASSETS} assets per batch.`);
    result.isValid = false;
  }

  // Track asset IDs for duplicate detection
  const assetIdCounts = {};
  
  // Validate each asset
  assets.forEach((asset, index) => {
    const validation = validateAsset(asset, index);
    
    if (validation.errors.length > 0) {
      result.assetErrors[index] = validation.errors;
      result.stats.assetsWithErrors++;
      result.isValid = false;
    } else {
      result.stats.validAssets++;
    }

    if (validation.warnings.length > 0) {
      result.assetWarnings[index] = validation.warnings;
      result.stats.assetsWithWarnings++;
    }

    // Track asset ID for duplicate detection
    if (asset.assetId) {
      assetIdCounts[asset.assetId] = (assetIdCounts[asset.assetId] || 0) + 1;
    }
  });

  // Check for duplicate asset IDs
  Object.entries(assetIdCounts).forEach(([assetId, count]) => {
    if (count > 1) {
      result.duplicateAssetIds.push(assetId);
      result.errors.push(`Duplicate asset ID "${assetId}" found ${count} times`);
      result.isValid = false;
    }
  });

  return result;
};

/**
 * Validate file before processing
 * @param {File} file - File to validate
 * @returns {Object} File validation result
 */
export const validateFile = (file) => {
  const errors = [];
  const warnings = [];

  // Check file size
  if (file.size > BATCH_LIMITS.MAX_FILE_SIZE) {
    errors.push(`File "${file.name}" is too large (${(file.size / 1024 / 1024).toFixed(2)}MB). Maximum ${BATCH_LIMITS.MAX_FILE_SIZE / 1024 / 1024}MB.`);
  }

  // Check file type
  const isValidFormat = BATCH_LIMITS.SUPPORTED_FORMATS.some(format => 
    file.name.toLowerCase().endsWith(format.toLowerCase())
  );
  
  if (!isValidFormat) {
    errors.push(`File "${file.name}" has unsupported format. Supported formats: ${BATCH_LIMITS.SUPPORTED_FORMATS.join(', ')}`);
  }

  // Check if file name is reasonable
  if (file.name.length > 255) {
    warnings.push(`File "${file.name}" has a very long name`);
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

/**
 * Parse and validate JSON content
 * @param {string} content - JSON content to parse
 * @param {string} source - Source identifier for error reporting
 * @returns {Object} Parse result with validation
 */
export const parseAndValidateJSON = (content, source = 'input') => {
  try {
    const parsed = JSON.parse(content);
    
    // Determine if it's a single asset or array
    const assets = Array.isArray(parsed) ? parsed : [parsed];
    
    // Validate the batch
    const validation = validateBatch(assets);
    
    return {
      success: true,
      assets,
      validation,
      source
    };
  } catch (error) {
    return {
      success: false,
      error: `Invalid JSON in ${source}: ${error.message}`,
      source
    };
  }
};

/**
 * Enhanced error handler with user-friendly messages
 * @param {Error} error - Error object
 * @param {string} context - Context where error occurred
 * @returns {string} User-friendly error message
 */
export const handleBatchUploadError = (error, context = 'batch upload') => {
  const errorMessage = error?.message || error?.toString() || 'Unknown error';
  
  // Network and connectivity errors
  if (errorMessage.includes('network') || errorMessage.includes('fetch')) {
    const message = `Network error during ${context}. Please check your connection and try again.`;
    toast.error(message);
    return message;
  }
  
  // Validation errors
  if (errorMessage.includes('validation') || errorMessage.includes('invalid')) {
    const message = `Validation error: ${errorMessage}`;
    toast.error(message);
    return message;
  }
  
  // Blockchain/MetaMask errors
  if (errorMessage.includes('user rejected') || errorMessage.includes('User denied')) {
    const message = 'Transaction was cancelled by user';
    toast.error(message);
    return message;
  }
  
  if (errorMessage.includes('insufficient funds')) {
    const message = 'Insufficient funds to complete transaction. Please check your ETH balance.';
    toast.error(message);
    return message;
  }
  
  if (errorMessage.includes('gas')) {
    const message = 'Gas limit too low. Please try again with higher gas settings.';
    toast.error(message);
    return message;
  }
  
  // Rate limiting
  if (errorMessage.includes('rate limit') || errorMessage.includes('429')) {
    const message = 'Request rate limit exceeded. Please wait a moment and try again.';
    toast.error(message);
    return message;
  }
  
  // Server errors
  if (errorMessage.includes('500') || errorMessage.includes('server error')) {
    const message = 'Server error occurred. Please try again later.';
    toast.error(message);
    return message;
  }
  
  // Generic error
  const message = `Error during ${context}: ${errorMessage}`;
  toast.error(message);
  return message;
};

/**
 * Generate validation summary for UI display
 * @param {Object} validation - Validation result from validateBatch
 * @returns {Object} Summary for UI display
 */
export const generateValidationSummary = (validation) => {
  const { stats, errors, warnings, duplicateAssetIds } = validation;
  
  return {
    canProceed: validation.isValid,
    summary: {
      total: stats.totalAssets,
      valid: stats.validAssets,
      withWarnings: stats.assetsWithWarnings,
      withErrors: stats.assetsWithErrors,
      duplicates: duplicateAssetIds.length
    },
    messages: {
      errors: errors,
      warnings: warnings
    },
    recommendation: validation.isValid 
      ? 'Batch is ready for upload'
      : 'Please fix the errors before proceeding with upload'
  };
};

/**
 * Sanitize asset data before upload
 * @param {Object} asset - Asset to sanitize
 * @returns {Object} Sanitized asset
 */
export const sanitizeAsset = (asset) => {
  const sanitized = {
    assetId: asset.assetId?.trim(),
    walletAddress: asset.walletAddress?.trim(),
    criticalMetadata: {},
    nonCriticalMetadata: asset.nonCriticalMetadata || {}
  };

  // Sanitize critical metadata
  if (asset.criticalMetadata) {
    sanitized.criticalMetadata = {
      name: asset.criticalMetadata.name?.trim(),
      description: asset.criticalMetadata.description?.trim(),
      tags: Array.isArray(asset.criticalMetadata.tags) 
        ? asset.criticalMetadata.tags.map(tag => tag?.trim()).filter(Boolean)
        : [],
      ...Object.fromEntries(
        Object.entries(asset.criticalMetadata)
          .filter(([key]) => !['name', 'description', 'tags'].includes(key))
          .map(([key, value]) => [key, typeof value === 'string' ? value.trim() : value])
      )
    };
  }

  return sanitized;
};

export default {
  validateAsset,
  validateBatch,
  validateFile,
  parseAndValidateJSON,
  handleBatchUploadError,
  generateValidationSummary,
  sanitizeAsset,
  VALIDATION_RULES,
  BATCH_LIMITS
};