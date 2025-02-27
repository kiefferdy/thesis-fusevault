from datetime import datetime, timezone
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List, Union
import json
from app.core.mongodb_client import MongoDBClient

# Set pymongo's logging level to WARNING to reduce verbosity
logging.getLogger('pymongo').setLevel(logging.WARNING)

# Set FastAPI logging level to WARNING
logging.basicConfig(level=logging.WARNING)

router = APIRouter(prefix="/db", tags=["mongodb"])

# Initialize MongoDB client
db_client = MongoDBClient()

@router.post("/upload")
async def upload_json_file(json_text: str):
    """Upload and process a JSON text file"""
    try:
        json_data = json.loads(json_text)
        
        # Extract required fields
        required_fields = [
            'asset_id', 
            'wallet_address',
            'smart_contract_tx_id',
            'ipfs_hash', 
            'critical_metadata',
            'non_critical_metadata'
        ]
        
        # Validate all required fields are present
        for field in required_fields:
            if field not in json_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Store in MongoDB
        doc_id = db_client.insert_document(
            asset_id=json_data['asset_id'],
            wallet_address=json_data['wallet_address'],
            smart_contract_tx_id=json_data['smart_contract_tx_id'],
            ipfs_hash=json_data['ipfs_hash'],
            critical_metadata=json_data['critical_metadata'],
            non_critical_metadata=json_data['non_critical_metadata']
        )
        
        return {
            "status": "success",
            "message": "File uploaded and stored successfully",
            "document_id": doc_id,
            "asset_id": json_data['asset_id'],
            "version": 1  # Initial version
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/")
async def create_document(
    asset_id: str,
    wallet_address: str,
    smart_contract_tx_id: str,
    ipfs_hash: str,
    critical_metadata: Dict[str, Any],
    non_critical_metadata: Optional[Dict[str, Any]] = None
):
    """Create a new document in MongoDB"""
    try:
        doc_id = db_client.insert_document(
            asset_id=asset_id,
            wallet_address=wallet_address,
            smart_contract_tx_id=smart_contract_tx_id,
            ipfs_hash=ipfs_hash,
            critical_metadata=critical_metadata,
            non_critical_metadata=non_critical_metadata
        )
        return {
            "status": "success", 
            "document_id": doc_id,
            "asset_id": asset_id,
            "version": 1  # Initial version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/asset/{asset_id}")
async def get_document(asset_id: str, version: Optional[int] = None):
    """
    Retrieve a document by its Asset ID and optionally its version.
    If version is not provided, returns the current version.
    """
    try:
        document = db_client.get_document_by_id(asset_id, version)
        return document
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/asset/{asset_id}/version")
async def create_new_version(
    asset_id: str,
    wallet_address: str,
    smart_contract_tx_id: str,
    ipfs_hash: str,
    critical_metadata: Dict[str, Any],
    non_critical_metadata: Dict[str, Any] = None
):
    """Create a new version of an existing document"""
    try:
        new_doc_id = db_client.create_new_version(
            asset_id=asset_id,
            wallet_address=wallet_address,
            smart_contract_tx_id=smart_contract_tx_id,
            ipfs_hash=ipfs_hash,
            critical_metadata=critical_metadata,
            non_critical_metadata=non_critical_metadata
        )
        
        # Get the new version number
        new_doc = db_client.get_document_by_id(asset_id)
        version_number = new_doc.get("versionNumber", 0)
        
        return {
            "status": "success",
            "message": "New version created successfully",
            "asset_id": asset_id,
            "new_document_id": new_doc_id,
            "version_number": version_number,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/asset/{asset_id}/versions")
async def get_version_history(asset_id: str):
    """Get complete version history for an asset"""
    try:
        versions = db_client.get_version_history(asset_id)
        return {
            "asset_id": asset_id,
            "version_count": len(versions),
            "versions": versions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/asset/{asset_id}/compare")
async def compare_versions(
    asset_id: str,
    version1: int,
    version2: int
):
    """Compare two versions of a document"""
    try:
        differences = db_client.compare_versions(
            asset_id,
            version1,
            version2
        )
        return {
            "asset_id": asset_id,
            "version1": version1,
            "version2": version2,
            "differences": differences
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/wallet/{wallet_address}")
async def get_documents_by_wallet(
    wallet_address: str, 
    include_all_versions: bool = False
):
    """
    Retrieve all documents associated with a wallet address.
    By default, only returns current versions unless include_all_versions is True.
    """
    try:
        documents = db_client.get_documents_by_wallet(
            wallet_address, 
            include_all_versions
        )
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/asset/{asset_id}")
async def update_document(
    asset_id: str,
    smart_contract_tx_id: str,
    ipfs_hash: str,
    critical_metadata: Dict[str, Any],
    non_critical_metadata: Optional[Dict[str, Any]] = None
):
    """Update the current version of an existing document"""
    try:
        updated = db_client.update_document(
            asset_id=asset_id,
            smart_contract_tx_id=smart_contract_tx_id,
            ipfs_hash=ipfs_hash,
            critical_metadata=critical_metadata,
            non_critical_metadata=non_critical_metadata
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success", "message": "Document updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/asset/{asset_id}/verify")
async def verify_document(asset_id: str):
    """Verify the current version of a document"""
    try:
        verified = db_client.verify_document(asset_id)
        if not verified:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success", "message": "Document verified successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/asset/{asset_id}")
async def delete_document(asset_id: str, wallet_address: str):
    """Soft delete the current version of a document"""
    try:
        deleted = db_client.soft_delete(
            asset_id=asset_id,
            deleted_by=wallet_address
        )
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
            
        return {
            "status": "success", 
            "message": "Document marked as deleted",
            "asset_id": asset_id,
            "deletion_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))