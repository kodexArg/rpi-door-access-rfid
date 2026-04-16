import datetime
from pydantic import BaseModel
from typing import Optional, List

class Company(BaseModel):
    id: Optional[int] = None
    name: str

class User(BaseModel):
    id: Optional[int] = None
    first_name: str
    last_name: str
    email: Optional[str] = None
    company_id: Optional[int] = None

class Account(BaseModel):
    account_id: str
    status: str
    expiration_date: datetime.datetime
    credits: int
    user_id: Optional[int] = None

class AccessLog(BaseModel):
    id: Optional[int] = None
    timestamp: datetime.datetime
    account_id: str
    event_type: str
    reason: Optional[str] = None
