"""
Tests for agent fallback behavior without live model calls.
"""
import pytest

from app.agents.cascade import CascadeAgent
from app.agents.classifier import ClassifierAgent
from app.agents.graph_mapper import GraphMapperAgent
from app.agents.severity import SeverityAgent
from tests.fixtures_network import seed_supplier_graph


@pytest.fixture(autouse=True)
def setup_graph():
    seed_supplier_graph()


class TestClassifierAgent:
    @pytest.mark.asyncio
    async def test_suez_classification(self):
        agent = ClassifierAgent()
        agent._structured_llm = None

        result = await agent.classify(
            "Suez Canal vessel diversions reported due to Red Sea conflict."
        )
        assert result.event_type == "trade_route_disruption"
        assert "Suez" in result.geography or "Egypt" in result.geography

    @pytest.mark.asyncio
    async def test_storm_classification(self):
        agent = ClassifierAgent()
        agent._structured_llm = None

        result = await agent.classify("Hurricane approaching Gulf coast with major storm warning.")
        assert result.event_type == "extreme_weather"


class TestSeverityAgent:
    @pytest.mark.asyncio
    async def test_trade_route_disruption_is_high_severity(self):
        agent = SeverityAgent()
        agent._structured_llm = None

        result = await agent.score(
            event_type="trade_route_disruption",
            geography="Suez Canal, Egypt",
            affected_nodes=["suez-hub", "rotterdam-dist"],
            raw_signal="Suez Canal blocked",
            affected_trade_routes=["Asia-Europe"],
        )
        assert result.severity_score >= 7.0

    @pytest.mark.asyncio
    async def test_severity_in_range(self):
        agent = SeverityAgent()
        agent._structured_llm = None

        for event_type in ["factory_fire", "extreme_weather", "port_congestion", "unknown"]:
            result = await agent.score(event_type, "Unknown", [], "signal", [])
            assert 1.0 <= result.severity_score <= 10.0


class TestGraphMapperAgent:
    @pytest.mark.asyncio
    async def test_suez_maps_to_suez_hub(self):
        agent = GraphMapperAgent()
        result = await agent.map(
            geography="Suez Canal, Egypt",
            event_type="trade_route_disruption",
            affected_trade_routes=["Asia-Europe"],
        )
        assert result.primary_node == "suez-hub"
        assert result.mapping_method == "geo_match"
        assert result.mapping_confidence >= 0.9

    @pytest.mark.asyncio
    async def test_rotterdam_maps_correctly(self):
        agent = GraphMapperAgent()
        result = await agent.map("Rotterdam, Netherlands", "port_congestion", [])
        assert result.primary_node == "rotterdam-dist"


class TestCascadeAgent:
    @pytest.mark.asyncio
    async def test_suez_cascade_has_downstream_nodes(self):
        agent = CascadeAgent()
        agent._llm = None

        result = await agent.simulate(
            primary_node="suez-hub",
            event_type="trade_route_disruption",
            severity_score=8.0,
            geography="Suez Canal, Egypt",
        )
        assert "rotterdam-dist" in result.cascade_nodes
        assert "frankfurt-warehouse" in result.cascade_nodes

    @pytest.mark.asyncio
    async def test_cascade_depth_minimum_2(self):
        agent = CascadeAgent()
        agent._llm = None

        result = await agent.simulate("suez-hub", "trade_route_disruption", 8.0, "Suez")
        assert result.cascade_depth >= 2

    @pytest.mark.asyncio
    async def test_unknown_node_returns_empty_cascade(self):
        agent = CascadeAgent()
        agent._llm = None

        result = await agent.simulate("unknown", "trade_route_disruption", 5.0, "Unknown")
        assert result.cascade_nodes == []
