import datetime
from pydantic import BaseModel
from typing import Optional

class Account(BaseModel):
    account_id: str
    status: str
    expiration_date: datetime.datetime
    credits: int

class AccessLog(BaseModel):
    id: Optional[int] = None
    timestamp: datetime.datetime
    account_id: str
    event_type: str
    reason: Optional[str] = None
