from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
import datetime

from app.infrastructure.database import get_db
from app.infrastructure.models import AccountModel
from app.domain.entities import Account
from app.core.events import broadcaster
from app.core.security import get_current_admin, get_current_admin_cookie

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
    return templates.TemplateResponse(request, "index.html", {"accounts": accounts})

@router.post("/ui/accounts/create")
def ui_create_account(
    request: Request,
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
        exp_date_obj = datetime.datetime.utcnow() + datetime.timedelta(days=365)

    account = db.query(AccountModel).filter(AccountModel.account_id == account_id).first()
    created = False
    if not account:
        account = AccountModel(
            account_id=account_id,
            status=status,
            expiration_date=exp_date_obj,
            credits=credits,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        created = True
        broadcaster.publish("account_created", {
            "account_id": account.account_id,
            "status": account.status,
            "credits": account.credits,
            "expiration_date": account.expiration_date.isoformat(),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })

    if request.headers.get("HX-Request"):
        response = templates.TemplateResponse(
            request, "_account_row.html", {"acc": account}
        )
        if created:
            response.headers["HX-Trigger"] = "account-created"
        return response
    return RedirectResponse(url="/", status_code=303)

@router.post("/ui/accounts/{account_id}/recharge")
def ui_recharge_account(
    account_id: str,
    request: Request,
    amount: int = Form(...),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie),
):
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    account = db.query(AccountModel).filter(AccountModel.account_id == account_id).first()
    if account:
        account.credits += amount
        db.commit()
        db.refresh(account)
        broadcaster.publish("account_recharged", {
            "account_id": account.account_id,
            "credits": account.credits,
            "delta": amount,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })

    if request.headers.get("HX-Request") and account:
        return templates.TemplateResponse(
            request, "_account_row.html", {"acc": account}
        )
    return RedirectResponse(url="/", status_code=303)


def _render_event_html(event_name: str, data: dict) -> str | None:
    if event_name == "swipe":
        view = data
    elif event_name in ("account_created", "account_recharged"):
        view = {**data, "event_type": event_name}
    else:
        return None
    ts = view.get("timestamp", "")
    view["timestamp_short"] = ts[11:19] if len(ts) >= 19 else ""
    return templates.get_template("_event_item.html").render(e=view)


def _sse_format(event_name: str, html: str) -> str:
    lines = "\n".join(f"data: {line}" for line in html.splitlines())
    return f"event: {event_name}\n{lines}\n\n"


@router.get("/sse/events")
async def sse_events(admin: str = Depends(get_current_admin_cookie)):
    if not admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async def stream():
        async for payload in broadcaster.subscribe():
            name = payload["event"]
            if name == "ping":
                yield ": ping\n\n"
                continue
            if name == "ready":
                yield "event: ready\ndata: ok\n\n"
                continue
            html = _render_event_html(name, payload["data"])
            if html is None:
                continue
            yield _sse_format(name, html)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
