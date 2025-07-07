import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import delegationService from '../services/delegationService';
import { toast } from 'react-hot-toast';
import { 
  LocationOn, 
  Twitter, 
  LinkedIn, 
  GitHub,
  Security,
  Search,
  People,
  Assignment,
  Lock,
  Speed
} from '@mui/icons-material';
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
      
      // For delegated users, fetch asset summaries
      const delegatedUsers = delegatorsResult.delegations || [];
      const delegatedWithAssets = await Promise.all(
        delegatedUsers.map(async (delegator) => {
          try {
            const summaryResult = await delegationService.getDelegatedAssetsSummary(delegator.ownerAddress);
            return {
              ...delegator,
              assetCount: summaryResult.total_assets || 0,
              assetCategories: summaryResult.asset_categories || {},
              lastActivity: summaryResult.last_activity || null,
              totalSizeBytes: summaryResult.total_size_bytes || 0
            };
          } catch (error) {
            console.error(`Error fetching asset summary for ${delegator.ownerAddress}:`, error);
            return {
              ...delegator,
              assetCount: 0,
              assetCategories: {},
              lastActivity: null,
              totalSizeBytes: 0
            };
          }
        })
      );
      
      setDelegatedToMe(delegatedWithAssets);
      
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

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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
          <h1>User Delegation</h1>
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
            <Search className="tab-icon" /> Search Users
          </button>
          <button 
            className={`tab ${activeTab === 'delegates' ? 'active' : ''}`}
            onClick={() => setActiveTab('delegates')}
          >
            <People className="tab-icon" /> My Delegates
          </button>
          <button 
            className={`tab ${activeTab === 'delegated' ? 'active' : ''}`}
            onClick={() => setActiveTab('delegated')}
          >
            <Assignment className="tab-icon" /> Delegated to Me
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
                          <div className="user-header">
                            {user.profile_image && (
                              <img 
                                src={user.profile_image} 
                                alt={user.name || user.username}
                                className="user-avatar"
                              />
                            )}
                            <div className="user-names">
                              <h4>{user.name || user.username}</h4>
                              {user.name && user.username && (
                                <span className="user-username">@{user.username}</span>
                              )}
                            </div>
                          </div>
                          <p className="user-address">{formatAddress(user.wallet_address)}</p>
                          
                          {(user.organization || user.job_title) && (
                            <div className="user-professional">
                              {user.job_title && user.organization ? (
                                <span className="job-org-combined">{user.job_title}, {user.organization}</span>
                              ) : user.job_title ? (
                                <span className="job-title">{user.job_title}</span>
                              ) : (
                                <span className="organization">{user.organization}</span>
                              )}
                            </div>
                          )}
                          
                          {user.location && (
                            <div className="user-location">
                              <LocationOn className="location-icon" />
                              {user.location}
                            </div>
                          )}
                          
                          {user.bio && <p className="user-bio">{user.bio}</p>}
                          
                          {(user.twitter || user.linkedin || user.github) && (
                            <div className="user-social">
                              {user.twitter && (
                                <a href={`https://twitter.com/${user.twitter}`} target="_blank" rel="noopener noreferrer" className="social-link-small">
                                  <Twitter className="social-icon-small" />
                                </a>
                              )}
                              {user.linkedin && (
                                <a href={user.linkedin} target="_blank" rel="noopener noreferrer" className="social-link-small">
                                  <LinkedIn className="social-icon-small" />
                                </a>
                              )}
                              {user.github && (
                                <a href={`https://github.com/${user.github}`} target="_blank" rel="noopener noreferrer" className="social-link-small">
                                  <GitHub className="social-icon-small" />
                                </a>
                              )}
                            </div>
                          )}
                          
                          {user.created_at && (
                            <div className="user-since">
                              Member since {new Date(user.created_at).toLocaleDateString()}
                            </div>
                          )}
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
                        <div className="delegate-header">
                          {delegate.delegateProfileImage && (
                            <img 
                              src={delegate.delegateProfileImage} 
                              alt={delegate.delegateName || delegate.delegateUsername}
                              className="delegate-avatar"
                            />
                          )}
                          <div className="delegate-names">
                            <h4>{delegate.delegateName || delegate.delegateUsername || 'Unknown User'}</h4>
                            {delegate.delegateName && delegate.delegateUsername && (
                              <span className="delegate-username">@{delegate.delegateUsername}</span>
                            )}
                          </div>
                        </div>
                        <p className="delegate-address">{formatAddress(delegate.delegateAddress)}</p>
                        
                        {(delegate.delegateOrganization || delegate.delegateJobTitle) && (
                          <div className="delegate-professional">
                            {delegate.delegateJobTitle && delegate.delegateOrganization ? (
                              <span className="job-org-combined">{delegate.delegateJobTitle}, {delegate.delegateOrganization}</span>
                            ) : delegate.delegateJobTitle ? (
                              <span className="job-title">{delegate.delegateJobTitle}</span>
                            ) : (
                              <span className="organization">{delegate.delegateOrganization}</span>
                            )}
                          </div>
                        )}
                        
                        {delegate.delegateLocation && (
                          <div className="delegate-location">
                            <LocationOn className="location-icon" />
                            {delegate.delegateLocation}
                          </div>
                        )}
                        
                        <div className="delegate-metadata">
                          <span className="delegate-status">Active</span>
                          <span className="delegate-date">
                            {delegate.createdAt ? 
                              `Delegated ${new Date(delegate.createdAt).toLocaleDateString()}` : 
                              'Recently delegated'
                            }
                          </span>
                          {delegate.delegateLastLogin && (
                            <span className="last-activity">
                              Last seen {new Date(delegate.delegateLastLogin).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                        
                        {(delegate.delegateTwitter || delegate.delegateLinkedin || delegate.delegateGithub) && (
                          <div className="delegate-social">
                            {delegate.delegateTwitter && (
                              <a href={`https://twitter.com/${delegate.delegateTwitter}`} target="_blank" rel="noopener noreferrer" className="social-link">
                                <Twitter className="social-icon" />
                                Twitter
                              </a>
                            )}
                            {delegate.delegateLinkedin && (
                              <a href={delegate.delegateLinkedin} target="_blank" rel="noopener noreferrer" className="social-link">
                                <LinkedIn className="social-icon" />
                                LinkedIn
                              </a>
                            )}
                            {delegate.delegateGithub && (
                              <a href={`https://github.com/${delegate.delegateGithub}`} target="_blank" rel="noopener noreferrer" className="social-link">
                                <GitHub className="social-icon" />
                                GitHub
                              </a>
                            )}
                          </div>
                        )}
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
                        <div className="delegated-header">
                          {delegator.ownerProfileImage && (
                            <img 
                              src={delegator.ownerProfileImage} 
                              alt={delegator.ownerName || delegator.ownerUsername}
                              className="delegated-avatar"
                            />
                          )}
                          <div className="delegated-names">
                            <h4>{delegator.ownerName || delegator.ownerUsername || 'Unknown User'}</h4>
                            {delegator.ownerName && delegator.ownerUsername && (
                              <span className="delegated-username">@{delegator.ownerUsername}</span>
                            )}
                          </div>
                        </div>
                        <p className="delegated-address">{formatAddress(delegator.ownerAddress)}</p>
                        
                        {(delegator.ownerOrganization || delegator.ownerJobTitle) && (
                          <div className="delegated-professional">
                            {delegator.ownerJobTitle && delegator.ownerOrganization ? (
                              <span className="job-org-combined">{delegator.ownerJobTitle}, {delegator.ownerOrganization}</span>
                            ) : delegator.ownerJobTitle ? (
                              <span className="job-title">{delegator.ownerJobTitle}</span>
                            ) : (
                              <span className="organization">{delegator.ownerOrganization}</span>
                            )}
                          </div>
                        )}
                        
                        {delegator.ownerLocation && (
                          <div className="delegated-location">
                            <LocationOn className="location-icon" />
                            {delegator.ownerLocation}
                          </div>
                        )}
                        
                        <div className="delegated-metadata">
                          <span className="delegation-received">
                            {delegator.createdAt ? 
                              `Delegated ${new Date(delegator.createdAt).toLocaleDateString()}` : 
                              'Recently received'
                            }
                          </span>
                          <span className="last-activity">
                            {delegator.lastActivity ? 
                              `Last activity: ${new Date(delegator.lastActivity).toLocaleDateString()}` : 
                              delegator.ownerLastLogin ? 
                              `Last seen ${new Date(delegator.ownerLastLogin).toLocaleDateString()}` :
                              'No recent activity'
                            }
                          </span>
                        </div>
                        
                        <div className="asset-summary">
                          <div className="asset-header">
                            <span className="asset-count-enhanced">
                              {delegator.assetCount || 0} total assets
                            </span>
                            {delegator.totalSizeBytes > 0 && (
                              <span className="storage-size">
                                {formatBytes(delegator.totalSizeBytes)}
                              </span>
                            )}
                          </div>
                          <div className="asset-breakdown">
                            {delegator.assetCategories && Object.keys(delegator.assetCategories).length > 0 ? (
                              Object.entries(delegator.assetCategories).map(([type, count]) => (
                                <span key={type} className="asset-type-badge">
                                  {count} {type}
                                </span>
                              ))
                            ) : (
                              <span className="asset-type-badge">Mixed content</span>
                            )}
                          </div>
                        </div>
                        
                        {(delegator.ownerTwitter || delegator.ownerLinkedin || delegator.ownerGithub) && (
                          <div className="delegated-social">
                            {delegator.ownerTwitter && (
                              <a href={`https://twitter.com/${delegator.ownerTwitter}`} target="_blank" rel="noopener noreferrer" className="social-link">
                                <Twitter className="social-icon" />
                                Twitter
                              </a>
                            )}
                            {delegator.ownerLinkedin && (
                              <a href={delegator.ownerLinkedin} target="_blank" rel="noopener noreferrer" className="social-link">
                                <LinkedIn className="social-icon" />
                                LinkedIn
                              </a>
                            )}
                            {delegator.ownerGithub && (
                              <a href={`https://github.com/${delegator.ownerGithub}`} target="_blank" rel="noopener noreferrer" className="social-link">
                                <GitHub className="social-icon" />
                                GitHub
                              </a>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="delegated-actions">
                        <button 
                          className="btn btn-primary"
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
              <h3><Lock className="info-icon" /> Security</h3>
              <p>
                Delegation allows trusted users to manage your assets without transferring ownership. 
                You maintain full control and can revoke delegation at any time.
              </p>
            </div>
            <div className="info-card">
              <h3><Speed className="info-icon" /> Convenience</h3>
              <p>
                Delegates can update, delete, and manage your assets on your behalf, 
                making collaboration and asset management more efficient.
              </p>
            </div>
            <div className="info-card">
              <h3><Security className="info-icon" /> Smart Contract</h3>
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