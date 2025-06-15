import { useState, useEffect } from 'react';
import { metamaskUtils, transactionFlow } from '../services/blockchainService';

const TransactionSigner = ({ 
  operation, 
  operationData, 
  onSuccess, 
  onError, 
  onCancel,
  isVisible = false 
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [error, setError] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [gasEstimate, setGasEstimate] = useState(null);
  const [networkStatus, setNetworkStatus] = useState(null);
  const [switchingNetwork, setSwitchingNetwork] = useState(false);

  useEffect(() => {
    if (isVisible && !isProcessing) {
      estimateGas();
      checkNetwork();
    }
  }, [isVisible, operationData]);

  const checkNetwork = async () => {
    try {
      if (metamaskUtils.isMetaMaskAvailable()) {
        const status = await metamaskUtils.checkNetwork();
        setNetworkStatus(status);
      }
    } catch (error) {
      console.error('Error checking network:', error);
    }
  };

  const handleNetworkSwitch = async () => {
    setSwitchingNetwork(true);
    try {
      await metamaskUtils.switchToSepolia();
      // Recheck network after switching
      setTimeout(() => {
        checkNetwork();
        setSwitchingNetwork(false);
      }, 1000);
    } catch (error) {
      console.error('Error switching network:', error);
      setError('Failed to switch network: ' + (error.message || 'Unknown error'));
      setSwitchingNetwork(false);
    }
  };

  const estimateGas = async () => {
    try {
      if (operation === 'upload' && operationData) {
        // For uploads, we don't have a direct gas estimation endpoint
        // This would be enhanced based on your specific needs
        setGasEstimate({
          estimatedGas: 200000,
          gasPrice: 20000000000, // 20 gwei
          estimatedCostEth: '0.004'
        });
      } else if (operation === 'delete' && operationData?.assetId) {
        // For deletes, we can estimate
        setGasEstimate({
          estimatedGas: 150000,
          gasPrice: 20000000000,
          estimatedCostEth: '0.003'
        });
      }
    } catch (error) {
      console.error('Error estimating gas:', error);
    }
  };

  const validateTransaction = () => {
    if (!operation) {
      throw new Error('No operation specified');
    }
    
    if (!operationData) {
      throw new Error('No operation data provided');
    }
    
    if (operation === 'upload') {
      if (!operationData.assetId || !operationData.walletAddress) {
        throw new Error('Asset ID and wallet address are required for upload');
      }
    } else if (operation === 'delete') {
      if (!operationData.assetId || !operationData.walletAddress) {
        throw new Error('Asset ID and wallet address are required for deletion');
      }
    }
  };

  const handleTransaction = async () => {
    setIsProcessing(true);
    setProgress(0);
    setError(null);

    try {
      // Validate transaction data
      validateTransaction();
      
      // Check MetaMask availability
      if (!metamaskUtils.isMetaMaskAvailable()) {
        throw new Error('MetaMask not detected. Please install the MetaMask browser extension.');
      }

      setCurrentStep('Checking wallet connection...');
      setProgress(5);
      
      let account;
      try {
        account = await metamaskUtils.getCurrentAccount();
      } catch (accountError) {
        throw new Error('Failed to connect to MetaMask. Please ensure MetaMask is unlocked.');
      }
      
      if (!account) {
        try {
          // Try to request account access
          await window.ethereum.request({ method: 'eth_requestAccounts' });
          account = await metamaskUtils.getCurrentAccount();
        } catch (requestError) {
          throw new Error('Please connect your MetaMask wallet and try again.');
        }
      }
      
      // Verify the account matches the operation data
      const expectedWallet = operationData.walletAddress?.toLowerCase();
      if (expectedWallet && account.toLowerCase() !== expectedWallet) {
        throw new Error(
          `Wallet mismatch: Expected ${expectedWallet} but connected wallet is ${account}. ` +
          'Please switch to the correct account in MetaMask.'
        );
      }

      // Execute the appropriate transaction flow
      let result;
      if (operation === 'upload') {
        result = await transactionFlow.uploadWithSigning(
          operationData,
          (step, progressValue) => {
            setCurrentStep(step);
            setProgress(progressValue);
          }
        );
      } else if (operation === 'delete') {
        result = await transactionFlow.deleteWithSigning(
          operationData.assetId,
          operationData.walletAddress,
          operationData.reason,
          (step, progressValue) => {
            setCurrentStep(step);
            setProgress(progressValue);
          }
        );
      } else {
        throw new Error(`Unsupported operation: ${operation}`);
      }

      setProgress(100);
      setCurrentStep('Transaction completed successfully!');
      
      // Call success callback after a brief delay
      setTimeout(() => {
        if (onSuccess) {
          onSuccess(result);
        }
      }, 1000);

    } catch (error) {
      console.error('Transaction error:', error);
      
      let errorMessage = error?.message || 'Transaction failed';
      
      // Add helpful context for common errors
      if (errorMessage.includes('User denied') || errorMessage.includes('user rejected')) {
        errorMessage = 'Transaction was cancelled. Please try again if needed.';
      } else if (errorMessage.includes('insufficient funds')) {
        errorMessage = 'Insufficient ETH balance. Please add funds to your wallet and try again.';
      } else if (errorMessage.includes('network')) {
        errorMessage = 'Network error. Please check your connection and try again.';
      }
      
      setError(errorMessage);
      if (onError) {
        onError(error);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancel = () => {
    if (!isProcessing) {
      onCancel();
    }
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="transaction-signer-overlay">
      <div className="transaction-signer-modal">
        <div className="transaction-signer-header">
          <h3>Sign Transaction</h3>
          {!isProcessing && (
            <button 
              className="close-button" 
              onClick={handleCancel}
              aria-label="Close"
            >
              ×
            </button>
          )}
        </div>

        <div className="transaction-signer-content">
          <div className="operation-info">
            <h4>Operation: {operation.charAt(0).toUpperCase() + operation.slice(1)}</h4>
            
            {operation === 'upload' && operationData && (
              <div className="operation-details">
                <p><strong>Asset ID:</strong> {operationData.assetId}</p>
                <p><strong>Wallet:</strong> {operationData.walletAddress}</p>
              </div>
            )}
            
            {operation === 'delete' && operationData && (
              <div className="operation-details">
                <p><strong>Asset ID:</strong> {operationData.assetId}</p>
                <p><strong>Wallet:</strong> {operationData.walletAddress}</p>
                {operationData.reason && <p><strong>Reason:</strong> {operationData.reason}</p>}
              </div>
            )}
          </div>

          {networkStatus && (
            <div className={`network-status ${networkStatus.isCorrectNetwork ? 'correct' : 'incorrect'}`}>
              <h4>Network Status</h4>
              {networkStatus.isCorrectNetwork ? (
                <div className="network-correct">
                  <p>✅ Connected to Sepolia Testnet</p>
                </div>
              ) : (
                <div className="network-incorrect">
                  <p>⚠️ Wrong Network: {networkStatus.networkName}</p>
                  <p>Please switch to Sepolia Testnet to continue.</p>
                  <button 
                    className="btn btn-warning" 
                    onClick={handleNetworkSwitch}
                    disabled={switchingNetwork}
                  >
                    {switchingNetwork ? 'Switching...' : 'Switch to Sepolia'}
                  </button>
                </div>
              )}
            </div>
          )}

          {gasEstimate && (
            <div className="gas-estimate">
              <h4>Transaction Cost Estimate</h4>
              <div className="gas-details">
                <p><strong>Gas Limit:</strong> {gasEstimate.estimatedGas.toLocaleString()}</p>
                <p><strong>Gas Price:</strong> {(gasEstimate.gasPrice / 1e9).toFixed(1)} Gwei</p>
                <p><strong>Estimated Cost:</strong> {gasEstimate.estimatedCostEth} ETH</p>
              </div>
              <button 
                className="toggle-details" 
                onClick={() => setShowDetails(!showDetails)}
              >
                {showDetails ? 'Hide' : 'Show'} Details
              </button>
            </div>
          )}

          {isProcessing && (
            <div className="progress-section">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="progress-text">{currentStep}</p>
              <p className="progress-percentage">{progress}%</p>
            </div>
          )}

          {error && (
            <div className="error-section">
              <div className="error-message">
                <h4>Transaction Failed</h4>
                <p>{error}</p>
              </div>
            </div>
          )}

          <div className="action-buttons">
            {!isProcessing && !error && (
              <>
                <button 
                  className="btn btn-primary" 
                  onClick={handleTransaction}
                  disabled={networkStatus && !networkStatus.isCorrectNetwork}
                >
                  Sign with MetaMask
                </button>
                <button 
                  className="btn btn-secondary" 
                  onClick={handleCancel}
                >
                  Cancel
                </button>
              </>
            )}

            {error && (
              <>
                <button 
                  className="btn btn-primary" 
                  onClick={handleTransaction}
                >
                  Retry
                </button>
                <button 
                  className="btn btn-secondary" 
                  onClick={handleCancel}
                >
                  Cancel
                </button>
              </>
            )}

            {isProcessing && (
              <p className="processing-note">
                Please check MetaMask for transaction signing prompts...
              </p>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        .transaction-signer-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(0, 0, 0, 0.5);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1000;
        }

        .transaction-signer-modal {
          background: white;
          border-radius: 8px;
          padding: 24px;
          max-width: 500px;
          width: 90%;
          max-height: 80vh;
          overflow-y: auto;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }

        .transaction-signer-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .transaction-signer-header h3 {
          margin: 0;
          color: #333;
        }

        .close-button {
          background: none;
          border: none;
          font-size: 24px;
          cursor: pointer;
          color: #666;
          padding: 0;
          width: 30px;
          height: 30px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .close-button:hover {
          color: #333;
        }

        .operation-info {
          margin-bottom: 20px;
          padding: 16px;
          background-color: #f8f9fa;
          border-radius: 6px;
        }

        .operation-info h4 {
          margin: 0 0 12px 0;
          color: #495057;
        }

        .operation-details p {
          margin: 4px 0;
          font-size: 14px;
          color: #6c757d;
        }
        
        .network-status {
          margin-bottom: 20px;
          padding: 16px;
          border-radius: 6px;
          border-left: 4px solid;
        }
        
        .network-status.correct {
          background-color: #d4edda;
          border-left-color: #28a745;
        }
        
        .network-status.incorrect {
          background-color: #fff3cd;
          border-left-color: #ffc107;
        }
        
        .network-status h4 {
          margin: 0 0 12px 0;
        }
        
        .network-correct {
          color: #155724;
        }
        
        .network-incorrect {
          color: #856404;
        }
        
        .network-incorrect p {
          margin: 4px 0;
        }
        
        .btn-warning {
          background-color: #ffc107;
          color: #212529;
          margin-top: 8px;
          padding: 8px 16px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
          transition: background-color 0.2s;
        }
        
        .btn-warning:hover:not(:disabled) {
          background-color: #e0a800;
        }
        
        .btn-warning:disabled {
          background-color: #6c757d;
          color: white;
          cursor: not-allowed;
          opacity: 0.6;
        }

        .gas-estimate {
          margin-bottom: 20px;
          padding: 16px;
          background-color: #e8f4f8;
          border-radius: 6px;
          border-left: 4px solid #17a2b8;
        }

        .gas-estimate h4 {
          margin: 0 0 12px 0;
          color: #0c5460;
        }

        .gas-details p {
          margin: 4px 0;
          font-size: 14px;
          color: #0c5460;
        }

        .toggle-details {
          background: none;
          border: none;
          color: #17a2b8;
          text-decoration: underline;
          cursor: pointer;
          padding: 0;
          margin-top: 8px;
        }

        .progress-section {
          margin-bottom: 20px;
        }

        .progress-bar {
          width: 100%;
          height: 8px;
          background-color: #e9ecef;
          border-radius: 4px;
          overflow: hidden;
          margin-bottom: 12px;
        }

        .progress-fill {
          height: 100%;
          background-color: #28a745;
          transition: width 0.3s ease;
        }

        .progress-text {
          font-weight: 500;
          margin: 8px 0 4px 0;
          color: #495057;
        }

        .progress-percentage {
          font-size: 14px;
          color: #6c757d;
          margin: 0;
        }

        .error-section {
          margin-bottom: 20px;
        }

        .error-message {
          padding: 16px;
          background-color: #f8d7da;
          border: 1px solid #f5c6cb;
          border-radius: 6px;
          color: #721c24;
        }

        .error-message h4 {
          margin: 0 0 8px 0;
        }

        .error-message p {
          margin: 0;
          font-size: 14px;
        }

        .action-buttons {
          display: flex;
          gap: 12px;
          justify-content: flex-end;
        }

        .btn {
          padding: 10px 20px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
          transition: background-color 0.2s;
        }

        .btn-primary {
          background-color: #007bff;
          color: white;
        }

        .btn-primary:hover {
          background-color: #0056b3;
        }

        .btn-secondary {
          background-color: #6c757d;
          color: white;
        }

        .btn-secondary:hover {
          background-color: #545b62;
        }
        
        .btn-primary:disabled {
          background-color: #6c757d;
          border-color: #6c757d;
          cursor: not-allowed;
          opacity: 0.6;
        }
        
        .btn-secondary:disabled {
          cursor: not-allowed;
          opacity: 0.6;
        }

        .processing-note {
          margin: 0;
          font-style: italic;
          color: #6c757d;
          text-align: center;
        }
      `}</style>
    </div>
  );
};

export default TransactionSigner;