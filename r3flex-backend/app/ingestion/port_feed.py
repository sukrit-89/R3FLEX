"""
Port signal ingestion from a real HTTP JSON feed.
"""
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def fetch_port_signals() -> list[dict]:
    """
    Fetch port disruption signals from a configured JSON endpoint.
    """
    if not settings.port_signals_url:
        logger.info("PORT_SIGNALS_URL not set; skipping port feed.")
        return []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(settings.port_signals_url)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("Port feed request failed: %s", exc)
        return []

    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("items", [])
    else:
        items = []

    signals: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = item.get("text") or item.get("title")
        if not text:
            continue
        signals.append(
            {
                "source": item.get("source", "port"),
                "title": item.get("title", ""),
                "text": text,
                "severity": float(item.get("severity", 0) or 0),
                "geography": item.get("geography"),
                "event_type": item.get("event_type"),
                "published_at": item.get("published_at"),
                "port_id": item.get("port_id"),
                "port_name": item.get("port_name"),
            }
        )

    logger.info("Port feed returned %d normalized signals.", len(signals))
    return signals
