"""
DisruptionService — orchestrates the full signal→decision pipeline.
Called by scheduler (automated) and POST /disruptions/trigger (manual).
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentState, run_pipeline
from app.config import get_settings
from app.engine.confidence import ConfidenceEvaluator
from app.engine.executor import Executor
from app.engine.scenario_gen import ScenarioGenerator
from app.graph.network_store import get_all_shipments
from app.engine.tradeoff import TradeoffScorer
from app.models.decision import Decision
from app.models.disruption import Disruption
from app.models.scenario import Scenario
from app.schemas.task import TaskCreate
from app.services.supplier_svc import SupplierService
from app.services.task_svc import TaskService

logger = logging.getLogger(__name__)
settings = get_settings()


class DisruptionService:
    """
    Full pipeline: signal → agents → scenarios → confidence → execute/escalate.
    All DB writes happen inside a single transaction (get_db() commits on exit).
    """

    @staticmethod
    async def process_signal(
        signal: dict,
        db: AsyncSession,
        company_id: str | None = None,
    ) -> Optional[Disruption]:
        """
        Process a raw signal through the full agent + decision pipeline.

        Args:
            signal    : Normalized signal dict (from live/manual ingestion sources)
            db        : Async SQLAlchemy session
            company_id: Company identifier

        Returns:
            Created Disruption ORM object, or None if processing failed.
        """
        company_id = company_id or settings.company_id
        raw_text = signal.get("text", signal.get("title", ""))
        if not raw_text:
            logger.warning("Signal has no text content. Skipping.")
            return None

        logger.info(
            "Processing signal: source=%s severity=%.1f",
            signal.get("source"), signal.get("severity", 0)
        )

        # ── Step 1: Create Disruption record in DB ─────────────────────────────
        disruption = Disruption(
            status="processing",
            raw_signal=raw_text,
        )
        db.add(disruption)
        await db.flush()  # Get disruption.id
        disruption_id = disruption.id
        logger.info("Disruption created: id=%s", disruption_id)

        # ── Step 2: Run agent pipeline ─────────────────────────────────────────
        agent_state: AgentState = await run_pipeline(
            raw_signal=raw_text,
            source=signal.get("source", "unknown"),
            company_id=company_id,
        )

        if agent_state.get("pipeline_error"):
            disruption.status = "error"
            logger.error(
                "Pipeline error for disruption %s: %s",
                disruption_id, agent_state["pipeline_error"]
            )
            await db.flush()
            return disruption

        # ── Step 3: Update Disruption with agent results ───────────────────────
        disruption.event_type = agent_state.get("event_type")
        disruption.geography = agent_state.get("geography")
        disruption.severity_score = agent_state.get("severity_score")
        disruption.affected_nodes = agent_state.get("affected_nodes", [])
        disruption.cascade_nodes = agent_state.get("cascade_nodes", [])
        await db.flush()

        # ── Step 4: Generate 3 scenarios ──────────────────────────────────────
        scenario_gen = ScenarioGenerator()
        raw_scenarios = await scenario_gen.generate(agent_state)
        candidate_suppliers = await DisruptionService._find_supplier_candidates(
            agent_state=agent_state,
            company_id=company_id,
            db=db,
        )
        raw_scenarios = DisruptionService._enrich_scenarios_with_supplier_context(
            raw_scenarios=raw_scenarios,
            agent_state=agent_state,
            candidate_suppliers=candidate_suppliers,
        )

        # ── Step 5: Score tradeoffs ────────────────────────────────────────────
        scorer = TradeoffScorer()
        scored_scenarios = scorer.score(raw_scenarios)

        # ── Step 6: Save scenarios to DB ──────────────────────────────────────
        scenario_records: list[Scenario] = []
        for scored in scored_scenarios:
            opt = scored.option
            rec = Scenario(
                disruption_id=disruption_id,
                option_index=opt.option_index,
                label=opt.label,
                description=opt.description,
                cost_delta_usd=opt.cost_delta_usd,
                time_delta_days=opt.time_delta_days,
                risk_score=opt.risk_score,
                composite_score=scored.composite_score,
                recommended=scored.recommended,
            )
            db.add(rec)
            scenario_records.append(rec)
        await db.flush()

        # ── Step 7: Evaluate confidence ────────────────────────────────────────
        recommended_scored = next(s for s in scored_scenarios if s.recommended)
        evaluator = ConfidenceEvaluator()
        confidence_result = evaluator.evaluate(
            recommended=recommended_scored,
            all_scenarios=scored_scenarios,
            agent_state=agent_state,
        )

        # ── Step 8: Create Decision record ────────────────────────────────────
        recommended_record = next(r for r in scenario_records if r.recommended)
        decision = Decision(
            disruption_id=disruption_id,
            scenario_id=recommended_record.id,
            confidence_score=confidence_result.confidence,
            status="pending",
        )
        db.add(decision)
        await db.flush()
        decision_id = decision.id

        # ── Step 9: Execute or escalate ───────────────────────────────────────
        executor = Executor()
        exec_result = await executor.execute(
            disruption_id=disruption_id,
            decision_id=decision_id,
            confidence_result=confidence_result,
            recommended_scenario=recommended_scored,
            agent_state=agent_state,
            db=db,
            company_id=company_id,
        )

        # ── Step 10: Update Disruption status ─────────────────────────────────
        disruption.status = (
            "resolved" if exec_result.auto_executed else "escalated"
        )
        disruption.updated_at = datetime.now(timezone.utc)
        await db.flush()

        logger.info(
            "Disruption %s complete: status=%s confidence=%.2f",
            disruption_id, disruption.status, confidence_result.confidence
        )
        await DisruptionService._create_operational_tasks(
            disruption=disruption,
            agent_state=agent_state,
            company_id=company_id,
            auto_executed=exec_result.auto_executed,
            decision_id=decision_id,
            candidate_suppliers=candidate_suppliers,
            db=db,
        )

        return disruption

    @staticmethod
    async def get_by_id(
        disruption_id: uuid.UUID, db: AsyncSession
    ) -> Optional[Disruption]:
        """Fetch single disruption by ID with scenarios eager-loaded."""
        from sqlalchemy import select
        result = await db.execute(
            select(Disruption).where(Disruption.id == disruption_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_paginated(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Disruption], int]:
        """Paginated list of disruptions, newest first."""
        from sqlalchemy import select, func, desc
        count_result = await db.execute(select(func.count(Disruption.id)))
        total = count_result.scalar() or 0

        result = await db.execute(
            select(Disruption)
            .order_by(desc(Disruption.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def _find_supplier_candidates(
        agent_state: AgentState,
        company_id: str,
        db: AsyncSession,
    ) -> list:
        affected_nodes = set(agent_state.get("affected_nodes", [])) | set(agent_state.get("cascade_nodes", []))
        impacted_shipments = [
            shipment for shipment in get_all_shipments()
            if any(node in affected_nodes for node in shipment.get("route", []))
        ]
        materials = [str(shipment.get("material", "")).strip() for shipment in impacted_shipments if shipment.get("material")]
        modes = [str(shipment.get("mode", "")).strip() for shipment in impacted_shipments if shipment.get("mode")]
        return await SupplierService.find_candidates(
            db=db,
            materials=materials,
            modes=modes,
            company_id=company_id,
        )

    @staticmethod
    def _enrich_scenarios_with_supplier_context(
        raw_scenarios,
        agent_state: AgentState,
        candidate_suppliers: list,
    ):
        impacted_shipments = [
            shipment for shipment in get_all_shipments()
            if shipment.get("id") in set(agent_state.get("affected_shipment_ids", []))
        ]
        materials = sorted({
            str(shipment.get("material")).strip()
            for shipment in impacted_shipments
            if shipment.get("material")
        })
        modes = sorted({
            str(shipment.get("mode")).strip()
            for shipment in impacted_shipments
            if shipment.get("mode")
        })
        top_supplier = candidate_suppliers[0] if candidate_suppliers else None
        preferred_modes = [
            entry.get("mode")
            for entry in getattr(top_supplier, "lane_preferences", [])
            if isinstance(entry, dict) and entry.get("mode")
        ] if top_supplier else []

        for option in raw_scenarios:
            if "backup supplier" in option.label.lower() and top_supplier:
                option.label = f"Activate backup supplier: {top_supplier.legal_name}"
                option.description = (
                    f"Shift replenishment for {', '.join(materials) or 'critical materials'} to "
                    f"{top_supplier.legal_name} in {top_supplier.country}. "
                    f"Registered modes: {', '.join(preferred_modes) or 'not specified'}."
                )
                option.time_delta_days = max(1.0, round(option.time_delta_days * 0.8, 1))
                option.risk_score = max(1.0, round(option.risk_score - 0.6, 1))
            elif "reroute" in option.label.lower() and modes:
                option.description = (
                    f"{option.description} Impacted shipment modes: {', '.join(modes)}. "
                    f"Prioritize alternate lanes that preserve cold-chain handling for {', '.join(materials) or 'affected SKUs'}."
                )
            elif "expedite" in option.label.lower() and materials:
                option.description = (
                    f"{option.description} Recommended for materials: {', '.join(materials)}."
                )
                if "air" in modes:
                    option.time_delta_days = max(1.0, round(option.time_delta_days * 0.85, 1))

        return raw_scenarios

    @staticmethod
    async def _create_operational_tasks(
        disruption: Disruption,
        agent_state: AgentState,
        company_id: str,
        auto_executed: bool,
        decision_id: uuid.UUID,
        candidate_suppliers: list,
        db: AsyncSession,
    ) -> None:
        priority = "critical" if (agent_state.get("severity_score") or 0) >= 8 else "high"
        payloads = [
            TaskCreate(
                company_id=company_id,
                title=f"Triage disruption at {disruption.geography or 'unknown geography'}",
                description=(
                    f"Review {disruption.event_type} severity {disruption.severity_score}/10. "
                    f"Affected nodes: {', '.join(disruption.affected_nodes or []) or 'none'}."
                ),
                priority=priority,
                task_type="triage",
                status="open",
                disruption_id=disruption.id,
                metadata_json={
                    "decision_id": str(decision_id),
                    "cascade_nodes": disruption.cascade_nodes or [],
                },
            )
        ]

        if auto_executed:
            payloads.append(
                TaskCreate(
                    company_id=company_id,
                    title=f"Monitor execution outcome for {disruption.geography or 'disruption'}",
                    description="Validate ERP updates, ETA changes, and downstream confirmations after automatic execution.",
                    priority="high",
                    task_type="execution_monitor",
                    status="open",
                    disruption_id=disruption.id,
                    metadata_json={"decision_id": str(decision_id), "auto_executed": True},
                )
            )
        else:
            payloads.append(
                TaskCreate(
                    company_id=company_id,
                    title=f"Approve escalation for {disruption.geography or 'disruption'}",
                    description="Human review required because confidence fell below the auto-execution threshold.",
                    priority="critical",
                    task_type="approval",
                    status="open",
                    disruption_id=disruption.id,
                    metadata_json={"decision_id": str(decision_id), "auto_executed": False},
                )
            )

        if candidate_suppliers:
            supplier = candidate_suppliers[0]
            payloads.append(
                TaskCreate(
                    company_id=company_id,
                    title=f"Confirm backup readiness with {supplier.legal_name}",
                    description=(
                        f"Validate material availability and lane readiness with registered supplier "
                        f"{supplier.supplier_code}."
                    ),
                    priority="high",
                    task_type="supplier_coordination",
                    status="open",
                    disruption_id=disruption.id,
                    supplier_id=supplier.id,
                    metadata_json={
                        "materials": supplier.material_profiles,
                        "lanes": supplier.lane_preferences,
                    },
                )
            )

        await TaskService.create_many(payloads, db)
