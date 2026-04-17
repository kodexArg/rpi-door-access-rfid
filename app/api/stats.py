import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.database import get_db
from app.infrastructure.models import AccessLogModel
from app.domain.entities import KPIStats
from app.core.security import get_current_admin_cookie
from app.core.time import utcnow

router = APIRouter()


def _count_window(db: Session, start: datetime.datetime, event_type: str | None = None) -> int:
    q = db.query(func.count(AccessLogModel.id)).filter(AccessLogModel.timestamp >= start)
    if event_type:
        q = q.filter(AccessLogModel.event_type == event_type)
    return q.scalar() or 0


def compute_kpi(db: Session) -> KPIStats:
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - datetime.timedelta(days=7)
    month_30_start = now - datetime.timedelta(days=30)
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return KPIStats(
        today_total=_count_window(db, today_start),
        today_grant=_count_window(db, today_start, "grant"),
        today_deny=_count_window(db, today_start, "deny"),
        last_7_days_total=_count_window(db, week_start),
        last_7_days_grant=_count_window(db, week_start, "grant"),
        last_7_days_deny=_count_window(db, week_start, "deny"),
        last_30_days_total=_count_window(db, month_30_start),
        last_30_days_grant=_count_window(db, month_30_start, "grant"),
        last_30_days_deny=_count_window(db, month_30_start, "deny"),
        this_month_total=_count_window(db, this_month_start),
        this_month_grant=_count_window(db, this_month_start, "grant"),
        this_month_deny=_count_window(db, this_month_start, "deny"),
    )


@router.get("/api/stats/kpi", response_model=KPIStats)
def get_kpi_stats(
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_cookie),
):
    if not admin:
        raise HTTPException(status_code=401)
    return compute_kpi(db)
