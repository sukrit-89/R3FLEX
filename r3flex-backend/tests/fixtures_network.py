"""
Test-only network fixture data.
"""
import logging

from app.graph.supplier_graph import SupplierGraph, set_supplier_graph
from app.graph.network_store import set_shipments

logger = logging.getLogger(__name__)

ACTIVE_SHIPMENTS = [
    {
        "id": "ship-001",
        "origin": "chennai-manufacturer",
        "destination": "frankfurt-warehouse",
        "route": ["chennai-manufacturer", "suez-hub", "rotterdam-dist", "frankfurt-warehouse"],
    },
    {
        "id": "ship-002",
        "origin": "chennai-manufacturer",
        "destination": "rotterdam-dist",
        "route": ["chennai-manufacturer", "suez-hub", "rotterdam-dist"],
    },
    {
        "id": "ship-003",
        "origin": "chennai-manufacturer",
        "destination": "frankfurt-warehouse",
        "route": ["chennai-manufacturer", "suez-hub", "rotterdam-dist", "frankfurt-warehouse"],
    },
    {
        "id": "ship-004",
        "origin": "chennai-manufacturer",
        "destination": "rotterdam-dist",
        "route": ["chennai-manufacturer", "suez-hub", "rotterdam-dist"],
    },
    {
        "id": "ship-005",
        "origin": "chennai-manufacturer",
        "destination": "berlin-pharma",
        "route": ["chennai-manufacturer", "cape-route-hub", "rotterdam-dist", "berlin-pharma"],
    },
    {
        "id": "ship-006",
        "origin": "chennai-manufacturer",
        "destination": "frankfurt-warehouse",
        "route": ["chennai-manufacturer", "cape-route-hub", "rotterdam-dist", "frankfurt-warehouse"],
    },
    {
        "id": "ship-007",
        "origin": "india-raw-supplier",
        "destination": "chennai-manufacturer",
        "route": ["india-raw-supplier", "chennai-manufacturer"],
    },
]


def seed_supplier_graph() -> SupplierGraph:
    graph = SupplierGraph()

    graph.add_node("india-raw-supplier", location="Gujarat, India", tier=0, type="raw_supplier", active=True, risk_level=0.3)
    graph.add_node("europe-excipient-supplier", location="Hamburg, Germany", tier=0, type="raw_supplier", active=True, risk_level=0.2)
    graph.add_node("chennai-manufacturer", location="Chennai, India", tier=1, type="manufacturer", active=True, risk_level=0.25)
    graph.add_node("suez-hub", location="Suez Canal, Egypt", tier=2, type="logistics_hub", active=True, risk_level=0.7, alternative="cape-route-hub")
    graph.add_node("cape-route-hub", location="Cape Town, South Africa", tier=2, type="logistics_hub", active=True, risk_level=0.2)
    graph.add_node("rotterdam-dist", location="Rotterdam, Netherlands", tier=2, type="distribution_center", active=True, risk_level=0.15)
    graph.add_node("frankfurt-warehouse", location="Frankfurt, Germany", tier=2, type="warehouse", active=True, risk_level=0.1, current_stock_days=12)
    graph.add_node("berlin-pharma", location="Berlin, Germany", tier=2, type="backup_supplier", active=True, risk_level=0.15)

    graph.add_edge("india-raw-supplier", "chennai-manufacturer", transit_days=3, cost_factor=1.0, risk_level=0.2, mode="road")
    graph.add_edge("europe-excipient-supplier", "chennai-manufacturer", transit_days=18, cost_factor=1.5, risk_level=0.3, mode="sea")
    graph.add_edge("chennai-manufacturer", "suez-hub", transit_days=7, cost_factor=1.0, risk_level=0.7, mode="sea", is_primary=True)
    graph.add_edge("chennai-manufacturer", "cape-route-hub", transit_days=21, cost_factor=1.8, risk_level=0.2, mode="sea", is_primary=False)
    graph.add_edge("suez-hub", "rotterdam-dist", transit_days=4, cost_factor=1.0, risk_level=0.15, mode="sea")
    graph.add_edge("cape-route-hub", "rotterdam-dist", transit_days=7, cost_factor=1.8, risk_level=0.1, mode="sea")
    graph.add_edge("rotterdam-dist", "frankfurt-warehouse", transit_days=1, cost_factor=1.0, risk_level=0.05, mode="road")
    graph.add_edge("rotterdam-dist", "berlin-pharma", transit_days=2, cost_factor=1.1, risk_level=0.08, mode="road")
    graph.add_edge("berlin-pharma", "frankfurt-warehouse", transit_days=1, cost_factor=1.2, risk_level=0.05, mode="road")

    set_supplier_graph(graph)
    set_shipments(ACTIVE_SHIPMENTS)

    logger.info("Test network seeded: %d nodes, %d edges.", graph.node_count, graph.edge_count)
    return graph


def get_suez_shipments() -> list[dict]:
    return [shipment for shipment in ACTIVE_SHIPMENTS if "suez-hub" in shipment["route"]]


def get_all_shipments() -> list[dict]:
    return ACTIVE_SHIPMENTS
