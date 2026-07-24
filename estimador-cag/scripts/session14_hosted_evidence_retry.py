"""Current Logfire query API runner for hosted Session 14 evidence."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta

import httpx

from scripts import session14_hosted_evidence as evidence


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    raw_retry_after = response.headers.get("retry-after", "").strip()
    if raw_retry_after:
        try:
            return min(max(float(raw_retry_after), 1.0), 60.0)
        except ValueError:
            pass
    return min(3.0 * (attempt + 1), 30.0)


async def _query_hosted_trace(
    *,
    api_key: str,
    trace_id: str,
) -> list[dict[str, object]]:
    base_url = os.getenv(
        "LOGFIRE_QUERY_BASE_URL",
        "https://logfire-eu.pydantic.dev",
    ).rstrip("/")
    sql = f"""
        SELECT
            trace_id,
            span_id,
            parent_span_id,
            span_name,
            attributes->>'execution_mode' AS execution_mode,
            attributes->>'execution_status' AS execution_status,
            attributes->>'human_review_status' AS human_review_status,
            attributes->>'node_name' AS node_name
        FROM records
        WHERE trace_id = '{trace_id}'
        ORDER BY start_timestamp ASC
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    body = {
        "sql": sql,
        "min_timestamp": (
            datetime.now(tz=UTC) - timedelta(hours=2)
        ).isoformat(),
        "limit": 500,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(20):
            response = await client.post(
                f"{base_url}/v2/query",
                headers=headers,
                json=body,
            )
            if response.status_code == 429:
                await asyncio.sleep(_retry_delay(response, attempt))
                continue
            response.raise_for_status()
            rows = evidence._rows_from_query_payload(response.json())
            if rows:
                return rows
            await asyncio.sleep(min(2.0 + attempt * 2.0, 15.0))

    raise RuntimeError(
        "Hosted trace remained unavailable after current-API retries"
    )


def main() -> None:
    evidence._query_hosted_trace = _query_hosted_trace
    evidence.main()


if __name__ == "__main__":
    main()
