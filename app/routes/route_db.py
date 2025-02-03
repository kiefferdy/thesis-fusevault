import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from app.mongodb_client import MongoDBClient

# Set pymongo's logging level to WARNING to reduce verbosity
logging.getLogger('pymongo').setLevel(logging.WARNING)

# Set FastAPI logging level to WARNING
logging.basicConfig(level=logging.WARNING)

router = APIRouter(prefix="/db", tags=["mongodb"])

# Initialize MongoDB client
db_client = MongoDBClient()

@router.post("/documents/")
def create_document(
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
def get_document(document_id: str):
    """Retrieve a document by its ID"""
    try:
        document = db_client.get_document_by_id(document_id)
        return document
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/wallet/{wallet_address}")
def get_documents_by_wallet(wallet_address: str):
    """Retrieve all documents associated with a wallet address"""
    try:
        documents = db_client.get_documents_by_wallet(wallet_address)
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{document_id}")
def update_document(
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
def verify_document(document_id: str):
    """Verify a document"""
    try:
        verified = db_client.verify_document(document_id)
        if not verified:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success", "message": "Document verified successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
def delete_document(document_id: str):
    """Soft delete a document"""
    try:
        deleted = db_client.soft_delete(document_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success", "message": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
