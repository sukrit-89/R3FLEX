"""
Runtime network store.

Loads supplier graph + shipment metadata from configured JSON files instead of
embedding a demo network in application code.
"""
import json
import logging
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.graph.supplier_graph import SupplierGraph, set_supplier_graph

logger = logging.getLogger(__name__)
settings = get_settings()

_shipments: list[dict[str, Any]] = []


def load_runtime_network() -> SupplierGraph:
    """
    Load graph and shipments from configured JSON sources.
    """
    graph = SupplierGraph()
    shipments: list[dict[str, Any]] = []

    if settings.supplier_graph_path:
        payload = _read_json_file(settings.supplier_graph_path)
        for node in payload.get("nodes", []):
            node_id = node.get("id")
            if not node_id:
                continue
            attrs = {k: v for k, v in node.items() if k != "id"}
            graph.add_node(str(node_id), **attrs)

        for edge in payload.get("edges", []):
            source = edge.get("source")
            target = edge.get("target")
            if not source or not target:
                continue
            attrs = {k: v for k, v in edge.items() if k not in {"source", "target"}}
            graph.add_edge(str(source), str(target), **attrs)

        shipments = _normalize_shipments(payload.get("shipments", []))

    if settings.shipments_data_path:
        shipment_payload = _read_json_file(settings.shipments_data_path)
        if isinstance(shipment_payload, list):
            shipments = _normalize_shipments(shipment_payload)
        elif isinstance(shipment_payload, dict):
            shipments = _normalize_shipments(shipment_payload.get("shipments", []))

    set_supplier_graph(graph)
    set_shipments(shipments)

    logger.info(
        "Runtime network loaded: %d nodes, %d edges, %d shipments",
        graph.node_count,
        graph.edge_count,
        len(_shipments),
    )
    return graph


def _read_json_file(raw_path: str) -> Any:
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists():
        raise FileNotFoundError(f"Configured data file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _normalize_shipments(items: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        shipment_id = item.get("id")
        if not shipment_id:
            continue
        route = item.get("route") or []
        normalized.append(
            {
                **item,
                "id": str(shipment_id),
                "route": [str(node_id) for node_id in route],
            }
        )
    return normalized


def set_shipments(shipments: list[dict[str, Any]]) -> None:
    global _shipments
    _shipments = shipments


def get_all_shipments() -> list[dict[str, Any]]:
    return list(_shipments)


def get_shipments_by_node(node_id: str) -> list[dict[str, Any]]:
    return [shipment for shipment in _shipments if node_id in shipment.get("route", [])]
