"""
Tests for decision engine components.
"""
import pytest

from app.agents.orchestrator import AgentState
from app.engine.confidence import ConfidenceEvaluator
from app.engine.scenario_gen import ScenarioGenerator, ScenarioOption
from app.engine.tradeoff import TradeoffScorer


class TestScenarioGenerator:
    @pytest.mark.asyncio
    async def test_returns_exactly_three_scenarios(self):
        gen = ScenarioGenerator()
        state: AgentState = {
            "primary_node": "suez-hub",
            "event_type": "trade_route_disruption",
            "geography": "Suez Canal, Egypt",
            "severity_score": 8.0,
        }
        scenarios = await gen.generate(state)
        assert len(scenarios) == 3

    @pytest.mark.asyncio
    async def test_option_indices_are_one_two_three(self):
        gen = ScenarioGenerator()
        state: AgentState = {
            "primary_node": "suez-hub",
            "event_type": "trade_route_disruption",
            "severity_score": 8.0,
        }
        scenarios = await gen.generate(state)
        assert [scenario.option_index for scenario in scenarios] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_scenarios_have_positive_costs(self):
        gen = ScenarioGenerator()
        state: AgentState = {
            "primary_node": "suez-hub",
            "event_type": "trade_route_disruption",
            "severity_score": 8.0,
        }
        scenarios = await gen.generate(state)
        assert all(scenario.cost_delta_usd >= 0 for scenario in scenarios)


class TestTradeoffScorer:
    def _make_scenarios(self):
        return [
            ScenarioOption(1, "Alternate Route", "", 28000, 14, 3.2),
            ScenarioOption(2, "Air Freight", "", 85000, 2, 1.8),
            ScenarioOption(3, "Backup Supplier", "", 12000, 3, 2.1),
        ]

    def test_returns_3_scored_scenarios(self):
        scorer = TradeoffScorer()
        scored = scorer.score(self._make_scenarios())
        assert len(scored) == 3

    def test_exactly_one_recommended(self):
        scorer = TradeoffScorer()
        scored = scorer.score(self._make_scenarios())
        assert len([item for item in scored if item.recommended]) == 1

    def test_sorted_by_composite_ascending(self):
        scorer = TradeoffScorer()
        scored = scorer.score(self._make_scenarios())
        composites = [item.composite_score for item in scored]
        assert composites == sorted(composites)

    def test_composite_scores_in_0_1_range(self):
        scorer = TradeoffScorer()
        scored = scorer.score(self._make_scenarios())
        for item in scored:
            assert 0.0 <= item.composite_score <= 1.0


class TestConfidenceEvaluator:
    def _make_agent_state(self, severity=8.0, classification_conf=0.9) -> AgentState:
        return {
            "raw_signal": "Major trade route disruption affecting multiple shipments. " * 20,
            "severity_score": severity,
            "classification_confidence": classification_conf,
            "mapping_confidence": 0.9,
            "primary_node": "suez-hub",
            "source": "port",
        }

    def _make_scored_scenarios(self):
        options = [
            ScenarioOption(1, "Alternate Route", "", 28000, 14, 3.2),
            ScenarioOption(2, "Air", "", 85000, 2, 1.8),
            ScenarioOption(3, "Backup", "", 12000, 3, 2.1),
        ]
        scorer = TradeoffScorer()
        return scorer.score(options)

    def test_high_confidence_case_can_exceed_threshold(self):
        evaluator = ConfidenceEvaluator()
        scored = self._make_scored_scenarios()
        recommended = next(item for item in scored if item.recommended)
        state = self._make_agent_state()

        result = evaluator.evaluate(recommended, scored, state)

        assert result.above_threshold
        assert result.confidence >= 0.85

    def test_low_confidence_case_stays_below_threshold(self):
        evaluator = ConfidenceEvaluator()
        scored = self._make_scored_scenarios()
        recommended = next(item for item in scored if item.recommended)
        state = self._make_agent_state(severity=2.0, classification_conf=0.3)
        state["raw_signal"] = "minor"
        state["mapping_confidence"] = 0.1
        state["primary_node"] = "unknown"

        result = evaluator.evaluate(recommended, scored, state)

        assert not result.above_threshold

    def test_confidence_in_0_1_range(self):
        evaluator = ConfidenceEvaluator()
        scored = self._make_scored_scenarios()
        recommended = next(item for item in scored if item.recommended)

        for severity in [1.0, 5.0, 8.0, 10.0]:
            state = self._make_agent_state(severity=severity)
            result = evaluator.evaluate(recommended, scored, state)
            assert 0.0 <= result.confidence <= 1.0
