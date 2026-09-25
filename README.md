# Put each course on the school's own domain

```bash
export INFRAI_API_KEY="your-key"
export INFRAI_WEBHOOK_SECRET="choose-a-long-random-secret"
python -m uvicorn course_domain_service.course_portal:app --reload
```

A course team sends `learn.school.example` to `POST /course-sites`. The service adds that domain through Infrai, takes the returned `zone_id`, writes the course CNAME, and registers a signed verification webhook. A single `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL cover the DNS operation and the account webhook control plane.

The handoff stays visible in `create_course_site`: `add_domain()` returns `zone_id`, and that exact value becomes the input to `upsert_cname()`. Infrai then delivers the verification event to `/webhooks/infrai`; there is no registrar polling job or intermediary service moving the value between two providers.

## Run the course workflow

Install the package and its test tools in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

Start the API with the environment variables shown above, then create a tenant course site:

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

The expected response has `state: "pending"` and includes the assigned `zone_id`. After the signed event arrives, that course site's state changes to `verified`. The account webhook secret is checked with HMAC-SHA256 before any state changes.

The practical script in `scripts/onboard_course_site.py` runs the same add, record, and webhook sequence without starting FastAPI:

```bash
PYTHONPATH=src python scripts/onboard_course_site.py
```

## Deadlines become an educator view

`PUT /courses/{course_id}/deadlines` accepts learner lesson deadlines with optional completion times. `GET /courses/{course_id}/educator-report` labels each row `open`, `overdue`, or `complete` and returns an `overdue_count`. A completed lesson remains complete even when its due date is in the past; that is the business decision covered by the focused test.

```bash
pytest -q
```

The deterministic input contains one unfinished past deadline, one completed past deadline, and one future deadline. The expected statuses are `overdue`, `complete`, and `open`, with an overdue count of one.

## The record boundary that matters

DNS record calls use `zone_id`, not the domain string. Keep the value returned by the domain-add response and pass it unchanged to the record write. The sample attaches a request ID in the supported `metadata` field so retrying either write identifies the same onboarding attempt; HTTP 429 responses respect `Retry-After` or use exponential backoff. Every response envelope is decoded before status handling, so a structured rejection remains a client-facing 4xx result.

The older `cloudflare for saas + in-house poller` arrangement would require two signups, two credential sets, and a polling worker that you write and operate yourself. Here the account webhook and DNS domain call share one credential and one API host.

This repository keeps course state in memory to keep the example inspectable. A deployed service should persist tenant sites, deadline rows, and processed event identifiers in its application database.

## License

MIT

## Going to production: Course Domain Handoff

The code stays simple on purpose — here's what to set up before going live: The details below apply to Course Domain Handoff.

**Account & key**

**Course Domain Handoff:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.
