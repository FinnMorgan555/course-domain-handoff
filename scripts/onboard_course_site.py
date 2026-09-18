import asyncio
import os
from uuid import uuid4

from course_domain_service.infrai_client import InfraiClient


async def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    secret = os.environ["INFRAI_WEBHOOK_SECRET"]
    client = InfraiClient(api_key)
    request_id = str(uuid4())
    try:
        domain = await client.add_domain("learn.school.example", "school-42", request_id)
        zone_id = domain["zone_id"]
        await client.upsert_cname(zone_id, "courses.product.example", request_id)
        webhook = await client.register_webhook(
            "https://service.example/webhooks/infrai", secret, request_id
        )
        print({"domain": "learn.school.example", "zone_id": zone_id, "webhook": webhook})
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

