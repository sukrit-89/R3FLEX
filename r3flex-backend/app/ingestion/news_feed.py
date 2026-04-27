"""
NewsAPI integration for live supply-chain disruption signals.

Returns an empty list when the provider is not configured or unavailable.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

NEWS_API_BASE = "https://newsapi.org/v2/everything"

SUPPLY_CHAIN_KEYWORDS = (
    "supply chain disruption OR port closure OR shipping delay "
    "OR canal blockage OR factory fire OR logistics disruption "
    "OR trade route OR cargo disruption OR semiconductor shortage"
)

BROADER_SUPPLY_CHAIN_KEYWORDS = (
    "shipping OR port OR logistics OR cargo OR supply chain OR factory"
)


async def fetch_news_signals() -> list[dict]:
    """
    Fetch supply-chain news signals from NewsAPI.
    """
    if not settings.news_api_key:
        logger.info("NEWS_API_KEY not set; skipping news feed.")
        return []

    from_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    articles = await _fetch_articles(SUPPLY_CHAIN_KEYWORDS, from_date, page_size=20)
    if not articles:
        logger.info("NewsAPI exact disruption query returned 0 articles; trying broader logistics query.")
        articles = await _fetch_articles(BROADER_SUPPLY_CHAIN_KEYWORDS, from_date, page_size=10)

    logger.info("NewsAPI usable articles: %d.", len(articles))
    return [
        _normalize_article(article)
        for article in articles
        if article.get("title") or article.get("description") or article.get("content")
    ]


async def _fetch_articles(query: str, from_date: str, page_size: int) -> list[dict]:
    params = {
        "q": query,
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": page_size,
        "apiKey": settings.news_api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(NEWS_API_BASE, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "NewsAPI HTTP error %d for query '%s': %s.",
            exc.response.status_code,
            query,
            exc,
        )
        return []
    except Exception as exc:
        logger.warning("NewsAPI error for query '%s': %s.", query, exc)
        return []

    articles = data.get("articles", [])
    logger.info("NewsAPI query '%s' returned %d articles.", query, len(articles))
    return articles


def _normalize_article(article: dict) -> dict:
    text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}"
    severity = _estimate_severity(text)

    return {
        "source": "news",
        "title": article.get("title", ""),
        "text": text[:2000],
        "url": article.get("url", ""),
        "published_at": article.get("publishedAt", ""),
        "severity": severity,
        "geography": _extract_geography(text),
    }


def _estimate_severity(text: str) -> float:
    text_lower = text.lower()
    score = 3.0

    high_impact = ["closure", "shutdown", "blockage", "military", "war", "explosion", "fire"]
    medium_impact = ["delay", "congestion", "disruption", "diversion", "shortage"]

    for word in high_impact:
        if word in text_lower:
            score += 1.5

    for word in medium_impact:
        if word in text_lower:
            score += 0.7

    return min(10.0, round(score, 1))


def _extract_geography(text: str) -> Optional[str]:
    locations = [
        "Suez Canal", "Red Sea", "Rotterdam", "Shanghai", "Singapore",
        "Chennai", "Frankfurt", "Hamburg", "Port Said", "Cape of Good Hope",
    ]
    for loc in locations:
        if loc.lower() in text.lower():
            return loc
    return None
