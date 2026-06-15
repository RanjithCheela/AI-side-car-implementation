import time
import logging
from shared.models import LoanApplicationRequest, FirewallResponse, Action
from shared.database import ApplicationLog, AuditEvent
from services.context_enrichment.service import ContextEnrichmentService
from services.ai_risk_engine.engine import AIRiskEngine
from services.policy_engine.pdp import PolicyDecisionPoint
from services.policy_engine.pep import PolicyEnforcementPoint
from services.kafka_producer.producer import KafkaEventProducer
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AISidecar:
    """
    Orchestrates the full intent firewall pipeline:
    1. Context Enrichment  → behavioral, geo, KYC/AML signals
    2. AI Risk Assessment  → Claude evaluates fraud intent
    3. Policy Decision     → rule-based action (ALLOW/BLOCK/ESCALATE/CHALLENGE)
    4. Policy Enforcement  → builds final response
    5. Kafka Publishing    → notifies downstream services
    6. Audit Persistence   → writes to PostgreSQL
    """

    def __init__(self):
        self.context_service = ContextEnrichmentService()
        self.risk_engine = AIRiskEngine()
        self.pdp = PolicyDecisionPoint()
        self.pep = PolicyEnforcementPoint()
        self.kafka = KafkaEventProducer()

    async def process(self, application: LoanApplicationRequest, db: AsyncSession) -> FirewallResponse:
        start = time.perf_counter()
        app_id = application.application_id
        logger.info(f"[{app_id}] Received loan application — customer={application.applicant.customer_id}")

        # ── 1. Context Enrichment ─────────────────────────────────────────────
        context = await self.context_service.enrich(application)
        await self._audit(db, app_id, "CONTEXT_ENRICHED", {
            "behavior": context.behavior.model_dump(),
            "device_geo": context.device_geo.model_dump(),
            "kyc_aml": context.kyc_aml.model_dump(),
        })

        # ── 2. AI Risk Assessment ─────────────────────────────────────────────
        risk = self.risk_engine.assess_risk(application, context)
        logger.info(f"[{app_id}] Risk assessed — score={risk.risk_score} level={risk.risk_level} intent={risk.intent}")
        await self._audit(db, app_id, "RISK_ASSESSED", {
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level.value,
            "intent": risk.intent.value,
            "confidence": risk.confidence,
            "fraud_indicators": risk.fraud_indicators,
        })

        # ── 3. Policy Decision ────────────────────────────────────────────────
        policy_ctx = {
            "sanctions_list": context.kyc_aml.sanctions_list,
            "aml_flagged": context.kyc_aml.aml_status == "flagged",
            "kyc_verified": context.kyc_aml.kyc_verified,
        }
        decision = self.pdp.decide(risk, policy_ctx)
        logger.info(f"[{app_id}] Policy decision — action={decision.action} rule={decision.policy_rule}")

        # ── 4. Policy Enforcement ─────────────────────────────────────────────
        elapsed_ms = (time.perf_counter() - start) * 1000
        response = self.pep.enforce(app_id, risk, decision, elapsed_ms)

        # ── 5. Kafka Publishing ───────────────────────────────────────────────
        try:
            self.kafka.publish_decision(response, application)
        except Exception as e:
            logger.error(f"[{app_id}] Kafka publish failed (non-fatal): {e}")

        # ── 6. Persist to PostgreSQL ──────────────────────────────────────────
        await self._persist(db, application, response)

        if response.action in (Action.BLOCK, Action.ESCALATE):
            await self.context_service.flag_fraud(application.applicant.customer_id)

        logger.info(f"[{app_id}] Completed in {elapsed_ms:.0f}ms — final_action={response.action}")
        return response

    async def _audit(self, db: AsyncSession, application_id: str, event_type: str, data: dict):
        db.add(AuditEvent(application_id=application_id, event_type=event_type, event_data=data))
        await db.commit()

    async def _persist(self, db: AsyncSession, application: LoanApplicationRequest, response: FirewallResponse):
        db.add(ApplicationLog(
            application_id=response.application_id,
            customer_id=application.applicant.customer_id,
            loan_amount=application.loan.amount,
            action=response.action.value,
            risk_score=response.risk_assessment.risk_score,
            risk_level=response.risk_assessment.risk_level.value,
            intent=response.risk_assessment.intent.value,
            policy_rule=response.policy_decision.policy_rule,
            fraud_indicators=response.risk_assessment.fraud_indicators,
            processing_time_ms=response.processing_time_ms,
            full_response=response.model_dump(mode="json"),
        ))
        await db.commit()

    async def close(self):
        await self.context_service.close()
        self.kafka.close()
