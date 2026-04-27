"""
Topology service.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.graph.network_store import get_all_shipments
from app.graph.supplier_graph import get_supplier_graph
from app.services.supplier_svc import SupplierService

settings = get_settings()


class TopologyService:
    @staticmethod
    async def get_network(db: AsyncSession, company_id: str | None = None) -> dict:
        graph = get_supplier_graph()
        shipments = get_all_shipments()
        suppliers, supplier_total = await SupplierService.list_suppliers(db, company_id)
        nodes = graph.all_nodes()
        edges: list[dict] = []
        for node in nodes:
            node_id = node["id"]
            for target in graph.get_cascade_nodes(node_id, hops=1):
                edge = graph.get_edge_data(node_id, target)
                if edge:
                    edges.append({"source": node_id, "target": target, **edge})

        supplier_nodes = []
        for supplier in suppliers:
            primary_materials = [item.get("material") for item in supplier.material_profiles if isinstance(item, dict)]
            supplier_nodes.append(
                {
                    "id": str(supplier.id),
                    "supplier_code": supplier.supplier_code,
                    "legal_name": supplier.legal_name,
                    "country": supplier.country,
                    "city": supplier.city,
                    "business_type": supplier.business_type,
                    "status": supplier.status,
                    "material_profiles": supplier.material_profiles,
                    "facilities": supplier.facilities,
                    "lane_preferences": supplier.lane_preferences,
                    "materials": [item for item in primary_materials if item],
                }
            )

        return {
            "company_id": company_id or settings.company_id,
            "nodes": nodes,
            "edges": edges,
            "shipments": shipments,
            "suppliers": supplier_nodes,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "shipment_count": len(shipments),
                "supplier_count": supplier_total,
                "modes": sorted({edge.get("mode", "unknown") for edge in edges}),
            },
        }
