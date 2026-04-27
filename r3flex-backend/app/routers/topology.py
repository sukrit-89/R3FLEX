"""
Topology router.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.topology import TopologyNetworkResponse
from app.services.topology_svc import TopologyService

router = APIRouter()


@router.get("/network", response_model=TopologyNetworkResponse)
async def get_network(
    company_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> TopologyNetworkResponse:
    payload = await TopologyService.get_network(db, company_id=company_id)
    return TopologyNetworkResponse(**payload)

