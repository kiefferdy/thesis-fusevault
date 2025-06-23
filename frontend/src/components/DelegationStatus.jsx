import React from 'react';
import { useDelegation } from '../hooks/useDelegation';
import './DelegationStatus.css';

/**
 * Simple delegation status component to show in API Keys page
 * Shows current delegation status and provides setup button if needed
 */
const DelegationStatus = ({ onSetupClick, className = '' }) => {
  const { 
    isDelegated, 
    isLoading, 
    serverInfo,
    error,
    hasWallet 
  } = useDelegation();

  // Don't render while loading
  if (isLoading) {
    return (
      <div className={`delegation-status loading ${className}`}>
        <div className="status-content">
          <div className="spinner"></div>
          <span>Checking delegation status...</span>
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className={`delegation-status error ${className}`}>
        <div className="status-content">
          <div className="status-icon">⚠️</div>
          <div className="status-text">
            <h3>Delegation Status Error</h3>
            <p>Unable to check delegation status. Please try again.</p>
          </div>
        </div>
      </div>
    );
  }

  // Show wallet connection required
  if (!hasWallet) {
    return (
      <div className={`delegation-status warning ${className}`}>
        <div className="status-content">
          <div className="status-icon">🔗</div>
          <div className="status-text">
            <h3>Wallet Connection Required</h3>
            <p>Please connect your wallet to check delegation status.</p>
          </div>
        </div>
      </div>
    );
  }

  // Show delegation active status
  if (isDelegated) {
    return (
      <div className={`delegation-status success ${className}`}>
        <div className="status-content">
          <div className="status-icon">🛡️</div>
          <div className="status-text">
            <h3>Delegation Active</h3>
            <p>
              Server wallet is delegated. Your API keys can perform operations.
            </p>
            {serverInfo?.server_wallet_address && (
              <div className="server-info">
                <small>
                  Delegated to: {serverInfo.server_wallet_address.slice(0, 6)}...{serverInfo.server_wallet_address.slice(-4)}
                </small>
              </div>
            )}
          </div>
          {onSetupClick && (
            <button 
              className="btn btn-secondary btn-sm"
              onClick={onSetupClick}
              title="Manage delegation settings"
            >
              Manage
            </button>
          )}
        </div>
      </div>
    );
  }

  // Show delegation required status
  return (
    <div className={`delegation-status warning ${className}`}>
      <div className="status-content">
        <div className="status-icon">⚠️</div>
        <div className="status-text">
          <h3>Delegation Required</h3>
          <p>
            To use API keys, you must first delegate permission to the server wallet.
          </p>
          <div className="delegation-benefits">
            <small>
              • You maintain full ownership • Server cannot transfer assets • Revocable anytime
            </small>
          </div>
        </div>
        {onSetupClick && (
          <button 
            className="btn btn-primary btn-sm"
            onClick={onSetupClick}
          >
            Setup Now
          </button>
        )}
      </div>
    </div>
  );
};

export default DelegationStatus;