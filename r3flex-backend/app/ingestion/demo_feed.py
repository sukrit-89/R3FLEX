"""
Deterministic demo signals for local live-scan flows.
"""
from datetime import datetime, timezone


def get_demo_signals() -> list[dict]:
    """
    Return normalized disruption signals when no external provider is configured.
    """
    published_at = datetime.now(timezone.utc).isoformat()
    return [
        {
            "source": "demo",
            "title": "Suez Canal traffic disruption",
            "text": (
                "Suez Canal traffic disruption is causing rerouting pressure across "
                "Europe-bound pharmaceutical shipments. Vessel queues are increasing "
                "near Port Said, cold-chain inventory buffers are tightening, and "
                "operators are evaluating Cape of Good Hope and air freight alternatives."
            ),
            "severity": 8.7,
            "geography": "Suez Canal",
            "event_type": "trade_route_disruption",
            "published_at": published_at,
            "port_id": "EGPSD",
            "port_name": "Port Said",
        },
        {
            "source": "demo",
            "title": "Rotterdam berth congestion",
            "text": (
                "Port of Rotterdam congestion has increased berth waiting times beyond "
                "48 hours, putting replenishment lanes and downstream delivery windows at risk."
            ),
            "severity": 6.4,
            "geography": "Rotterdam",
            "event_type": "port_congestion",
            "published_at": published_at,
            "port_id": "NLRTM",
            "port_name": "Rotterdam",
        },
    ]
