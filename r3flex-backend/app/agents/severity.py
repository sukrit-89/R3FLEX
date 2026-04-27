"""
Severity Agent scores disruption impact on a 1.0-10.0 scale.
"""
import logging
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.graph.network_store import get_all_shipments

logger = logging.getLogger(__name__)
settings = get_settings()


class SeverityOutput(BaseModel):
    severity_score: float = Field(ge=1.0, le=10.0)
    reasoning: str
    affected_shipment_count: int = Field(ge=0)
    estimated_delay_days: float = Field(ge=0.0)
    estimated_cost_impact_usd: float = Field(ge=0.0)


class SeverityAgent:
    def __init__(self) -> None:
        self._structured_llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        if not settings.google_api_key:
            logger.warning("GOOGLE_API_KEY not set. SeverityAgent will use heuristic fallback.")
            return
        try:
            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.google_api_key,
                max_output_tokens=settings.llm_max_tokens,
                temperature=0.2,
            )
            self._structured_llm = llm.with_structured_output(SeverityOutput)
            logger.info("SeverityAgent initialized with %s.", settings.gemini_model)
        except Exception as exc:
            logger.warning("SeverityAgent LLM init failed: %s. Using fallback.", exc)

    async def score(
        self,
        event_type: str,
        geography: str,
        affected_nodes: list[str],
        raw_signal: str,
        affected_trade_routes: list[str],
    ) -> SeverityOutput:
        all_shipments = get_all_shipments()

        context = (
            "Supply network: configured customer supply network.\n"
            f"Total active shipments: {len(all_shipments)}\n"
            f"Affected network nodes: {', '.join(affected_nodes) if affected_nodes else 'unknown'}\n"
            f"Event type: {event_type}\n"
            f"Affected geography: {geography}\n"
            f"Trade routes at risk: {', '.join(affected_trade_routes) if affected_trade_routes else 'unknown'}\n"
        )

        if self._structured_llm is None:
            return self._heuristic_fallback(event_type, geography, len(affected_nodes))

        prompt = (
            "You are a supply chain risk expert scoring disruption severity. "
            "Score on a scale from 1.0 (minor) to 10.0 (catastrophic). "
            "Consider delay risk, exposure breadth, and cost impact.\n\n"
            f"Network context:\n{context}\n\n"
            f"Raw signal:\n{raw_signal[:1000]}"
        )

        try:
            result: SeverityOutput = await self._structured_llm.ainvoke(prompt)
            logger.info(
                "Severity scored: %.1f/10 affected_shipments=%d delay=%.1fd cost=$%.0f",
                result.severity_score,
                result.affected_shipment_count,
                result.estimated_delay_days,
                result.estimated_cost_impact_usd,
            )
            return result
        except Exception as exc:
            logger.warning("LLM severity scoring failed: %s. Using heuristic.", exc)
            return self._heuristic_fallback(event_type, geography, len(affected_nodes))

    def _heuristic_fallback(
        self, event_type: str, geography: str, node_count: int
    ) -> SeverityOutput:
        score_map = {
            "trade_route_disruption": 8.0,
            "factory_fire": 7.5,
            "extreme_weather": 6.5,
            "port_congestion": 5.0,
            "geopolitical_event": 8.0,
            "cyber_attack": 7.0,
            "labor_strike": 5.5,
            "regulatory_action": 4.0,
            "unknown": 3.0,
        }
        base_score = score_map.get(event_type, 3.0)
        shipment_count = max(1, len(get_all_shipments()))
        impacted_count = max(node_count, 1)
        delay_days = round(max(1.0, base_score * 0.9), 1)
        cost_impact = float(int(base_score * impacted_count * shipment_count * 2500))

        return SeverityOutput(
            severity_score=base_score,
            reasoning=(
                f"Heuristic scoring: {event_type} at {geography}. "
                f"Base score {base_score}/10 for this event type. "
                f"{node_count} supplier nodes affected."
            ),
            affected_shipment_count=impacted_count,
            estimated_delay_days=delay_days,
            estimated_cost_impact_usd=cost_impact,
        )


_severity_instance: Optional[SeverityAgent] = None


def get_severity_agent() -> SeverityAgent:
    global _severity_instance
    if _severity_instance is None:
        _severity_instance = SeverityAgent()
    return _severity_instance
