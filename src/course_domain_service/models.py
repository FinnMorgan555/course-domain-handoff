from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DomainState(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"


class CourseSiteRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    domain: str = Field(min_length=3)
    origin_hostname: str = Field(min_length=3)
    webhook_url: str


class CourseSite(BaseModel):
    tenant_id: str
    course_id: str
    domain: str
    zone_id: str
    state: DomainState


class LearnerDeadline(BaseModel):
    learner_id: str
    lesson_id: str
    due_at: datetime
    completed_at: datetime | None = None


class DeadlineStatus(StrEnum):
    COMPLETE = "complete"
    OPEN = "open"
    OVERDUE = "overdue"


class DeadlineRow(BaseModel):
    learner_id: str
    lesson_id: str
    due_at: datetime
    status: DeadlineStatus


class EducatorReport(BaseModel):
    course_id: str
    generated_at: datetime
    rows: list[DeadlineRow]
    overdue_count: int

