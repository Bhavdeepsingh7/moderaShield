from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OverviewMetricsResponse(BaseModel):
    total_requests: int
    approved_requests: int
    flagged_requests: int
    failed_requests: int
    flag_rate: float


class StatusBreakdownResponse(BaseModel):
    statuses: dict[str, int]


class CategoryMetricsResponse(BaseModel):
    categories: dict[str, int]


class UsageDay(BaseModel):
    date: date
    requests: int
    approved: int
    flagged: int
    failed: int


class UsageMetricsResponse(BaseModel):
    days: list[UsageDay]


class RecentRequestItem(BaseModel):
    id: UUID
    content_type: str
    status: str
    is_flagged: bool | None = None
    categories: list[str] = Field(default_factory=list)
    model: str | None = None
    created_at: datetime
    updated_at: datetime


class RecentRequestsResponse(BaseModel):
    items: list[RecentRequestItem]
    total: int
    page: int
    page_size: int
