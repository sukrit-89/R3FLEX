"""
APScheduler setup for polling live signal feeds on a fixed interval.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: AsyncIOScheduler = AsyncIOScheduler(timezone="UTC")


def _has_configured_live_provider() -> bool:
    return bool(
        settings.news_api_key
        or settings.noaa_api_key
        or settings.port_signals_url
    )


async def collect_live_signals() -> list[dict]:
    """
    Collect normalized signals from all configured live providers.
    """
    from app.ingestion.demo_feed import get_demo_signals
    from app.ingestion.news_feed import fetch_news_signals
    from app.ingestion.weather_feed import fetch_weather_signals
    from app.ingestion.port_feed import fetch_port_signals

    all_signals: list[dict] = []
    logger.info(
        "Live provider config: news=%s weather=%s port=%s demo_fallback=%s.",
        bool(settings.news_api_key),
        bool(settings.noaa_api_key),
        bool(settings.port_signals_url),
        settings.demo_signal_fallback_enabled,
    )

    try:
        news = await fetch_news_signals()
        all_signals.extend(news)
        logger.info("News feed: %d signals fetched.", len(news))
    except Exception as exc:
        logger.warning("News feed error: %s. Skipping.", exc)

    try:
        weather = await fetch_weather_signals()
        all_signals.extend(weather)
        logger.info("Weather feed: %d signals fetched.", len(weather))
    except Exception as exc:
        logger.warning("Weather feed error: %s. Skipping.", exc)

    try:
        port_signals = await fetch_port_signals()
        active_port = [item for item in port_signals if item.get("severity", 0) >= 5]
        all_signals.extend(active_port)
        logger.info("Port feed: %d active signals.", len(active_port))
    except Exception as exc:
        logger.warning("Port data error: %s. Skipping.", exc)

    if not all_signals and settings.demo_signal_fallback_enabled and not _has_configured_live_provider():
        demo_signals = get_demo_signals()
        all_signals.extend(demo_signals)
        logger.info("Demo feed fallback: %d signals loaded.", len(demo_signals))
    elif not all_signals:
        logger.info(
            "Configured live providers produced no actionable signals. "
            "This can happen when NewsAPI has no matching recent articles and NOAA has no severe records."
        )

    return all_signals


async def poll_all_feeds() -> None:
    """
    Poll all configured feeds and process the top-priority signal.
    """
    logger.info("Polling all signal feeds...")
    all_signals = await collect_live_signals()

    if not all_signals:
        logger.info("No signals from any feed this cycle.")
        return

    top_signal = max(all_signals, key=lambda item: item.get("severity", 0))
    logger.info(
        "Top signal this cycle: source=%s severity=%.1f text='%s...'",
        top_signal.get("source", "unknown"),
        top_signal.get("severity", 0),
        top_signal.get("text", "")[:80],
    )

    try:
        from app.database import AsyncSessionLocal
        from app.services.disruption_svc import DisruptionService

        async with AsyncSessionLocal() as db:
            await DisruptionService.process_signal(signal=top_signal, db=db)
            await db.commit()
    except Exception as exc:
        logger.error("Signal processing error: %s", exc, exc_info=True)


def start_scheduler() -> None:
    if _scheduler.running:
        logger.info("Scheduler already running.")
        return

    _scheduler.add_job(
        poll_all_feeds,
        trigger=IntervalTrigger(seconds=settings.poll_interval_seconds),
        id="poll_feeds",
        replace_existing=True,
        misfire_grace_time=30,
    )
    _scheduler.start()
    logger.info("Scheduler started. Polling every %ds.", settings.poll_interval_seconds)


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
