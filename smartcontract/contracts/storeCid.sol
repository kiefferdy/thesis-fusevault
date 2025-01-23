// SPDX-License-Identifier: MIT
pragma solidity ^0.8.21;

contract CIDStorage {
    // Struct to hold CID data with a 32-byte SHA-256 digest
    struct CIDRecord {
        bytes32 digestHash;  // Store the 32-byte SHA-256 digest hash
        uint256 timestamp;   // Optional: To track when it was added
    }

    // Mapping to associate a unique record identifier (e.g., address) with its CID digest hash
    mapping(address => CIDRecord[]) private addressToCIDs;

    // Event to emit when a new CID digest hash is stored
    event CIDStored(address indexed user, bytes32 digestHash, uint256 timestamp);

    /**
     * @dev Store a CID digest hash associated with the caller's address
     * @param cid The Content Identifier (CID) to hash and store
     */
    function storeCIDDigest(string memory cid) public {
        require(bytes(cid).length > 0, "CID cannot be empty");

        // Compute the 32-byte SHA-256 digest of the CID
        bytes32 cidHash = sha256(bytes(cid));

        // Store the CID digest and its timestamp in the caller's record
        addressToCIDs[msg.sender].push(CIDRecord({digestHash: cidHash, timestamp: block.timestamp}));

        // Emit event with the stored digest hash
        emit CIDStored(msg.sender, cidHash, block.timestamp);
    }

    /**
     * @dev Fetch all CID digest hashes associated with a specific address
     * @param user The address to query
     * @return digestHashes Array of CID digest hashes linked to the address
     */
    function fetchCIDsDigestByAddress(address user) public view returns (bytes32[] memory digestHashes) {
        CIDRecord[] memory records = addressToCIDs[user];
        digestHashes = new bytes32[](records.length);

        for (uint256 i = 0; i < records.length; i++) {
            digestHashes[i] = records[i].digestHash;
        }

        return digestHashes;
    }

    /**
     * @dev Fetch all CID digest hashes associated with the caller's address
     * @return digestHashes Array of CID digest hashes linked to the caller's address
     */
    function fetchMyCIDsDigest() public view returns (bytes32[] memory digestHashes) {
        return fetchCIDsDigestByAddress(msg.sender);
    }

    /**
     * @dev Get the total number of CID digest hashes associated with an address
     * @param user The address to query
     * @return count The number of CID digest hashes
     */
    function getCIDDigestCountByAddress(address user) public view returns (uint256 count) {
        return addressToCIDs[user].length;
    }
}