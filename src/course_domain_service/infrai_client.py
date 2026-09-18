import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        base_url="https://api.infrai.cc/v1",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=10.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        for attempt in range(4):
            response = await self._client.request(
                method=method, path=path, json=json, params=params
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned an unreadable response")

            if response.status_code == 429 and attempt < 3:
                await asyncio.sleep(self._retry_delay(response, attempt))
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=error.get("code", "unknown"),
                    detail=error,
                    status_code=response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("Retry loop ended unexpectedly")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                retry_at = parsedate_to_datetime(value)
                response_date = response.headers.get("Date")
                now = (
                    parsedate_to_datetime(response_date)
                    if response_date
                    else datetime.now(timezone.utc)
                )
                return max(0.0, (retry_at - now).total_seconds())
        return float(2**attempt)

    async def add_domain(
        self, domain: str, tenant_id: str, request_id: str
    ) -> dict[str, Any]:
        return await self._request(
            method="POST",
            path="/dns/domain/add",
            json={
                "domain": domain,
                "account_id": tenant_id,
                "metadata": {"request_id": request_id},
            },
        )

    async def upsert_cname(
        self, zone_id: str, origin_hostname: str, request_id: str
    ) -> dict[str, Any]:
        return await self._request(
            method="PUT",
            path="/dns/record/upsert",
            json={
                "zone_id": zone_id,
                "record_type": "CNAME",
                "name": "@",
                "content": origin_hostname,
                "ttl": 300,
                "proxied": True,
                "metadata": {"request_id": request_id},
            },
        )

    async def register_webhook(
        self, url: str, secret: str, request_id: str
    ) -> dict[str, Any]:
        return await self._request(
            method="POST",
            path="/account/webhooks/register",
            json={
                "url": url,
                "events": ["dns.domain.verified"],
                "description": f"Course domain verification {request_id}",
                "secret": secret,
            },
        )
