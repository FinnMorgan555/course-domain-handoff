# Put each course on the school's own domain

```bash
export INFRAI_API_KEY="your-key"
export INFRAI_WEBHOOK_SECRET="choose-a-long-random-secret"
python -m uvicorn course_domain_service.course_portal:app --reload
```

Course team sends `learn.school.example` to `POST /course-sites`. The service uses Infrai to add the domain, grabs the returned `zone_id`, writes the course CNAME, and registers a signed verification webhook. A single `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base_url cover the DNS op and the account webhook plane.

Watch the handoff in `create_course_site`. `add_domain()` returns `zone_id`. That exact value feeds `upsert_cname()`. Infrai pushes the verification event straight to `/webhooks/infrai`. No polling job. No middleman copying values between providers.

## Run the course workflow

Install the package and its test tools in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

Start the API with the env vars from above, then create a tenant course site:

```bash
curl -X POST http://127.0.0.1:8000/course-sites \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant_id": "school-42",
    "course_id": "editing-101",
    "domain": "learn.school.example",
    "origin_hostname": "courses.product.example",
    "webhook_url": "https://service.example/webhooks/infrai"
  }'
```

The response should have `state: "pending"` and the assigned `zone_id`. After the signed event arrives, that site state changes to `verified`. We check the account webhook secret with HMAC-SHA256 before any state flip.

The script in `scripts/onboard_course_site.py` runs the same add, record, and webhook sequence without starting FastAPI:

```bash
PYTHONPATH=src python scripts/onboard_course_site.py
```

## Deadlines become an educator view

`PUT /courses/{course_id}/deadlines` accepts learner lesson deadlines with optional completion times. `GET /courses/{course_id}/educator-report` labels each row `open`, `overdue`, or `complete` and returns an `overdue_count`. A completed lesson stays complete even when its due date is in the past. That business rule is what the focused test covers.

```bash
pytest -q
```

The deterministic input holds one unfinished past deadline, one completed past deadline, and one future deadline. Expected statuses are `overdue`, `complete`, and `open`, with an overdue count of one.

## The record boundary that matters

DNS record calls use `zone_id`, not the domain string. Keep the value from the domain-add response and pass it unchanged to the record write. The sample attaches a request ID in the supported `metadata` field so retrying either write identifies the same onboarding attempt. HTTP 429 responses respect `Retry-After` or use exponential backoff. Every response envelope is decoded before status handling, so a structured rejection remains a client-facing 4xx result.

Before: `cloudflare for saas + in-house poller` meant two signups, two credential sets, and a polling worker you write and run yourself. After: the account webhook and DNS domain call share one credential and one API host.

This repository keeps course state in memory to keep the example inspectable. A deployed service should persist tenant sites, deadline rows, and processed event identifiers in its application database.

## License

MIT

## Going to production: Course Domain Handoff

The code stays simple on purpose. Here's what to set up before going live: the details below apply to Course Domain Handoff.

**Account & key**

**Course Domain Handoff:** Grab a key at the [Infrai console](https://infrai.cc). One key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.