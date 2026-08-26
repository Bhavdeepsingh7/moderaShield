"""Tenant-scoped, database-backed moderation metrics."""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select, true
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_tenant
from app.dependencies.database import get_db
from app.models.moderation import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.models.tenant import Tenant
from app.schemas.metrics import (
    CategoryMetricsResponse,
    OverviewMetricsResponse,
    RecentRequestItem,
    RecentRequestsResponse,
    StatusBreakdownResponse,
    UsageDay,
    UsageMetricsResponse,
)


router = APIRouter()
METRIC_STATUSES = ("approved", "flagged", "failed")


@router.get(
    "/overview",
    response_model=OverviewMetricsResponse,
    summary="Get moderation overview metrics",
)
def get_overview(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> OverviewMetricsResponse:
    row = db.execute(
        select(
            func.count(ModerationRequest.id).label("total"),
            func.coalesce(func.sum(case((ModerationRequest.status == "approved", 1), else_=0)), 0).label("approved"),
            func.coalesce(func.sum(case((ModerationRequest.status == "flagged", 1), else_=0)), 0).label("flagged"),
            func.coalesce(func.sum(case((ModerationRequest.status == "failed", 1), else_=0)), 0).label("failed"),
        ).where(ModerationRequest.tenant_id == tenant.id)
    ).one()
    total = int(row.total)
    flagged = int(row.flagged)
    return OverviewMetricsResponse(
        total_requests=total,
        approved_requests=int(row.approved),
        flagged_requests=flagged,
        failed_requests=int(row.failed),
        flag_rate=(flagged / total) if total else 0.0,
    )


@router.get(
    "/breakdown",
    response_model=StatusBreakdownResponse,
    summary="Get counts by stored moderation request status",
)
def get_breakdown(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> StatusBreakdownResponse:
    rows = db.execute(
        select(ModerationRequest.status, func.count(ModerationRequest.id))
        .where(ModerationRequest.tenant_id == tenant.id)
        .group_by(ModerationRequest.status)
    ).all()
    return StatusBreakdownResponse(statuses={status: int(count) for status, count in rows})


@router.get(
    "/categories",
    response_model=CategoryMetricsResponse,
    summary="Get counts of stored text moderation categories",
)
def get_categories(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CategoryMetricsResponse:
    # PostgreSQL production uses JSONB; SQLite support keeps database-backed
    # tests portable without materializing result rows in Python.
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        category_rows = func.jsonb_array_elements_text(ModerationResult.category).table_valued("value").alias("category_rows")
    else:
        category_rows = func.json_each(ModerationResult.category).table_valued("key", "value").alias("category_rows")

    rows = db.execute(
        select(category_rows.c.value, func.count())
        .select_from(ModerationResult)
        .join(ModerationRequest, ModerationRequest.id == ModerationResult.request_id)
        .join(category_rows, true())
        .where(ModerationRequest.tenant_id == tenant.id)
        .group_by(category_rows.c.value)
    ).all()
    return CategoryMetricsResponse(categories={category: int(count) for category, count in rows})


@router.get(
    "/usage",
    response_model=UsageMetricsResponse,
    summary="Get daily request counts in UTC",
)
def get_usage(
    days: int = Query(default=7, ge=1, le=90, description="Number of UTC calendar days, including today"),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> UsageMetricsResponse:
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        day_expression = func.date_trunc("day", ModerationRequest.created_at)
    else:
        day_expression = func.date(ModerationRequest.created_at)

    rows = db.execute(
        select(
            day_expression.label("day"),
            func.count(ModerationRequest.id).label("requests"),
            func.coalesce(func.sum(case((ModerationRequest.status == "approved", 1), else_=0)), 0).label("approved"),
            func.coalesce(func.sum(case((ModerationRequest.status == "flagged", 1), else_=0)), 0).label("flagged"),
            func.coalesce(func.sum(case((ModerationRequest.status == "failed", 1), else_=0)), 0).label("failed"),
        )
        .where(ModerationRequest.tenant_id == tenant.id, ModerationRequest.created_at >= start)
        .group_by(day_expression)
        .order_by(day_expression)
    ).all()

    by_day = {}
    for row in rows:
        row_day = row.day.date() if isinstance(row.day, datetime) else date.fromisoformat(str(row.day))
        by_day[row_day] = row
    return UsageMetricsResponse(days=[
        UsageDay(
            date=current_day,
            requests=int(by_day[current_day].requests) if current_day in by_day else 0,
            approved=int(by_day[current_day].approved) if current_day in by_day else 0,
            flagged=int(by_day[current_day].flagged) if current_day in by_day else 0,
            failed=int(by_day[current_day].failed) if current_day in by_day else 0,
        )
        for current_day in (start_date + timedelta(offset) for offset in range(days))
    ])


@router.get(
    "/requests",
    response_model=RecentRequestsResponse,
    summary="Get paginated recent moderation requests without source content",
)
def get_recent_requests(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> RecentRequestsResponse:
    base_query = select(ModerationRequest).where(ModerationRequest.tenant_id == tenant.id)
    total = int(db.scalar(select(func.count()).select_from(base_query.subquery())) or 0)
    rows = db.execute(
        select(ModerationRequest, ModerationResult)
        .outerjoin(ModerationResult, ModerationResult.request_id == ModerationRequest.id)
        .where(ModerationRequest.tenant_id == tenant.id)
        .order_by(ModerationRequest.created_at.desc(), ModerationRequest.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return RecentRequestsResponse(
        items=[
            RecentRequestItem(
                id=request.id,
                content_type=request.content_type,
                status=request.status,
                is_flagged=result.is_flagged if result else None,
                categories=result.category if result else [],
                model=result.model if result else None,
                created_at=request.created_at,
                updated_at=request.updated_at,
            )
            for request, result in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
