from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
import datetime

from ..infrastructure.database import get_db
from ..infrastructure.models import AccountModel
from ..domain.entities import Account
from ..core.security import get_current_admin, get_current_admin_cookie

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# REST API

@router.get("/api/accounts", response_model=List[Account])
def read_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    accounts = db.query(AccountModel).offset(skip).limit(limit).all()
    return accounts

@router.post("/api/accounts", response_model=Account)
def create_account(account: Account, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    db_account = db.query(AccountModel).filter(AccountModel.account_id == account.account_id).first()
    if db_account:
        raise HTTPException(status_code=400, detail="Account already exists")
    new_account = AccountModel(
        account_id=account.account_id,
        status=account.status,
        expiration_date=account.expiration_date,
        credits=account.credits
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account

@router.put("/api/accounts/{account_id}/recharge")
def recharge_account(account_id: str, amount: int, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    db_account = db.query(AccountModel).filter(AccountModel.account_id == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    db_account.credits += amount
    db.commit()
    db.refresh(db_account)
    return {"status": "success", "new_credits": db_account.credits}

# Web UI Routes

@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db), admin: str = Depends(get_current_admin_cookie)):
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    accounts = db.query(AccountModel).all()
    return templates.TemplateResponse("index.html", {"request": request, "accounts": accounts})

@router.post("/ui/accounts/create")
def ui_create_account(
    account_id: str = Form(...),
    status: str = Form(...),
    expiration_date: str = Form(...),
    credits: int = Form(...),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie)
):
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    try:
        exp_date_obj = datetime.datetime.fromisoformat(expiration_date)
    except ValueError:
        exp_date_obj = datetime.datetime.utcnow() + datetime.timedelta(days=365) # fallback
        
    db_account = db.query(AccountModel).filter(AccountModel.account_id == account_id).first()
    if not db_account:
        new_account = AccountModel(
            account_id=account_id,
            status=status,
            expiration_date=exp_date_obj,
            credits=credits
        )
        db.add(new_account)
        db.commit()
        
    # Redirect back to index
    return RedirectResponse(url="/", status_code=303)

@router.post("/ui/accounts/{account_id}/recharge")
def ui_recharge_account(account_id: str, amount: int = Form(...), db: Session = Depends(get_db), admin: str = Depends(get_current_admin_cookie)):
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    db_account = db.query(AccountModel).filter(AccountModel.account_id == account_id).first()
    if db_account:
        db_account.credits += amount
        db.commit()
    
    return RedirectResponse(url="/", status_code=303)
