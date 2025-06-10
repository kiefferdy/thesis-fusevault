import React from 'react';
import useApiKeysStatus from '../hooks/useApiKeysStatus';

/**
 * Debug component to test API Keys status
 * This can be temporarily added to any page for debugging
 */
const ApiKeysStatusDebug = () => {
  const { 
    status, 
    loading, 
    error, 
    lastChecked, 
    isEnabled, 
    isDisabled, 
    refresh 
  } = useApiKeysStatus();

  return (
    <div style={{
      position: 'fixed',
      top: '10px',
      right: '10px',
      background: 'white',
      border: '2px solid #ccc',
      borderRadius: '8px',
      padding: '10px',
      fontSize: '12px',
      fontFamily: 'monospace',
      maxWidth: '300px',
      zIndex: 9999,
      boxShadow: '0 2px 10px rgba(0,0,0,0.2)'
    }}>
      <h4 style={{ margin: '0 0 10px 0', fontSize: '14px' }}>
        🔧 API Keys Status Debug
      </h4>
      
      <div style={{ marginBottom: '5px' }}>
        <strong>Loading:</strong> {loading ? 'Yes' : 'No'}
      </div>
      
      <div style={{ marginBottom: '5px' }}>
        <strong>Enabled:</strong> {isEnabled ? '✅ Yes' : '❌ No'}
      </div>
      
      <div style={{ marginBottom: '5px' }}>
        <strong>Disabled:</strong> {isDisabled ? '🚫 Yes' : '✅ No'}
      </div>
      
      <div style={{ marginBottom: '5px' }}>
        <strong>Last Checked:</strong><br />
        {lastChecked ? lastChecked.toLocaleTimeString() : 'Never'}
      </div>
      
      <div style={{ marginBottom: '10px' }}>
        <strong>Raw Status:</strong><br />
        {JSON.stringify(status, null, 2)}
      </div>
      
      {error && (
        <div style={{ marginBottom: '10px', color: 'red' }}>
          <strong>Error:</strong><br />
          {error.message || error.toString()}
        </div>
      )}
      
      <button 
        onClick={refresh}
        disabled={loading}
        style={{
          background: '#007bff',
          color: 'white',
          border: 'none',
          padding: '5px 10px',
          borderRadius: '4px',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: '12px'
        }}
      >
        {loading ? 'Refreshing...' : 'Refresh Status'}
      </button>
      
      <div style={{ marginTop: '10px', fontSize: '10px', color: '#666' }}>
        This debug panel shows the real-time status of the API Keys feature.
        Remove this component in production.
      </div>
    </div>
  );
};

export default ApiKeysStatusDebug;
