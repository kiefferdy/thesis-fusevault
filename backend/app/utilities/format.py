import json
from typing import Dict, Any, Union
from pydantic import BaseModel

def format_json(data: Any, encode: bool = True) -> Union[str, bytes]:
    """
    Formats data as JSON with consistent encoding for reliable CID generation.
    
    Args:
        data: The data to encode (can be any JSON-serializable object)
        encode: Whether to encode the result as UTF-8 bytes (default: True)
        
    Returns:
        str or bytes: The formatted JSON string or bytes
    """
    # Serialize with minimal separators (no extra spaces, no newlines)
    json_str = json.dumps(
        data,
        separators=(",", ":")
    )
    
    # Return bytes or string based on encode parameter
    return json_str.encode("utf-8") if encode else json_str

def get_ipfs_metadata(metadata: Union[Dict[str, Any], BaseModel]) -> Dict[str, Any]:
    """
    Extracts only the fields that go to IPFS (asset_id, wallet_address, critical_metadata)
    and sorts the keys for consistent ordering.
    
    Args:
        metadata: The input metadata (either a dict or a Pydantic model)
        
    Returns:
        Dict[str, Any]: Filtered metadata with only IPFS-relevant fields, with sorted keys
        
    Raises:
        ValueError: If any required fields are missing
    """
    # Convert to dict if it's a Pydantic model
    if isinstance(metadata, BaseModel):
        metadata = metadata.model_dump()
    
    # Check for required fields
    required_fields = ["asset_id", "wallet_address", "critical_metadata"]
    missing_fields = [field for field in required_fields if field not in metadata or metadata[field] is None]
    
    if missing_fields:
        missing_fields_str = ", ".join(missing_fields)
        raise ValueError(f"Missing required fields for IPFS metadata: {missing_fields_str}")
    
    # Extract only the fields that should go to IPFS
    ipfs_payload = {
        "asset_id": metadata["asset_id"],
        "wallet_address": metadata["wallet_address"],
        "critical_metadata": metadata["critical_metadata"]
    }
    
    # Sort keys to ensure consistent ordering
    # We'll convert to JSON with sorted keys and back to a dict to ensure deep sorting
    sorted_json = json.dumps(ipfs_payload, sort_keys=True)
    return json.loads(sorted_json)

def get_mongodb_metadata(metadata: Union[Dict[str, Any], BaseModel]) -> Dict[str, Any]:
    """
    Ensures the required MongoDB fields are present and sorts the metadata for consistency.
    
    Args:
        metadata: The input metadata (either a dict or a Pydantic model)
        
    Returns:
        Dict[str, Any]: Validated and sorted metadata for MongoDB
        
    Raises:
        ValueError: If any required fields are missing
    """
    # Convert to dict if it's a Pydantic model
    if isinstance(metadata, BaseModel):
        metadata = metadata.model_dump()
    
    # Check for required fields
    required_fields = [
        "asset_id", 
        "wallet_address", 
        "smart_contract_tx_id", 
        "ipfs_hash", 
        "critical_metadata", 
        "non_critical_metadata"
    ]
    missing_fields = [field for field in required_fields if field not in metadata or metadata[field] is None]
    
    if missing_fields:
        missing_fields_str = ", ".join(missing_fields)
        raise ValueError(f"Missing required fields for MongoDB metadata: {missing_fields_str}")
    
    # Ensure all required fields are included
    mongodb_payload = {
        "asset_id": metadata["asset_id"],
        "wallet_address": metadata["wallet_address"],
        "smart_contract_tx_id": metadata["smart_contract_tx_id"],
        "ipfs_hash": metadata["ipfs_hash"],
        "critical_metadata": metadata["critical_metadata"],
        "non_critical_metadata": metadata["non_critical_metadata"]
    }
    
    # Sort keys to ensure consistent ordering
    sorted_json = json.dumps(mongodb_payload, sort_keys=True)
    return json.loads(sorted_json)
