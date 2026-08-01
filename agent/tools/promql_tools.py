# agent/tools/promql_tools.py
# PromQL query helper — queries Prometheus HTTP API.

import logging
import httpx
from agent.config import cfg

logger = logging.getLogger(__name__)


def run_promql(query: str, time: str | None = None) -> dict | None:
    """
    Run an instant PromQL query against Prometheus.
    Returns the parsed result or None on failure.
    """
    url = f"{cfg.prometheus_url}/api/v1/query"
    params = {"query": query}
    if time:
        params["time"] = time

    try:
        with httpx.Client(timeout=10.0) as http:
            resp = http.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "success":
                return data.get("data", {})
            logger.warning(f"[promql] Query returned non-success: {data.get('status')}")
            return None

    except httpx.TimeoutException:
        logger.warning(f"[promql] Timeout querying: {query[:80]}")
        return None
    except Exception as e:
        logger.warning(f"[promql] Error: {e}")
        return None


def run_promql_range(
    query: str,
    start: str,
    end: str,
    step: str = "60s",
) -> dict | None:
    """Run a range PromQL query."""
    url = f"{cfg.prometheus_url}/api/v1/query_range"
    try:
        with httpx.Client(timeout=15.0) as http:
            resp = http.get(
                url,
                params={"query": query, "start": start, "end": end, "step": step},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data") if data.get("status") == "success" else None
    except Exception as e:
        logger.warning(f"[promql_range] Error: {e}")
        return None
