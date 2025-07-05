import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import delegationService from '../services/delegationService';
import { toast } from 'react-hot-toast';
import './DelegationPage.css';

const DelegationPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated, currentAccount } = useAuth();
  const [activeTab, setActiveTab] = useState('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [myDelegates, setMyDelegates] = useState([]);
  const [delegatedToMe, setDelegatedToMe] = useState([]);
  const [error, setError] = useState(null);

  // Mock data for now - will be replaced with actual API calls
  useEffect(() => {
    if (isAuthenticated) {
      // Load initial data
      loadDelegationData();
    }
  }, [isAuthenticated]);

  const loadDelegationData = async () => {
    try {
      setLoading(true);
      
      // Load delegates and delegators in parallel
      const [delegatesResult, delegatorsResult] = await Promise.all([
        delegationService.getMyDelegates(),
        delegationService.getDelegatedToMe()
      ]);
      
      setMyDelegates(delegatesResult.delegations || []);
      setDelegatedToMe(delegatorsResult.delegations || []);
      
    } catch (err) {
      setError('Failed to load delegation data');
      console.error('Error loading delegation data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const results = await delegationService.searchUsers(searchQuery);
      setSearchResults(results.users || []);
      
    } catch (err) {
      setError('Failed to search users');
      console.error('Error searching users:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelegate = async (user) => {
    try {
      setLoading(true);
      setError(null);
      
      toast.loading('Checking delegation status...', { id: 'delegation' });
      
      // Check if user is already delegated
      const delegationCheck = await delegationService.checkSpecificDelegation(
        currentAccount,
        user.wallet_address
      );
      
      if (delegationCheck.is_delegated) {
        toast.loading('Syncing delegation state...', { id: 'delegation' });
        
        // Sync blockchain state to database for consistency
        try {
          const syncResult = await delegationService.syncDelegationFromBlockchain(
            currentAccount,
            user.wallet_address
          );
          
          if (syncResult.was_synced) {
            toast.success(`${user.username} is already your delegate! Database synced.`, { id: 'delegation' });
            // Reload delegation data to show the synced delegation
            await loadDelegationData();
          } else {
            toast.success(`${user.username} is already your delegate!`, { id: 'delegation' });
          }
        } catch (syncError) {
          console.error('Failed to sync delegation:', syncError);
          toast.success(`${user.username} is already your delegate! (Sync failed but delegation works)`, { id: 'delegation' });
        }
        
        return;
      }
      
      toast.loading('Preparing delegation transaction...', { id: 'delegation' });
      
      // Prepare the delegation transaction
      const txData = await delegationService.prepareUserDelegationTransaction(
        user.wallet_address, 
        true // Enable delegation
      );
      
      // Execute the transaction using MetaMask
      await delegationService.executeDelegationTransaction(txData, (status) => {
        toast.loading(status, { id: 'delegation' });
      });
      
      toast.success(`Successfully delegated to ${user.username}!`, { id: 'delegation' });
      
      // Reload delegation data
      await loadDelegationData();
      
    } catch (err) {
      if (err.code === 4001) {
        toast.error('Transaction rejected by user', { id: 'delegation' });
      } else {
        toast.error('Failed to delegate to user', { id: 'delegation' });
      }
      console.error('Error delegating:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (delegateAddress) => {
    if (!window.confirm('Are you sure you want to revoke this delegation?')) {
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      toast.loading('Preparing revoke transaction...', { id: 'revoke' });
      
      // Prepare the revoke delegation transaction
      const txData = await delegationService.prepareRevokeDelegationTransaction(delegateAddress);
      
      // Execute the transaction using MetaMask
      await delegationService.executeDelegationTransaction(txData, (status) => {
        toast.loading(status, { id: 'revoke' });
      });
      
      toast.success('Successfully revoked delegation!', { id: 'revoke' });
      
      // Reload delegation data
      await loadDelegationData();
      
    } catch (err) {
      if (err.code === 4001) {
        toast.error('Transaction rejected by user', { id: 'revoke' });
      } else {
        toast.error('Failed to revoke delegation', { id: 'revoke' });
      }
      console.error('Error revoking delegation:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatAddress = (address) => {
    if (!address) return '';
    if (address.length < 10) return address;
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  if (!isAuthenticated) {
    return (
      <div className="delegation-page">
        <div className="container">
          <h1>User Delegation</h1>
          <p>Please connect your wallet to manage delegations.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="delegation-page">
      <div className="container">
        <div className="page-header">
          <h1>🛡️ User Delegation</h1>
          <p>Manage user delegations to allow others to manage your assets on your behalf.</p>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <div className="delegation-tabs">
          <button 
            className={`tab ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            🔍 Search Users
          </button>
          <button 
            className={`tab ${activeTab === 'delegates' ? 'active' : ''}`}
            onClick={() => setActiveTab('delegates')}
          >
            👥 My Delegates
          </button>
          <button 
            className={`tab ${activeTab === 'delegated' ? 'active' : ''}`}
            onClick={() => setActiveTab('delegated')}
          >
            📋 Delegated to Me
          </button>
        </div>

        <div className="tab-content">
          {activeTab === 'search' && (
            <div className="search-section">
              <h2>Find Users to Delegate</h2>
              <div className="search-form">
                <div className="search-input-group">
                  <input
                    type="text"
                    placeholder="Search by username or wallet address..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  />
                  <button 
                    onClick={handleSearch}
                    disabled={loading || !searchQuery.trim()}
                    className="btn btn-primary"
                  >
                    {loading ? 'Searching...' : 'Search'}
                  </button>
                </div>
              </div>

              {searchResults.length > 0 && (
                <div className="search-results">
                  <h3>Search Results</h3>
                  <div className="user-cards">
                    {searchResults.map((user) => (
                      <div key={user.id} className="user-card">
                        <div className="user-info">
                          <h4>{user.username}</h4>
                          <p className="user-address">{formatAddress(user.wallet_address)}</p>
                          {user.name && <p className="user-name">{user.name}</p>}
                          {user.bio && <p className="user-bio">{user.bio}</p>}
                        </div>
                        <div className="user-actions">
                          <button 
                            className="btn btn-primary"
                            onClick={() => handleDelegate(user)}
                            disabled={loading}
                          >
                            Delegate
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'delegates' && (
            <div className="delegates-section">
              <h2>Users I've Delegated To</h2>
              {myDelegates.length === 0 ? (
                <div className="empty-state">
                  <p>You haven't delegated to any users yet.</p>
                  <p>Use the "Search Users" tab to find users to delegate to.</p>
                </div>
              ) : (
                <div className="delegate-list">
                  {myDelegates.map((delegate) => (
                    <div key={delegate.delegateAddress} className="delegate-item">
                      <div className="delegate-info">
                        <h4>{delegate.delegateUsername || 'Unknown User'}</h4>
                        <p>{formatAddress(delegate.delegateAddress)}</p>
                        <span className="delegate-status">Active</span>
                      </div>
                      <div className="delegate-actions">
                        <button 
                          className="btn btn-danger"
                          onClick={() => handleRevoke(delegate.delegateAddress)}
                          disabled={loading}
                        >
                          Revoke
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'delegated' && (
            <div className="delegated-section">
              <h2>Users Who've Delegated to Me</h2>
              {delegatedToMe.length === 0 ? (
                <div className="empty-state">
                  <p>No users have delegated to you yet.</p>
                  <p>When users delegate to you, you'll be able to manage their assets here.</p>
                </div>
              ) : (
                <div className="delegated-list">
                  {delegatedToMe.map((delegator) => (
                    <div key={delegator.ownerAddress} className="delegated-item">
                      <div className="delegated-info">
                        <h4>{delegator.ownerUsername || 'Unknown User'}</h4>
                        <p>{formatAddress(delegator.ownerAddress)}</p>
                        <span className="asset-count">{delegator.assetCount || 0} assets</span>
                      </div>
                      <div className="delegated-actions">
                        <button 
                          className="btn btn-secondary"
                          onClick={() => {
                            navigate(`/delegation/manage/${delegator.ownerAddress}`);
                          }}
                        >
                          Manage Assets
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="delegation-info">
          <h2>About User Delegation</h2>
          <div className="info-grid">
            <div className="info-card">
              <h3>🔒 Security</h3>
              <p>
                Delegation allows trusted users to manage your assets without transferring ownership. 
                You maintain full control and can revoke delegation at any time.
              </p>
            </div>
            <div className="info-card">
              <h3>⚡ Convenience</h3>
              <p>
                Delegates can update, delete, and manage your assets on your behalf, 
                making collaboration and asset management more efficient.
              </p>
            </div>
            <div className="info-card">
              <h3>🛡️ Smart Contract</h3>
              <p>
                All delegation is managed through blockchain smart contracts, 
                ensuring transparency and immutable delegation records.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DelegationPage;