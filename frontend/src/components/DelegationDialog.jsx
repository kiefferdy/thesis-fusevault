import React, { useState, useEffect } from 'react';
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
  
  const {
    serverInfo,
    isDelegated,
    delegate,
    revoke,
    isDelegating,
    refreshStatus,
    getDelegationInfo,
    hasWallet,
    error
  } = useDelegation();

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
    try {
      await delegate();
      await refreshStatus();
      setActiveStep(2); // Move to success step
    } catch (error) {
      console.error('Delegation failed:', error);
      // Error handling is done in the hook
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

            <div className="action-buttons">
              <button
                className="btn btn-primary btn-large"
                onClick={handleDelegate}
                disabled={isDelegating || isDelegated || !hasWallet}
              >
                {isDelegating ? (
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
              {!hasWallet && (
                <p className="wallet-warning">Please connect your wallet first</p>
              )}
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
                      {delegationInfo.canUpdate && <span className="permission-badge">Update</span>}
                      {delegationInfo.canDelete && <span className="permission-badge">Delete</span>}
                    </div>
                  </div>
                </div>
              )}

              <div className="management-actions">
                <button 
                  className="btn btn-danger"
                  onClick={handleRevoke}
                  disabled={isDelegating}
                >
                  {isDelegating ? (
                    <>
                      <div className="spinner-small"></div>
                      Revoking...
                    </>
                  ) : (
                    'Revoke Delegation'
                  )}
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

              <div className="step-navigation">
                {activeStep > 0 && activeStep < 2 && (
                  <button 
                    className="btn btn-secondary"
                    onClick={() => setActiveStep(activeStep - 1)}
                  >
                    Back
                  </button>
                )}
                {activeStep < 1 && (
                  <button 
                    className="btn btn-primary"
                    onClick={() => setActiveStep(activeStep + 1)}
                  >
                    Continue
                  </button>
                )}
                {activeStep === 2 && (
                  <button 
                    className="btn btn-primary"
                    onClick={handleClose}
                  >
                    Done
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="dialog-footer">
          <button className="btn btn-secondary" onClick={handleClose}>
            {isDelegated || activeStep === 2 ? 'Close' : 'Cancel'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DelegationDialog;