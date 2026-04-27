"""
Topology API schemas.
"""
from pydantic import BaseModel, Field


class TopologyNetworkResponse(BaseModel):
    company_id: str
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)
    shipments: list[dict] = Field(default_factory=list)
    suppliers: list[dict] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)

