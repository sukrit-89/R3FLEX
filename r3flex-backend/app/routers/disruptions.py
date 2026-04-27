"""
Disruptions router for live/manual disruption analysis.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.disruption import (
    DisruptionCreate,
    DisruptionList,
    DisruptionRead,
    DisruptionSummary,
)
from app.services.disruption_svc import DisruptionService

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/trigger", response_model=DisruptionRead, status_code=201)
async def trigger_custom_disruption(
    payload: DisruptionCreate,
    db: AsyncSession = Depends(get_db),
) -> DisruptionRead:
    """
    Trigger analysis of a custom raw signal.
    """
    signal = {
        "text": payload.raw_signal,
        "source": payload.source or "manual",
        "severity": 5.0,
    }

    logger.info(
        "Custom disruption triggered: source=%s signal_len=%d",
        payload.source, len(payload.raw_signal)
    )

    disruption = await DisruptionService.process_signal(
        signal=signal,
        db=db,
        company_id=payload.company_id or settings.company_id,
    )

    if disruption is None:
        raise HTTPException(status_code=500, detail="Signal processing failed.")

    await db.refresh(disruption)
    return DisruptionRead.model_validate(disruption)


@router.post("/ingest", response_model=DisruptionRead, status_code=201)
async def trigger_live_ingestion(
    db: AsyncSession = Depends(get_db),
) -> DisruptionRead:
    """
    Poll configured live providers once and process the highest-severity signal.
    """
    from app.ingestion.scheduler import collect_live_signals

    signals = await collect_live_signals()
    if not signals:
        raise HTTPException(
            status_code=503,
            detail="No live signals available. Configure at least one provider or feed URL.",
        )

    signal = max(signals, key=lambda item: item.get("severity", 0))
    disruption = await DisruptionService.process_signal(
        signal=signal,
        db=db,
        company_id=settings.company_id,
    )
    if disruption is None:
        raise HTTPException(status_code=500, detail="Live signal processing failed.")

    await db.refresh(disruption)
    return DisruptionRead.model_validate(disruption)


@router.get("", response_model=DisruptionList)
async def list_disruptions(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Records per page"),
    db: AsyncSession = Depends(get_db),
) -> DisruptionList:
    disruptions, total = await DisruptionService.get_paginated(db, page, page_size)
    return DisruptionList(
        items=[DisruptionSummary.model_validate(disruption) for disruption in disruptions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{disruption_id}", response_model=DisruptionRead)
async def get_disruption(
    disruption_id: str,
    db: AsyncSession = Depends(get_db),
) -> DisruptionRead:
    import uuid

    try:
        uid = uuid.UUID(disruption_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format.")

    disruption = await DisruptionService.get_by_id(uid, db)
    if not disruption:
        raise HTTPException(status_code=404, detail=f"Disruption {disruption_id} not found.")

    return DisruptionRead.model_validate(disruption)
