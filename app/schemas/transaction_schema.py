from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

class TransactionBase(BaseModel):
    asset_id: str
    action: str
    wallet_address: str
    metadata: Optional[Dict[str, Any]] = None

class TransactionResponse(TransactionBase):
    id: str
    timestamp: datetime

    class Config:
        orm_mode = True