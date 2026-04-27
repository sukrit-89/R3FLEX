"""
Executor executes autonomous decisions or escalates them to human review.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentState
from app.config import get_settings
from app.engine.confidence import ConfidenceResult
from app.engine.tradeoff import ScoredScenario

logger = logging.getLogger(__name__)
settings = get_settings()


class ExecutionResult:
    def __init__(
        self,
        auto_executed: bool,
        status: str,
        message: str,
        erp_log: Optional[str] = None,
        supplier_email_draft: Optional[str] = None,
    ) -> None:
        self.auto_executed = auto_executed
        self.status = status
        self.message = message
        self.erp_log = erp_log
        self.supplier_email_draft = supplier_email_draft

    def to_dict(self) -> dict:
        return {
            "auto_executed": self.auto_executed,
            "status": self.status,
            "message": self.message,
            "erp_log": self.erp_log,
            "supplier_email_draft": self.supplier_email_draft,
        }


class Executor:
    async def execute(
        self,
        disruption_id: uuid.UUID,
        decision_id: uuid.UUID,
        confidence_result: ConfidenceResult,
        recommended_scenario: ScoredScenario,
        agent_state: AgentState,
        db: AsyncSession,
        company_id: str = "default",
    ) -> ExecutionResult:
        if confidence_result.above_threshold:
            return await self._auto_execute(
                disruption_id=disruption_id,
                decision_id=decision_id,
                confidence_result=confidence_result,
                recommended_scenario=recommended_scenario,
                agent_state=agent_state,
                db=db,
            )

        return await self._escalate_to_human(
            disruption_id=disruption_id,
            decision_id=decision_id,
            confidence_result=confidence_result,
            recommended_scenario=recommended_scenario,
            agent_state=agent_state,
            db=db,
            company_id=company_id,
        )

    async def _auto_execute(
        self,
        disruption_id: uuid.UUID,
        decision_id: uuid.UUID,
        confidence_result: ConfidenceResult,
        recommended_scenario: ScoredScenario,
        agent_state: AgentState,
        db: AsyncSession,
    ) -> ExecutionResult:
        logger.info(
            "AUTO-EXECUTE: disruption=%s decision=%s confidence=%.2f",
            disruption_id, decision_id, confidence_result.confidence
        )

        option = recommended_scenario.option

        from app.services.audit_svc import AuditService

        await AuditService.log(
            action_type="auto_execute",
            disruption_id=disruption_id,
            decision_id=decision_id,
            reasoning=(
                f"{confidence_result.reasoning}\n\n"
                f"Executing: {option.label}\n"
                f"Cost delta: ${option.cost_delta_usd:,.0f} | "
                f"Time delta: +{option.time_delta_days:.0f} days | "
                f"Risk score: {option.risk_score:.1f}/10"
            ),
            signals_used={
                "news": agent_state.get("source") == "news",
                "weather": agent_state.get("source") == "weather",
                "port": agent_state.get("source") == "port",
            },
            confidence_score=confidence_result.confidence,
            actor="agent",
            db=db,
        )

        erp_log = self._generate_erp_log(option, agent_state, disruption_id)
        email_draft = self._draft_supplier_email(option, agent_state)

        from app.models.decision import Decision
        from sqlalchemy import select

        result = await db.execute(select(Decision).where(Decision.id == decision_id))
        decision = result.scalar_one_or_none()
        if decision:
            decision.status = "executed"
            decision.auto_executed = True
            decision.executed_at = datetime.now(timezone.utc)
            decision.outcome = f"Auto-executed: {option.label}"
            await db.flush()

        return ExecutionResult(
            auto_executed=True,
            status="executed",
            message=(
                f"Autonomously executed: {option.label}. "
                f"Confidence was {confidence_result.confidence:.0%} "
                f"(threshold {confidence_result.threshold_used:.0%}). "
                "Full reasoning saved to audit log."
            ),
            erp_log=erp_log,
            supplier_email_draft=email_draft,
        )

    async def _escalate_to_human(
        self,
        disruption_id: uuid.UUID,
        decision_id: uuid.UUID,
        confidence_result: ConfidenceResult,
        recommended_scenario: ScoredScenario,
        agent_state: AgentState,
        db: AsyncSession,
        company_id: str,
    ) -> ExecutionResult:
        logger.info(
            "ESCALATING TO HUMAN: disruption=%s confidence=%.2f threshold=%.2f",
            disruption_id, confidence_result.confidence, confidence_result.threshold_used
        )

        from app.services.audit_svc import AuditService

        await AuditService.log(
            action_type="escalate_human",
            disruption_id=disruption_id,
            decision_id=decision_id,
            reasoning=confidence_result.reasoning,
            signals_used={
                "news": agent_state.get("source") == "news",
                "weather": agent_state.get("source") == "weather",
                "port": agent_state.get("source") == "port",
            },
            confidence_score=confidence_result.confidence,
            actor="agent",
            db=db,
        )

        channel = f"disruptions:{company_id}"
        payload = {
            "event": "approval_required",
            "disruption_id": str(disruption_id),
            "decision_id": str(decision_id),
            "confidence": confidence_result.confidence,
            "threshold": confidence_result.threshold_used,
            "confidence_breakdown": confidence_result.breakdown,
            "recommended_scenario": {
                "option_index": recommended_scenario.option.option_index,
                "label": recommended_scenario.option.label,
                "description": recommended_scenario.option.description,
                "cost_delta_usd": recommended_scenario.option.cost_delta_usd,
                "time_delta_days": recommended_scenario.option.time_delta_days,
                "risk_score": recommended_scenario.option.risk_score,
            },
            "risk_summary": agent_state.get("risk_summary", ""),
            "severity_score": agent_state.get("severity_score", 0),
            "geography": agent_state.get("geography", ""),
        }

        try:
            from app.redis_client import publish

            await publish(channel, payload)
            logger.info("Published approval_required to Redis channel '%s'.", channel)
        except Exception as exc:
            logger.error("Redis publish failed: %s. Decision still escalated.", exc)

        return ExecutionResult(
            auto_executed=False,
            status="pending_approval",
            message=(
                f"Confidence {confidence_result.confidence:.0%} below threshold "
                f"{confidence_result.threshold_used:.0%}. "
                "Escalated to human approval. Check WebSocket or /decisions endpoint."
            ),
        )

    def _generate_erp_log(
        self,
        option,
        agent_state: AgentState,
        disruption_id: uuid.UUID,
    ) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        return (
            f"[ERP UPDATE | {timestamp}]\n"
            f"Disruption ID: {disruption_id}\n"
            f"Action: {option.label}\n"
            f"Trigger: {agent_state.get('event_type')} at {agent_state.get('geography')}\n"
            f"Severity: {agent_state.get('severity_score')}/10\n"
            f"Affected shipments: {', '.join(agent_state.get('affected_shipment_ids', []))}\n"
            f"Cost delta: +${option.cost_delta_usd:,.0f}\n"
            f"ETA delta: +{option.time_delta_days:.0f} days\n"
            f"Status: EXECUTED_BY_AGENT\n"
            "Next ERP sync: PENDING_CONFIRMATION"
        )

    def _draft_supplier_email(self, option, agent_state: AgentState) -> str:
        is_backup = "backup" in option.label.lower()

        if is_backup:
            recipient = "operations@backup-supplier.example"
            subject = "URGENT: Backup Supply Activation Request"
            body = (
                "Dear Operations Team,\n\n"
                f"Due to a critical supply chain disruption ({agent_state.get('event_type')} at "
                f"{agent_state.get('geography')}, severity {agent_state.get('severity_score')}/10), "
                "we are activating your facility as a backup supply option effective immediately.\n\n"
                "Please confirm fulfillment readiness and earliest possible ship date.\n\n"
                "This is an automated notification from the R3flex AI system.\n\n"
                f"Reference: Disruption ID {agent_state.get('source', 'auto')}-"
                f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}\n\n"
                "Best regards,\nR3flex Automated Operations"
            )
        else:
            recipient = "logistics@carrier.example.com"
            subject = f"URGENT: Rerouting Request - {option.label}"
            body = (
                f"Due to supply chain disruption at {agent_state.get('geography')}, "
                f"we are implementing: {option.label}.\n\n"
                "Please acknowledge receipt and confirm implementation timeline. "
                f"Affected shipments: {', '.join(agent_state.get('affected_shipment_ids', []))}."
            )

        return f"TO: {recipient}\nSUBJECT: {subject}\n\n{body}"
