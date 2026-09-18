import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request

from .course_delivery import build_educator_report
from .infrai_client import InfraiClient, InfraiError
from .models import (
    CourseSite,
    CourseSiteRequest,
    DomainState,
    EducatorReport,
    LearnerDeadline,
)
from .webhook_security import valid_signature

app = FastAPI(title="Course domain handoff")
sites: dict[str, CourseSite] = {}
deadlines: dict[str, list[LearnerDeadline]] = {}


def _api_key() -> str:
    value = os.environ.get("INFRAI_API_KEY")
    if not value:
        raise RuntimeError("Set INFRAI_API_KEY before starting the service")
    return value


def _webhook_secret() -> str:
    value = os.environ.get("INFRAI_WEBHOOK_SECRET")
    if not value:
        raise RuntimeError("Set INFRAI_WEBHOOK_SECRET before starting the service")
    return value


@app.post("/course-sites", response_model=CourseSite, status_code=201)
async def create_course_site(request: CourseSiteRequest) -> CourseSite:
    request_id = str(uuid4())
    client = InfraiClient(_api_key())
    try:
        domain_data = await client.add_domain(
            request.domain, request.tenant_id, request_id
        )
        zone_id = domain_data["zone_id"]
        await client.upsert_cname(zone_id, request.origin_hostname, request_id)
        await client.register_webhook(
            request.webhook_url, _webhook_secret(), request_id
        )
    except InfraiError as exc:
        raise HTTPException(
            status_code=exc.status_code if 400 <= exc.status_code < 500 else 502,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    finally:
        await client.close()

    site = CourseSite(
        tenant_id=request.tenant_id,
        course_id=request.course_id,
        domain=request.domain,
        zone_id=zone_id,
        state=DomainState.PENDING,
    )
    sites[request.domain] = site
    return site


@app.post("/webhooks/infrai", status_code=204)
async def domain_verified(
    request: Request, x_infrai_signature: str = Header(alias="X-Infrai-Signature")
) -> None:
    body = await request.body()
    if not valid_signature(body, x_infrai_signature, _webhook_secret()):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    event = json.loads(body)
    if event.get("type") == "dns.domain.verified":
        domain = event["data"]["domain"]
        if domain in sites:
            sites[domain].state = DomainState.VERIFIED


@app.put("/courses/{course_id}/deadlines", status_code=204)
async def replace_deadlines(course_id: str, items: list[LearnerDeadline]) -> None:
    deadlines[course_id] = items


@app.get("/courses/{course_id}/educator-report", response_model=EducatorReport)
async def educator_report(course_id: str) -> EducatorReport:
    return build_educator_report(
        course_id, deadlines.get(course_id, []), datetime.now(timezone.utc)
    )
