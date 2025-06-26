// SPDX-License-Identifier: MIT
pragma solidity ^0.8.21;

/**
 * @title FuseVaultRegistry
 * @dev Comprehensive asset management contract for the FuseVault platform
 * Handles IPFS metadata versioning, ownership, delegation, transfers, and batch operations
 */
contract FuseVaultRegistry {
    // Struct optimized to efficiently use storage slots
    struct AssetIPFS {
        // Slot 1 (32 bytes)
        bytes32 cidHash;          // Hash of the IPFS CID (32 bytes)
        
        // Slot 2 (32 bytes)
        uint32 ipfsVersion;       // Version number for critical metadata updates (4 bytes)
        uint64 lastUpdated;       // Timestamp of last update (8 bytes)
        uint64 createdAt;         // Timestamp of creation (8 bytes)
        bool isDeleted;           // Whether the asset is deleted (1 byte)
        // 11 bytes remaining in this slot for future use
    }

    // Owner -> Asset ID hash -> IPFS info
    mapping(address => mapping(bytes32 => AssetIPFS)) private assetIPFSVersions;
    
    // Owner -> Delegate -> Is authorized
    mapping(address => mapping(address => bool)) public delegates;
    
    // Admin mappings
    mapping(address => bool) public admins;
    
    // Mapping for pending transfers
    mapping(address => mapping(bytes32 => address)) public pendingTransfers;
    
    // Batch operation constants
    uint256 public constant MAX_BATCH_SIZE = 50; // Conservative limit for gas efficiency
    
    // Events
    event IPFSUpdated(
        address indexed owner,
        string indexed assetId,
        uint32 ipfsVersion,
        string cid,
        bool isDeleted
    );
    
    event BatchIPFSUpdated(
        address indexed owner,
        uint256 assetCount,
        uint256 timestamp
    );
    
    event AdminStatusChanged(address indexed account, bool isAdmin);
    event DelegateStatusChanged(address indexed owner, address indexed delegate, bool status);
    event AssetDeleted(address indexed owner, string indexed assetId, uint32 lastVersion);
    event BatchAssetsDeleted(address indexed owner, uint256 assetCount, uint256 timestamp);
    event TransferInitiated(address indexed from, address indexed to, string indexed assetId);
    event TransferCompleted(address indexed from, address indexed to, string indexed assetId);
    event TransferCancelled(address indexed from, address indexed to, string indexed assetId);

    // Constructor to set initial admin
    constructor() {
        admins[msg.sender] = true;
        emit AdminStatusChanged(msg.sender, true);
    }

    // Modifiers
    modifier onlyAdmin() {
        require(admins[msg.sender], "Only admins can call this function");
        _;
    }
    
    modifier canModifyAsset(address _owner, bytes32 _assetIdHash) {
        bool isAuthorized = 
            msg.sender == _owner || 
            admins[msg.sender] || 
            delegates[_owner][msg.sender];
            
        require(isAuthorized, "Not authorized to modify this asset");
        _;
    }

    /**
     * @dev Hash an asset ID to bytes32 for storage efficiency
     */
    function hashAssetId(string memory _assetId) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(_assetId));
    }

    /**
     * @dev Updates critical metadata for an asset
     */
    function updateIPFS(
        string calldata _assetId, 
        string calldata _cid
    ) public {
        updateIPFSFor(msg.sender, _assetId, _cid);
    }
    
    /**
     * @dev Updates critical metadata for an asset on behalf of another owner
     */
    function updateIPFSFor(
        address _owner,
        string calldata _assetId, 
        string calldata _cid
    ) public {
        // Check authorization
        require(
            msg.sender == _owner || 
            admins[msg.sender] || 
            delegates[_owner][msg.sender],
            "Not authorized to modify this asset"
        );
        
        _updateIPFSInternal(_owner, _assetId, _cid);
    }

    /**
     * @dev Updates critical metadata for multiple assets in a single transaction
     * @param _assetIds Array of asset IDs to update
     * @param _cids Array of IPFS CIDs corresponding to each asset
     */
    function batchUpdateIPFS(
        string[] calldata _assetIds, 
        string[] calldata _cids
    ) public {
        require(_assetIds.length == _cids.length, "Arrays must have same length");
        require(_assetIds.length > 0, "Must provide at least one asset");
        require(_assetIds.length <= MAX_BATCH_SIZE, "Batch size limit exceeded");
        
        for (uint256 i = 0; i < _assetIds.length; i++) {
            // Reuse existing logic via internal function call
            _updateIPFSInternal(msg.sender, _assetIds[i], _cids[i]);
        }
        
        emit BatchIPFSUpdated(msg.sender, _assetIds.length, block.timestamp);
    }

    /**
     * @dev Updates critical metadata for multiple assets on behalf of another owner
     * @param _owner The owner of the assets
     * @param _assetIds Array of asset IDs to update
     * @param _cids Array of IPFS CIDs corresponding to each asset
     */
    function batchUpdateIPFSFor(
        address _owner,
        string[] calldata _assetIds, 
        string[] calldata _cids
    ) public {
        require(_assetIds.length == _cids.length, "Arrays must have same length");
        require(_assetIds.length > 0, "Must provide at least one asset");
        require(_assetIds.length <= MAX_BATCH_SIZE, "Batch size limit exceeded");
        
        // Check authorization for the entire batch
        require(
            msg.sender == _owner || 
            admins[msg.sender] || 
            delegates[_owner][msg.sender],
            "Not authorized to modify assets for this owner"
        );
        
        for (uint256 i = 0; i < _assetIds.length; i++) {
            // Reuse existing logic via internal function call
            _updateIPFSInternal(_owner, _assetIds[i], _cids[i]);
        }
        
        emit BatchIPFSUpdated(_owner, _assetIds.length, block.timestamp);
    }

    /**
     * @dev Internal function to avoid code duplication between single and batch operations
     */
    function _updateIPFSInternal(
        address _owner,
        string memory _assetId,
        string memory _cid
    ) private {
        require(bytes(_assetId).length > 0, "Asset ID cannot be empty");
        require(bytes(_cid).length > 0, "CID cannot be empty");
        
        bytes32 assetIdHash = hashAssetId(_assetId);
        bytes32 cidHash = keccak256(abi.encodePacked(_cid));
        
        AssetIPFS storage assetIPFS = assetIPFSVersions[_owner][assetIdHash];
        
        if (assetIPFS.ipfsVersion == 0 || assetIPFS.isDeleted) {
            assetIPFS.ipfsVersion = 1;
            assetIPFS.createdAt = uint64(block.timestamp);
            assetIPFS.isDeleted = false;
        } else {
            assetIPFS.ipfsVersion += 1;
        }
        
        assetIPFS.cidHash = cidHash;
        assetIPFS.lastUpdated = uint64(block.timestamp);
        
        emit IPFSUpdated(_owner, _assetId, assetIPFS.ipfsVersion, _cid, false);
    }

    /**
     * @dev Delete multiple assets in a single transaction
     * @param _assetIds Array of asset IDs to delete
     */
    function batchDeleteAssets(string[] calldata _assetIds) public {
        require(_assetIds.length > 0, "Must provide at least one asset");
        require(_assetIds.length <= MAX_BATCH_SIZE, "Batch size limit exceeded");
        
        for (uint256 i = 0; i < _assetIds.length; i++) {
            deleteAsset(_assetIds[i]);
        }
        
        emit BatchAssetsDeleted(msg.sender, _assetIds.length, block.timestamp);
    }

    /**
     * @dev Delete multiple assets on behalf of another owner
     * @param _owner The owner of the assets
     * @param _assetIds Array of asset IDs to delete
     */
    function batchDeleteAssetsFor(address _owner, string[] calldata _assetIds) public {
        require(_assetIds.length > 0, "Must provide at least one asset");
        require(_assetIds.length <= MAX_BATCH_SIZE, "Batch size limit exceeded");
        
        // Check authorization for the entire batch
        require(
            msg.sender == _owner || 
            admins[msg.sender] || 
            delegates[_owner][msg.sender],
            "Not authorized to delete assets for this owner"
        );
        
        for (uint256 i = 0; i < _assetIds.length; i++) {
            deleteAssetFor(_owner, _assetIds[i]);
        }
        
        emit BatchAssetsDeleted(_owner, _assetIds.length, block.timestamp);
    }

    /**
     * @dev Delete an asset (mark as deleted)
     */
    function deleteAsset(string calldata _assetId) public {
        deleteAssetFor(msg.sender, _assetId);
    }
    
    /**
     * @dev Delete an asset on behalf of another owner
     */
    function deleteAssetFor(address _owner, string calldata _assetId) public {
        bytes32 assetIdHash = hashAssetId(_assetId);
        
        // Check authorization
        require(
            msg.sender == _owner || 
            admins[msg.sender] || 
            delegates[_owner][msg.sender],
            "Not authorized to delete this asset"
        );
        
        // Get current IPFS info
        AssetIPFS storage assetIPFS = assetIPFSVersions[_owner][assetIdHash];
        
        // Ensure asset exists and is not already deleted
        require(assetIPFS.ipfsVersion > 0, "Asset does not exist");
        require(!assetIPFS.isDeleted, "Asset already deleted");
        
        // Mark as deleted
        assetIPFS.isDeleted = true;
        assetIPFS.lastUpdated = uint64(block.timestamp);
        
        // Emit events
        emit AssetDeleted(_owner, _assetId, assetIPFS.ipfsVersion);
    }

    /**
     * @dev Get the IPFS version information for an asset
     */
    function getIPFSInfo(string calldata _assetId, address _owner) public view returns (
        uint32 ipfsVersion,
        bytes32 cidHash,
        uint64 lastUpdated,
        uint64 createdAt,
        bool isDeleted
    ) {
        bytes32 assetIdHash = hashAssetId(_assetId);
        AssetIPFS storage assetIPFS = assetIPFSVersions[_owner][assetIdHash];
        
        require(assetIPFS.ipfsVersion > 0, "Asset does not exist");
        
        return (
            assetIPFS.ipfsVersion,
            assetIPFS.cidHash,
            assetIPFS.lastUpdated,
            assetIPFS.createdAt,
            assetIPFS.isDeleted
        );
    }

    /**
     * @dev Verify if a given CID is valid for an asset
     */
    function verifyCID(
        string calldata _assetId, 
        address _owner,
        string calldata _cid,
        uint32 _claimedIpfsVersion
    ) public view returns (
        bool isValid,
        string memory message,
        uint32 actualIpfsVersion,
        bool isDeleted
    ) {
        bytes32 assetIdHash = hashAssetId(_assetId);
        AssetIPFS storage assetIPFS = assetIPFSVersions[_owner][assetIdHash];
        
        // Check if asset exists
        if (assetIPFS.ipfsVersion == 0) {
            return (false, "Asset does not exist", 0, false);
        }
        
        // Store actual version from blockchain for return value
        actualIpfsVersion = assetIPFS.ipfsVersion;
        isDeleted = assetIPFS.isDeleted;
        
        // If asset is deleted, return that information
        if (isDeleted) {
            return (false, "Asset is deleted", actualIpfsVersion, true);
        }
        
        // Check for version mismatch (prevents rollback attacks)
        if (_claimedIpfsVersion != assetIPFS.ipfsVersion) {
            return (false, "IPFS version mismatch - MongoDB record references outdated version", actualIpfsVersion, false);
        }
        
        // Check if CID matches
        bytes32 cidHash = keccak256(abi.encodePacked(_cid));
        if (cidHash != assetIPFS.cidHash) {
            return (false, "CID mismatch - Content does not match what's on blockchain", actualIpfsVersion, false);
        }
        
        return (true, "Valid CID matches blockchain record", actualIpfsVersion, false);
    }

    /**
     * @dev Check if an asset exists
     */
    function assetExists(string calldata _assetId, address _owner) public view returns (bool exists, bool isDeleted) {
        bytes32 assetIdHash = hashAssetId(_assetId);
        AssetIPFS storage assetIPFS = assetIPFSVersions[_owner][assetIdHash];
        
        exists = assetIPFS.ipfsVersion > 0;
        isDeleted = assetIPFS.isDeleted;
        
        return (exists, isDeleted);
    }
    
    /**
     * @dev Set or remove an admin
     */
    function setAdmin(address _account, bool _isAdmin) public onlyAdmin {
        admins[_account] = _isAdmin;
        emit AdminStatusChanged(_account, _isAdmin);
    }
    
    /**
     * @dev Set or remove a delegate who can act on behalf of the caller
     */
    function setDelegate(address _delegate, bool _status) public {
        delegates[msg.sender][_delegate] = _status;
        emit DelegateStatusChanged(msg.sender, _delegate, _status);
    }
    
    /**
     * @dev Initiate transfer of an asset to a new owner
     * @param _assetId The asset identifier
     * @param _newOwner The address of the new owner
     */
    function initiateTransfer(string calldata _assetId, address _newOwner) public {
        require(_newOwner != address(0), "Cannot transfer to zero address");
        require(_newOwner != msg.sender, "Cannot transfer to self");
        
        bytes32 assetIdHash = hashAssetId(_assetId);
        
        // Check that sender owns the asset
        AssetIPFS storage assetIPFS = assetIPFSVersions[msg.sender][assetIdHash];
        require(assetIPFS.ipfsVersion > 0, "Asset does not exist or you don't own it");
        require(!assetIPFS.isDeleted, "Cannot transfer deleted asset");
        
        // Set pending transfer
        pendingTransfers[msg.sender][assetIdHash] = _newOwner;
        
        // Emit event
        emit TransferInitiated(msg.sender, _newOwner, _assetId);
    }
    
    /**
     * @dev Accept transfer of an asset from previous owner
     * @param _assetId The asset identifier
     * @param _previousOwner The address of the previous owner
     */
    function acceptTransfer(string calldata _assetId, address _previousOwner) public {
        bytes32 assetIdHash = hashAssetId(_assetId);
        
        // Check that transfer was initiated by previous owner to msg.sender
        require(pendingTransfers[_previousOwner][assetIdHash] == msg.sender, "No pending transfer to you");
        
        // Get the asset's data
        AssetIPFS storage sourceAssetIPFS = assetIPFSVersions[_previousOwner][assetIdHash];
        require(sourceAssetIPFS.ipfsVersion > 0, "Asset does not exist");
        require(!sourceAssetIPFS.isDeleted, "Cannot transfer deleted asset");
        
        // Create a copy of the asset data for the new owner
        AssetIPFS storage targetAssetIPFS = assetIPFSVersions[msg.sender][assetIdHash];
        
        // Copy all asset data to new owner
        targetAssetIPFS.ipfsVersion = sourceAssetIPFS.ipfsVersion;
        targetAssetIPFS.cidHash = sourceAssetIPFS.cidHash;
        targetAssetIPFS.lastUpdated = uint64(block.timestamp);
        targetAssetIPFS.createdAt = sourceAssetIPFS.createdAt;
        targetAssetIPFS.isDeleted = false;
        
        // Delete the asset from previous owner (mark as deleted)
        sourceAssetIPFS.isDeleted = true;
        sourceAssetIPFS.lastUpdated = uint64(block.timestamp);
        
        // Clear the pending transfer
        delete pendingTransfers[_previousOwner][assetIdHash];
        
        // Emit events
        emit TransferCompleted(_previousOwner, msg.sender, _assetId);
        emit AssetDeleted(_previousOwner, _assetId, sourceAssetIPFS.ipfsVersion);
    }
    
    /**
     * @dev Cancel a pending transfer
     * @param _assetId The asset identifier
     */
    function cancelTransfer(string calldata _assetId) public {
        bytes32 assetIdHash = hashAssetId(_assetId);
        
        // Check that there is a pending transfer
        address pendingRecipient = pendingTransfers[msg.sender][assetIdHash];
        require(pendingRecipient != address(0), "No pending transfer");
        
        // Clear the pending transfer
        delete pendingTransfers[msg.sender][assetIdHash];
        
        // Emit event
        emit TransferCancelled(msg.sender, pendingRecipient, _assetId);
    }
    
    /**
     * @dev Check if there's a pending transfer for an asset
     * @param _assetId The asset identifier
     * @param _owner The current owner
     * @return pendingTo The address the asset is pending transfer to, or zero address if none
     */
    function getPendingTransfer(string calldata _assetId, address _owner) public view returns (address pendingTo) {
        bytes32 assetIdHash = hashAssetId(_assetId);
        return pendingTransfers[_owner][assetIdHash];
    }
}