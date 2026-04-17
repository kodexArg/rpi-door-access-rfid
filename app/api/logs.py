import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.models import AuditLogModel
from app.core.security import get_current_admin_cookie

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PER_PAGE = 50

# Human-readable event type labels (Spanish)
EVENT_LABELS = {
    "rfid.grant":      "Acceso concedido",
    "rfid.deny":       "Acceso denegado",
    "user.created":    "Usuario creado",
    "user.deleted":    "Usuario eliminado",
    "company.created": "Empresa creada",
    "company.deleted": "Empresa eliminada",
    "card.created":    "Tarjeta creada",
    "card.edited":     "Tarjeta editada",
    "card.recharged":  "Créditos recargados",
    "card.unlinked":   "Tarjeta desvinculada",
    "batch.blanquear": "Blanqueo de tarjetas",
}

# Event type categories for UI grouping
EVENT_CATEGORIES = {
    "rfid":    ["rfid.grant", "rfid.deny"],
    "users":   ["user.created", "user.deleted"],
    "companies": ["company.created", "company.deleted"],
    "cards":   ["card.created", "card.edited", "card.recharged", "card.unlinked", "batch.blanquear"],
}


def _build_query(db: Session, event_type: str, actor: str, text: str, date_from: str, date_to: str):
    query = db.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc())

    if event_type and event_type != "all":
        if event_type in EVENT_CATEGORIES:
            query = query.filter(AuditLogModel.event_type.in_(EVENT_CATEGORIES[event_type]))
        else:
            query = query.filter(AuditLogModel.event_type == event_type)

    if actor and actor != "all":
        query = query.filter(AuditLogModel.actor == actor)

    if text.strip():
        pattern = f"%{text.strip()}%"
        query = query.filter(AuditLogModel.summary.ilike(pattern))

    if date_from.strip():
        try:
            dt = datetime.datetime.strptime(date_from.strip(), "%Y-%m-%d")
            query = query.filter(AuditLogModel.timestamp >= dt)
        except ValueError:
            pass

    if date_to.strip():
        try:
            dt = datetime.datetime.strptime(date_to.strip(), "%Y-%m-%d") + datetime.timedelta(days=1)
            query = query.filter(AuditLogModel.timestamp < dt)
        except ValueError:
            pass

    return query


@router.get("/ui/logs", response_class=HTMLResponse)
def ui_logs(
    request: Request,
    event_type: str = "all",
    actor: str = "all",
    text: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie),
):
    if not admin:
        raise HTTPException(status_code=401)

    query = _build_query(db, event_type, actor, text, date_from, date_to)
    total = query.count()
    rows = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    has_more = (page * PER_PAGE) < total
    filters = {
        "event_type": event_type,
        "actor": actor,
        "text": text,
        "date_from": date_from,
        "date_to": date_to,
    }

    context = {
        "logs": rows,
        "has_more": has_more,
        "next_page": page + 1,
        "total": total,
        "filters": filters,
        "event_labels": EVENT_LABELS,
        "event_categories": list(EVENT_CATEGORIES.keys()),
        "all_event_types": list(EVENT_LABELS.keys()),
    }

    is_htmx = request.headers.get("HX-Request")
    template = "_logs_table.html" if is_htmx else "_tab_logs.html"
    return templates.TemplateResponse(request, template, context)
