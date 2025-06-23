import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { toast } from 'react-hot-toast';
import { useDelegation } from '../hooks/useDelegation';
import delegationService from '../services/delegationService';
import './DelegationDialog.css';

/**
 * Full delegation UI in a dialog/modal
 * Handles the complete delegation workflow with multiple steps
 */
const DelegationDialog = ({ 
  isOpen, 
  onClose, 
  title = "Server Wallet Delegation" 
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [isClosing, setIsClosing] = useState(false);
  const [isDelegatingLocal, setIsDelegatingLocal] = useState(false);
  
  const {
    serverInfo,
    isDelegated,
    revoke,
    isDelegating,
    refreshStatus,
    getDelegationInfo,
    hasWallet,
    error,
    walletAddress
  } = useDelegation();

  // Get signer for manual transaction handling
  const [signer, setSigner] = useState(null);
  
  useEffect(() => {
    const initializeSigner = async () => {
      if (walletAddress && window.ethereum) {
        try {
          const provider = new ethers.BrowserProvider(window.ethereum);
          const walletSigner = await provider.getSigner();
          setSigner(walletSigner);
        } catch (error) {
          console.error('Error initializing signer:', error);
          setSigner(null);
        }
      } else {
        setSigner(null);
      }
    };

    initializeSigner();
  }, [walletAddress]);

  const delegationInfo = getDelegationInfo();
  const explanations = delegationService.getDelegationExplanations();

  // Reset step when dialog opens/closes
  useEffect(() => {
    if (isOpen && !isDelegated) {
      setActiveStep(0);
    }
  }, [isOpen, isDelegated]);

  // Handle delegation action
  const handleDelegate = async () => {
    if (!serverInfo?.server_wallet_address) {
      toast.error('Server wallet address not available');
      return;
    }

    if (!signer) {
      toast.error('Wallet signer not available. Please ensure MetaMask is connected.');
      return;
    }

    setIsDelegatingLocal(true);
    toast.loading('Preparing delegation transaction...', { id: 'delegation-loading' });

    try {
      // Phase 1: Prepare transaction (stay on step 1, just show loading on button)
      const txData = await delegationService.prepareDelegationTransaction(
        serverInfo.server_wallet_address,
        true
      );

      if (!txData.success) {
        throw new Error(txData.error || 'Failed to prepare delegation transaction');
      }

      // Phase 2: Sign transaction (MetaMask prompt - still on step 1)
      toast.loading('Please sign the transaction in MetaMask...', { id: 'delegation-loading' });
      const tx = await signer.sendTransaction(txData.transaction);
      
      // Phase 3: Transaction sent! Now move to confirming step
      toast.loading('Transaction submitted. Waiting for confirmation...', { id: 'delegation-loading' });
      setActiveStep(2);
      
      // Phase 4: Wait for blockchain confirmation
      const receipt = await tx.wait();
      
      if (receipt.status === 0) {
        throw new Error('Transaction failed on blockchain');
      }

      // Phase 5: Refresh status and move to success
      await refreshStatus();
      setActiveStep(3);
      
      toast.success(
        `Delegation successful! Transaction: ${delegationService.formatAddress(receipt.hash)}`, 
        { id: 'delegation-loading', duration: 5000 }
      );
      
    } catch (error) {
      console.error('Delegation failed:', error);
      
      // Handle specific error types
      let errorMessage = 'Delegation failed';
      
      if (error.code === 4001) {
        errorMessage = 'Transaction rejected by user';
      } else if (error.code === -32603) {
        errorMessage = 'Network error - please check your connection';
      } else if (error.message?.includes('insufficient funds')) {
        errorMessage = 'Insufficient funds for gas fee';
      } else if (error.message?.includes('nonce')) {
        errorMessage = 'Transaction nonce error - please try again';
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      toast.error(errorMessage, { id: 'delegation-loading' });
      
      // Stay on or go back to approval step if there's an error
      setActiveStep(1);
    } finally {
      setIsDelegatingLocal(false);
    }
  };

  // Handle revocation action
  const handleRevoke = async () => {
    if (!window.confirm('Are you sure you want to revoke delegation? This will disable API key functionality.')) {
      return;
    }
    
    try {
      await revoke();
      await refreshStatus();
      setActiveStep(0); // Reset to first step
    } catch (error) {
      console.error('Revocation failed:', error);
      // Error handling is done in the hook
    }
  };

  // Handle close with animation
  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      setIsClosing(false);
      onClose();
    }, 200);
  };

  // Don't render if not open
  if (!isOpen && !isClosing) return null;

  const steps = [
    {
      label: 'Understanding Delegation',
      content: (
        <div className="step-content">
          <div className="step-header">
            <h3>🔒 What is Delegation?</h3>
          </div>
          <div className="explanation-content">
            <p>{explanations.notDelegated.description}</p>
            <div className="benefits-list">
              <h4>Key Benefits:</h4>
              <ul>
                {explanations.notDelegated.benefits.map((benefit, index) => (
                  <li key={index}>{benefit}</li>
                ))}
              </ul>
            </div>
            {delegationInfo && (
              <div className="technical-details">
                <h4>Technical Details:</h4>
                <div className="detail-row">
                  <span>Your wallet:</span>
                  <code>{delegationInfo.userWalletFormatted}</code>
                </div>
                <div className="detail-row">
                  <span>Server wallet:</span>
                  <code>{delegationInfo.serverWalletFormatted}</code>
                </div>
                <div className="detail-row">
                  <span>Network:</span>
                  <span>{delegationInfo.network.name}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )
    },
    {
      label: 'Approve Delegation',
      content: (
        <div className="step-content">
          <div className="step-header">
            <h3>⚡ Approve Transaction</h3>
          </div>
          <div className="approval-content">
            <div className="info-box">
              <p>You will be asked to sign a transaction to delegate the server wallet.</p>
              <p><strong>This transaction will:</strong></p>
              <ul>
                <li>Grant permission to the FuseVault server</li>
                <li>Enable API key functionality</li>
                <li>Cost a small gas fee (usually under $1)</li>
              </ul>
            </div>
            
            {delegationInfo && (
              <div className="transaction-details">
                <h4>Transaction Details:</h4>
                <div className="detail-row">
                  <span>Function:</span>
                  <code>setDelegate</code>
                </div>
                <div className="detail-row">
                  <span>Delegate to:</span>
                  <code>{delegationInfo.serverWalletFormatted}</code>
                </div>
                <div className="detail-row">
                  <span>Status:</span>
                  <span className="status-badge">Enable</span>
                </div>
              </div>
            )}

            {!hasWallet && (
              <div className="wallet-warning">
                <p>Please connect your wallet first</p>
              </div>
            )}
          </div>
        </div>
      )
    },
    {
      label: 'Transaction Confirming',
      content: (
        <div className="step-content">
          <div className="step-header">
            <h3>⏳ Confirming Transaction</h3>
          </div>
          <div className="confirming-content">
            <div className="transaction-progress">
              <div className="progress-spinner"></div>
              <h4>Please wait while your transaction is being confirmed...</h4>
              <p>
                Your transaction has been submitted to the blockchain and is being processed. 
                This usually takes 15-30 seconds on Sepolia testnet.
              </p>
            </div>
            
            <div className="info-box">
              <h4>What's happening:</h4>
              <ul>
                <li>✅ Transaction signed and submitted</li>
                <li>🔄 Waiting for blockchain confirmation</li>
                <li>⏳ Processing delegation status update</li>
              </ul>
            </div>
            
            <div className="confirmation-note">
              <p><strong>Note:</strong> Do not close this window or refresh the page.</p>
            </div>
          </div>
        </div>
      )
    },
    {
      label: 'Delegation Complete',
      content: (
        <div className="step-content">
          <div className="step-header success">
            <div className="success-icon">✅</div>
            <h3>Delegation Successful!</h3>
          </div>
          <div className="success-content">
            <p>You have successfully delegated permission to the FuseVault server.</p>
            <div className="next-steps">
              <h4>What's next?</h4>
              <ul>
                <li>You can now create and use API keys</li>
                <li>Your assets remain under your full control</li>
                <li>You can revoke delegation at any time</li>
              </ul>
            </div>
          </div>
        </div>
      )
    }
  ];

  return (
    <div className={`delegation-overlay ${isClosing ? 'closing' : ''}`}>
      <div className="delegation-dialog">
        <div className="dialog-header">
          <h2>🛡️ {title}</h2>
          <button className="close-button" onClick={handleClose}>×</button>
        </div>
        
        <div className="dialog-content">
          {error && (
            <div className="error-message">
              <p>⚠️ Error: {error.message || 'An error occurred'}</p>
            </div>
          )}

          {isDelegated ? (
            // Show delegation management for already delegated users
            <div className="delegation-management">
              <div className="current-status success">
                <div className="status-icon">✅</div>
                <div className="status-info">
                  <h3>Delegation is Active</h3>
                  <p>{explanations.delegated.description}</p>
                </div>
              </div>

              {delegationInfo && (
                <div className="delegation-details">
                  <h4>Current Delegation:</h4>
                  <div className="detail-row">
                    <span>Your wallet:</span>
                    <code>{delegationInfo.userWalletFormatted}</code>
                  </div>
                  <div className="detail-row">
                    <span>Delegated to:</span>
                    <code>{delegationInfo.serverWalletFormatted}</code>
                  </div>
                  <div className="detail-row">
                    <span>Permissions:</span>
                    <div className="permissions">
                      {delegationInfo.isDelegated && <span className="permission-badge">Read</span>}
                      {delegationInfo.canUpdate && <span className="permission-badge">Write</span>}
                      {delegationInfo.canDelete && <span className="permission-badge">Delete</span>}
                    </div>
                  </div>
                </div>
              )}

              <div className="management-actions">
                <button 
                  className="btn btn-danger btn-revoke"
                  onClick={handleRevoke}
                  disabled={isDelegating}
                >
                  <span style={{ display: 'contents' }}>
                    {isDelegating ? (
                      <>
                        <div className="spinner-small"></div>
                        Revoking...
                      </>
                    ) : (
                      'Revoke Delegation'
                    )}
                  </span>
                </button>
                <p className="revoke-warning">
                  ⚠️ Revoking delegation will disable API key functionality
                </p>
              </div>
            </div>
          ) : (
            // Show delegation setup wizard for non-delegated users
            <div className="delegation-wizard">
              <div className="steps-indicator">
                {steps.map((step, index) => (
                  <div 
                    key={index}
                    className={`step-indicator ${index <= activeStep ? 'active' : ''} ${index === activeStep ? 'current' : ''}`}
                  >
                    <div className="step-number">{index + 1}</div>
                    <div className="step-label">{step.label}</div>
                  </div>
                ))}
              </div>

              <div className="step-content-container">
                {steps[activeStep]?.content}
              </div>

            </div>
          )}
        </div>

        <div className="dialog-footer">
          {!isDelegated && (
            <>
              {/* Back button for steps 1 only */}
              {activeStep === 1 && (
                <button 
                  className="btn btn-secondary"
                  onClick={() => setActiveStep(activeStep - 1)}
                >
                  Back
                </button>
              )}
              
              {/* Continue button for step 0 */}
              {activeStep === 0 && (
                <button 
                  className="btn btn-primary"
                  onClick={() => setActiveStep(activeStep + 1)}
                >
                  Continue
                </button>
              )}
              
              {/* Approve Delegation button for step 1 */}
              {activeStep === 1 && (
                <button
                  className="btn btn-primary"
                  onClick={handleDelegate}
                  disabled={!hasWallet || isDelegatingLocal}
                >
                  {isDelegatingLocal ? (
                    <>
                      <div className="spinner-small"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      🛡️ Approve Delegation
                    </>
                  )}
                </button>
              )}
              
              {/* No buttons for step 2 (transaction confirming) */}
              
              {/* Done button for step 3 */}
              {activeStep === 3 && (
                <button 
                  className="btn btn-primary"
                  onClick={handleClose}
                >
                  Done
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default DelegationDialog;