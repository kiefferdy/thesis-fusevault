import { useState, useCallback } from 'react';
import { transactionFlow } from '../services/blockchainService';

export const useTransactionSigner = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [operation, setOperation] = useState(null);
  const [operationData, setOperationData] = useState(null);
  const [onSuccess, setOnSuccess] = useState(() => () => {});
  const [onError, setOnError] = useState(() => () => {});

  const showUploadSigner = useCallback((assetData, successCallback, errorCallback) => {
    setOperation('upload');
    setOperationData(assetData);
    setOnSuccess(() => successCallback || (() => {}));
    setOnError(() => errorCallback || (() => {}));
    setIsVisible(true);
  }, []);

  const showDeleteSigner = useCallback((assetId, walletAddress, reason, successCallback, errorCallback) => {
    setOperation('delete');
    setOperationData({ assetId, walletAddress, reason });
    setOnSuccess(() => successCallback || (() => {}));
    setOnError(() => errorCallback || (() => {}));
    setIsVisible(true);
  }, []);

  const showEditSigner = useCallback((assetData, successCallback, errorCallback) => {
    setOperation('edit');
    setOperationData(assetData);
    setOnSuccess(() => successCallback || (() => {}));
    setOnError(() => errorCallback || (() => {}));
    setIsVisible(true);
  }, []);

  const hideSigner = useCallback(() => {
    setIsVisible(false);
    setOperation(null);
    setOperationData(null);
  }, []);

  // Direct transaction methods that don't require the UI component
  const uploadWithSigning = useCallback(async (assetData, onProgress) => {
    return await transactionFlow.uploadWithSigning(assetData, onProgress);
  }, []);

  const deleteWithSigning = useCallback(async (assetId, walletAddress, reason, onProgress) => {
    return await transactionFlow.deleteWithSigning(assetId, walletAddress, reason, onProgress);
  }, []);

  const editWithSigning = useCallback(async (assetData, onProgress) => {
    return await transactionFlow.editWithSigning(assetData, onProgress);
  }, []);

  return {
    // UI-based signing
    isVisible,
    operation,
    operationData,
    showUploadSigner,
    showDeleteSigner,
    showEditSigner,
    hideSigner,
    onSuccess,
    onError,
    
    // Direct methods
    uploadWithSigning,
    deleteWithSigning,
    editWithSigning
  };
};