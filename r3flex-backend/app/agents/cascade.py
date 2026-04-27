"""
Cascade Agent simulates second-order downstream impact.
"""
import logging
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.graph.supplier_graph import get_supplier_graph

logger = logging.getLogger(__name__)
settings = get_settings()


class CascadeOutput(BaseModel):
    cascade_nodes: list[str] = Field(default_factory=list)
    cascade_depth: int = Field(ge=2)
    risk_summary: str
    secondary_bottlenecks: list[str] = Field(default_factory=list)
    stock_out_risk_nodes: list[str] = Field(default_factory=list)


class CascadeAgent:
    def __init__(self) -> None:
        self._llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        if not settings.google_api_key:
            logger.warning("GOOGLE_API_KEY not set. CascadeAgent will use template summary.")
            return
        try:
            self._llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.google_api_key,
                max_output_tokens=settings.llm_max_tokens,
                temperature=0.3,
            )
            logger.info("CascadeAgent initialized with %s.", settings.gemini_model)
        except Exception as exc:
            logger.warning("CascadeAgent LLM init failed: %s", exc)

    async def simulate(
        self,
        primary_node: str,
        event_type: str,
        severity_score: float,
        geography: str,
    ) -> CascadeOutput:
        graph = get_supplier_graph()

        if primary_node == "unknown" or not primary_node:
            logger.warning("Cascade simulation skipped - unknown primary node.")
            return CascadeOutput(
                cascade_nodes=[],
                cascade_depth=2,
                risk_summary="Unable to simulate cascade because the disruption node could not be identified.",
                secondary_bottlenecks=[],
                stock_out_risk_nodes=[],
            )

        cascade_2 = graph.get_cascade_nodes(primary_node, hops=2)
        cascade_1 = graph.get_cascade_nodes(primary_node, hops=1)
        all_cascade = list(set(cascade_1 + cascade_2))

        secondary_bottlenecks = [
            node_id for node_id in cascade_1 if len(graph.get_cascade_nodes(node_id, hops=1)) > 1
        ]

        stock_out_risk = []
        if severity_score >= 7.0:
            for node_id in all_cascade:
                node = graph.get_node(node_id)
                if not node:
                    continue
                buffer_days = node.get("current_stock_days")
                if buffer_days is not None and buffer_days < max(7, severity_score):
                    stock_out_risk.append(node_id)

        risk_summary = await self._generate_narrative(
            primary_node=primary_node,
            cascade_nodes=all_cascade,
            secondary_bottlenecks=secondary_bottlenecks,
            stock_out_risk=stock_out_risk,
            event_type=event_type,
            severity_score=severity_score,
            geography=geography,
            graph=graph,
        )

        return CascadeOutput(
            cascade_nodes=all_cascade,
            cascade_depth=2,
            risk_summary=risk_summary,
            secondary_bottlenecks=secondary_bottlenecks,
            stock_out_risk_nodes=stock_out_risk,
        )

    async def _generate_narrative(
        self,
        primary_node: str,
        cascade_nodes: list[str],
        secondary_bottlenecks: list[str],
        stock_out_risk: list[str],
        event_type: str,
        severity_score: float,
        geography: str,
        graph,
    ) -> str:
        def node_name(node_id: str) -> str:
            node = graph.get_node(node_id)
            return node.get("name", node_id) if node else node_id

        cascade_named = [node_name(node_id) for node_id in cascade_nodes]
        bottleneck_named = [node_name(node_id) for node_id in secondary_bottlenecks]
        stock_named = [node_name(node_id) for node_id in stock_out_risk]
        primary_named = node_name(primary_node)

        if self._llm is None:
            return self._template_narrative(
                primary_named, cascade_named, bottleneck_named, stock_named, severity_score
            )

        prompt = (
            f"You are analyzing cascade effects in a supply chain.\n"
            f"Primary disruption: {event_type} at {geography} (severity {severity_score}/10)\n"
            f"Disrupted node: {primary_named}\n"
            f"Second-order affected nodes: {', '.join(cascade_named) or 'none'}\n"
            f"Secondary bottlenecks: {', '.join(bottleneck_named) or 'none'}\n"
            f"Stock-out risk nodes: {', '.join(stock_named) or 'none'}\n\n"
            "Write a 3-sentence risk summary covering the disruption, downstream impact, and most urgent action."
        )

        try:
            response = await self._llm.ainvoke(prompt)
            return response.content.strip()
        except Exception as exc:
            logger.warning("LLM narrative generation failed: %s", exc)
            return self._template_narrative(
                primary_named, cascade_named, bottleneck_named, stock_named, severity_score
            )

    def _template_narrative(
        self,
        primary: str,
        cascade: list[str],
        bottlenecks: list[str],
        stock_out: list[str],
        severity: float,
    ) -> str:
        cascade_str = ", ".join(cascade[:3]) if cascade else "no downstream nodes"
        bottleneck_str = ", ".join(bottlenecks) if bottlenecks else "none identified"
        stock_str = ", ".join(stock_out) if stock_out else "no immediate stock-out risk"

        return (
            f"{primary} is disrupted (severity {severity:.1f}/10), directly impacting {cascade_str}. "
            f"Secondary bottlenecks: {bottleneck_str}. "
            f"Stock-out risk: {stock_str}; immediate rerouting assessment is recommended."
        )


_cascade_instance: Optional[CascadeAgent] = None


def get_cascade_agent() -> CascadeAgent:
    global _cascade_instance
    if _cascade_instance is None:
        _cascade_instance = CascadeAgent()
    return _cascade_instance
