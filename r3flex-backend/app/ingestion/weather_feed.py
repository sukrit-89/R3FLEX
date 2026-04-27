"""
NOAA weather feed for live disruption signals.

Returns an empty list when the provider is not configured or unavailable.
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

NOAA_BASE = "https://www.ncdc.noaa.gov/cdo-web/api/v2/data"

MONITORED_STATIONS = {
    "GHCND:EGY00000001": "Suez Canal Region, Egypt",
    "GHCND:NLD00000001": "Rotterdam, Netherlands",
    "GHCND:DEU00000001": "Frankfurt, Germany",
}


async def fetch_weather_signals() -> list[dict]:
    """
    Fetch severe weather data from NOAA Climate Data Online API.
    """
    if not settings.noaa_api_key:
        logger.info("NOAA_API_KEY not set; skipping weather feed.")
        return []

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    headers = {"token": settings.noaa_api_key}
    params = {
        "datasetid": "GHCND",
        "datatypeid": "WSFI",
        "stationid": list(MONITORED_STATIONS.keys()),
        "startdate": start_date,
        "enddate": end_date,
        "units": "metric",
        "limit": 50,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(NOAA_BASE, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("NOAA API HTTP error %d: %s.", exc.response.status_code, exc)
        return []
    except Exception as exc:
        logger.warning("NOAA API error: %s.", exc)
        return []

    results = data.get("results", [])
    logger.info("NOAA API returned %d weather records.", len(results))
    signals = _normalize_weather_results(results)
    logger.info(
        "NOAA weather signals after severity threshold: %d.",
        len(signals),
    )
    return signals


def _normalize_weather_results(results: list[dict]) -> list[dict]:
    signals = []
    wind_severe_threshold_kmh = 60

    for record in results:
        value = record.get("value", 0)
        station_id = record.get("station", "")
        geography = MONITORED_STATIONS.get(station_id, "Unknown location")

        if value < wind_severe_threshold_kmh:
            continue

        severity = min(10.0, round(5.0 + (value - 60) / 10, 1))

        signals.append({
            "source": "weather",
            "title": f"Severe weather event detected: {geography}",
            "text": (
                f"NOAA monitoring recorded severe weather at {geography}. "
                f"Wind speed: {value} km/h. Threshold for shipping disruption: "
                f"{wind_severe_threshold_kmh} km/h. Station: {station_id}. "
                f"Date: {record.get('date', 'unknown')}."
            ),
            "published_at": record.get("date", datetime.now(timezone.utc).isoformat()),
            "severity": severity,
            "geography": geography,
            "event_type": "extreme_weather",
            "raw_value": value,
            "station_id": station_id,
        })

    return signals
