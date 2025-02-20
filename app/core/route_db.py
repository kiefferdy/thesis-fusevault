from datetime import datetime, timezone
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
import json
from app.core.mongodb_client import MongoDBClient
from app.core.version_control import VersionControl

# Set pymongo's logging level to WARNING to reduce verbosity
logging.getLogger('pymongo').setLevel(logging.WARNING)

# Set FastAPI logging level to WARNING
logging.basicConfig(level=logging.WARNING)

router = APIRouter(prefix="/db", tags=["mongodb"])

# Initialize MongoDB client and version control
db_client = MongoDBClient()
version_control = VersionControl(db_client)

@router.post("/upload")
async def upload_json_file(json_text: str):
    """Upload and process a JSON text file"""
    try:
        json_data = json.loads(json_text)
        
        # Extract required fields
        required_fields = [
            'asset_id', 
            'user_wallet_address', 
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
            user_wallet_address=json_data['user_wallet_address'],
            smart_contract_tx_id=json_data['smart_contract_tx_id'],
            ipfs_hash=json_data['ipfs_hash'],
            critical_metadata=json_data['critical_metadata'],
            non_critical_metadata=json_data['non_critical_metadata']
        )
        
        return {
            "status": "success",
            "message": "File uploaded and stored successfully",
            "document_id": doc_id
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/")
async def create_document(
    asset_id: str,
    user_wallet_address: str,
    smart_contract_tx_id: str,
    ipfs_hash: str,
    critical_metadata: Dict[str, Any],
    non_critical_metadata: Optional[Dict[str, Any]] = None
):
    """Create a new document in MongoDB"""
    try:
        doc_id = db_client.insert_document(
            asset_id=asset_id,
            user_wallet_address=user_wallet_address,
            smart_contract_tx_id=smart_contract_tx_id,
            ipfs_hash=ipfs_hash,
            critical_metadata=critical_metadata,
            non_critical_metadata=non_critical_metadata
        )
        return {"status": "success", "document_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Retrieve a document by its ID"""
    try:
        document = db_client.get_document_by_id(document_id)
        return document
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/{document_id}/version")
async def create_new_version(
    document_id: str,
    smart_contract_tx_id: str,
    ipfs_hash: str,
    critical_metadata: Dict[str, Any],
    non_critical_metadata: Dict[str, Any],
    user_wallet_address: str
):
    """Create a new version of an existing document"""
    try:
        new_doc_id = await version_control.create_new_version(
            document_id=document_id,
            smart_contract_tx_id=smart_contract_tx_id,
            ipfs_hash=ipfs_hash,
            critical_metadata=critical_metadata,
            non_critical_metadata=non_critical_metadata,
            user_wallet_address=user_wallet_address
        )
        
        return {
            "status": "success",
            "message": "New version created successfully",
            "new_document_id": new_doc_id,
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
        versions = await version_control.get_version_history(asset_id)
        return {
            "asset_id": asset_id,
            "version_count": len(versions),
            "versions": versions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/asset/{asset_id}/version/{version_number}")
async def get_specific_version(asset_id: str, version_number: int):
    """Get a specific version of a document"""
    try:
        version = await version_control.get_specific_version(
            asset_id,
            version_number
        )
        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_number} not found for asset {asset_id}"
            )
        return version
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
        differences = await version_control.compare_versions(
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

# Keep existing routes...
@router.get("/documents/wallet/{wallet_address}")
async def get_documents_by_wallet(wallet_address: str):
    """Retrieve all documents associated with a wallet address"""
    try:
        documents = db_client.get_documents_by_wallet(wallet_address)
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{document_id}")
async def update_document(
    document_id: str,
    smart_contract_tx_id: str,
    ipfs_hash: str,
    critical_metadata: Dict[str, Any],
    non_critical_metadata: Optional[Dict[str, Any]] = None
):
    """Update an existing document"""
    try:
        updated = db_client.update_document(
            document_id=document_id,
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

@router.post("/documents/{document_id}/verify")
async def verify_document(document_id: str):
    """Verify a document"""
    try:
        verified = db_client.verify_document(document_id)
        if not verified:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success", "message": "Document verified successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Soft delete a document"""
    try:
        # First get the document to obtain the wallet address
        document = db_client.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get the wallet address from the document
        wallet_address = document["userWalletAddress"]
        
        # Perform soft delete
        deleted = db_client.soft_delete(
            document_id=document_id,
            deleted_by=wallet_address
        )
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
            
        return {
            "status": "success", 
            "message": "Document marked as deleted",
            "document_id": document_id,
            "deletion_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))