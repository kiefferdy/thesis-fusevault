// SPDX-License-Identifier: MIT
pragma solidity ^0.8.21;

/**
 * @title BaselineStorage
 * @dev Minimal IPFS + Ethereum storage for performance baseline testing
 * Stores only CID with minimal business logic for fair comparison
 */
contract BaselineStorage {
    
    // Simple mapping: asset_id -> IPFS CID
    mapping(string => string) private assetCIDs;
    
    // Event for CID storage
    event CIDStored(string indexed assetId, string cid, uint256 timestamp);
    event BatchCIDsStored(uint256 assetCount, uint256 timestamp);
    
    /**
     * @dev Store a single CID for an asset
     */
    function storeCID(string calldata _assetId, string calldata _cid) external {
        require(bytes(_assetId).length > 0, "Asset ID cannot be empty");
        require(bytes(_cid).length > 0, "CID cannot be empty");
        
        assetCIDs[_assetId] = _cid;
        emit CIDStored(_assetId, _cid, block.timestamp);
    }
    
    /**
     * @dev Store multiple CIDs in batch
     */
    function batchStoreCIDs(
        string[] calldata _assetIds, 
        string[] calldata _cids
    ) external {
        require(_assetIds.length == _cids.length, "Arrays must have same length");
        require(_assetIds.length > 0, "Must provide at least one asset");
        require(_assetIds.length <= 50, "Batch size limit exceeded");
        
        for (uint256 i = 0; i < _assetIds.length; i++) {
            require(bytes(_assetIds[i]).length > 0, "Asset ID cannot be empty");
            require(bytes(_cids[i]).length > 0, "CID cannot be empty");
            
            assetCIDs[_assetIds[i]] = _cids[i];
            emit CIDStored(_assetIds[i], _cids[i], block.timestamp);
        }
        
        emit BatchCIDsStored(_assetIds.length, block.timestamp);
    }
    
    /**
     * @dev Retrieve CID for an asset
     */
    function getCID(string calldata _assetId) external view returns (string memory) {
        return assetCIDs[_assetId];
    }
}