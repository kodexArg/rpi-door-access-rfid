import datetime
from sqlalchemy import String, Integer, DateTime, Boolean, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional

class Base(DeclarativeBase):
    pass

class AccountModel(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="active") # "active" or "inactive"
    expiration_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    credits: Mapped[int] = mapped_column(Integer, default=0)

class AccessLogModel(Base):
    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    account_id: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String) # "grant" or "deny"
    reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
