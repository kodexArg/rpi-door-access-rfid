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

# --- Extended schemas ---

class AccountDetail(BaseModel):
    account_id: str
    status: str
    expiration_date: datetime.datetime
    credits: int
    user_id: Optional[int] = None

class UserDetail(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    accounts: List[AccountDetail] = []

class AccessLogDetail(BaseModel):
    id: int
    timestamp: datetime.datetime
    account_id: str
    event_type: str
    reason: Optional[str] = None
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    company_name: Optional[str] = None

class KPIStats(BaseModel):
    today_total: int
    today_grant: int
    today_deny: int
    last_7_days_total: int
    last_7_days_grant: int
    last_7_days_deny: int
    last_30_days_total: int
    last_30_days_grant: int
    last_30_days_deny: int
    this_month_total: int
    this_month_grant: int
    this_month_deny: int
