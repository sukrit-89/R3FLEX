"""
Scenario Generator produces exactly three rerouting options per disruption.
"""
import logging
from dataclasses import dataclass

from app.agents.orchestrator import AgentState
from app.config import get_settings
from app.graph.network_store import get_shipments_by_node
from app.graph.supplier_graph import get_supplier_graph

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ScenarioOption:
    option_index: int
    label: str
    description: str
    cost_delta_usd: float
    time_delta_days: float
    risk_score: float


class ScenarioGenerator:
    async def generate(self, agent_state: AgentState) -> list[ScenarioOption]:
        logger.info(
            "Generating scenarios for event=%s node=%s",
            agent_state.get("event_type", "unknown"),
            agent_state.get("primary_node", ""),
        )
        if settings.google_api_key:
            return await self._llm_generate(agent_state)
        return self._graph_fallback(agent_state)

    async def _llm_generate(self, state: AgentState) -> list[ScenarioOption]:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from pydantic import BaseModel, Field

            class ScenarioList(BaseModel):
                scenarios: list[dict] = Field(
                    description="Exactly 3 scenarios with keys: label, description, cost_delta_usd, time_delta_days, risk_score"
                )

            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.google_api_key,
                max_output_tokens=settings.llm_max_tokens,
                temperature=0.4,
            )
            structured = llm.with_structured_output(ScenarioList)

            prompt = (
                f"Supply chain disruption: {state.get('event_type')} at {state.get('geography')}\n"
                f"Severity: {state.get('severity_score')}/10\n"
                f"Primary disrupted node: {state.get('primary_node')}\n"
                f"Cascade risk: {state.get('risk_summary', 'unknown')}\n\n"
                "Generate EXACTLY 3 rerouting/resilience options. "
                "For each scenario provide: label, description, cost_delta_usd, "
                "time_delta_days, risk_score."
            )

            result: ScenarioList = await structured.ainvoke(prompt)
            scenarios_raw = result.scenarios[:3]

            options = [
                ScenarioOption(
                    option_index=index,
                    label=str(item.get("label", f"Option {index}")),
                    description=str(item.get("description", "")),
                    cost_delta_usd=float(item.get("cost_delta_usd", 0)),
                    time_delta_days=float(item.get("time_delta_days", 0)),
                    risk_score=float(item.get("risk_score", 5.0)),
                )
                for index, item in enumerate(scenarios_raw, start=1)
            ]

            while len(options) < 3:
                options.extend(self._graph_fallback(state)[: 3 - len(options)])

            return options[:3]
        except Exception as exc:
            logger.warning("LLM scenario generation failed: %s. Using fallback.", exc)
            return self._graph_fallback(state)

    def _graph_fallback(self, state: AgentState) -> list[ScenarioOption]:
        primary_node = state.get("primary_node", "unknown")
        geography = state.get("geography", "affected area")
        severity = float(state.get("severity_score", 5.0) or 5.0)
        shipments = get_shipments_by_node(primary_node)
        shipment_count = max(1, len(shipments))
        base_cost = shipment_count * severity * 2200
        base_delay = max(1.0, round(severity / 2, 1))

        graph = get_supplier_graph()
        node = graph.get_node(primary_node) if primary_node and primary_node != "unknown" else None
        alternate_node = node.get("alternative") if node else None

        alternate_label = f"Reroute via {alternate_node}" if alternate_node else "Reroute via alternate lane"

        return [
            ScenarioOption(
                option_index=1,
                label=alternate_label,
                description=(
                    f"Move affected flow away from {geography} using the nearest available "
                    "alternate route or logistics lane."
                ),
                cost_delta_usd=round(base_cost * 1.3, 2),
                time_delta_days=round(base_delay * 1.8, 1),
                risk_score=max(1.5, round(4.8 - min(severity / 5, 2.0), 1)),
            ),
            ScenarioOption(
                option_index=2,
                label="Activate backup supplier",
                description=(
                    "Shift replenishment or fulfillment to a qualified backup supplier or "
                    "distribution node to reduce concentration risk."
                ),
                cost_delta_usd=round(base_cost * 0.95, 2),
                time_delta_days=round(base_delay * 1.1, 1),
                risk_score=max(1.2, round(3.8 - min(severity / 6, 1.5), 1)),
            ),
            ScenarioOption(
                option_index=3,
                label="Expedite critical shipments",
                description=(
                    "Prioritize the most time-sensitive inventory through premium transport "
                    "while lower-priority shipments remain on standard routes."
                ),
                cost_delta_usd=round(base_cost * 2.2, 2),
                time_delta_days=max(1.0, round(base_delay * 0.45, 1)),
                risk_score=max(1.0, round(2.6 - min(severity / 10, 0.8), 1)),
            ),
        ]
