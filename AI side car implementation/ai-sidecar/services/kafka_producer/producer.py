from confluent_kafka import Producer
from shared.models import FirewallResponse, LoanApplicationRequest, Action
from config import settings
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    def __init__(self):
        self._producer = Producer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "client.id": "bfsi-ai-sidecar",
            "acks": "all",
            "retries": 3,
        })

    def publish_decision(self, response: FirewallResponse, application: LoanApplicationRequest):
        now = datetime.now(timezone.utc).isoformat()
        base_event = {
            "event_type": f"LOAN_{response.action.value}",
            "application_id": response.application_id,
            "action": response.action.value,
            "risk_score": response.risk_assessment.risk_score,
            "risk_level": response.risk_assessment.risk_level.value,
            "intent": response.risk_assessment.intent.value,
            "confidence": response.risk_assessment.confidence,
            "fraud_indicators": response.risk_assessment.fraud_indicators,
            "policy_rule": response.policy_decision.policy_rule,
            "reason": response.policy_decision.reason,
            "requires_manual_review": response.policy_decision.requires_manual_review,
            "requires_verification": response.policy_decision.requires_verification,
            "verification_type": response.policy_decision.verification_type,
            "applicant_name": application.applicant.name,
            "applicant_email": application.applicant.email,
            "applicant_customer_id": application.applicant.customer_id,
            "loan_amount": application.loan.amount,
            "loan_purpose": application.loan.purpose,
            "timestamp": now,
        }

        # decisions topic — consumed by analytics/audit
        self._produce(settings.kafka_topic_decisions, response.application_id, base_event)

        # notification topic — consumed by notification-service (Java)
        notification_event = {
            **base_event,
            "next_steps": response.next_steps,
            "message": response.message,
            "stakeholder_emails": (
                settings.get_fraud_team_emails()
                if response.action in (Action.BLOCK, Action.ESCALATE)
                else []
            ),
        }
        self._produce(settings.kafka_topic_notifications, response.application_id, notification_event)

        # allowed topic — consumed by loan-origination-service (Java)
        if response.action == Action.ALLOW:
            loan_event = {
                **base_event,
                "loan_details": {
                    "amount": application.loan.amount,
                    "purpose": application.loan.purpose,
                    "tenure_months": application.loan.tenure_months,
                    "monthly_income": application.loan.monthly_income,
                    "employment_type": application.loan.employment_type,
                    "employer_name": application.loan.employer_name,
                },
                "applicant_details": {
                    "customer_id": application.applicant.customer_id,
                    "name": application.applicant.name,
                    "email": application.applicant.email,
                    "phone": application.applicant.phone,
                    "national_id": application.applicant.national_id,
                    "address": application.applicant.address,
                },
            }
            self._produce(settings.kafka_topic_allowed, response.application_id, loan_event)

        # escalations topic — consumed by risk management system
        if response.action == Action.ESCALATE:
            self._produce(settings.kafka_topic_escalations, response.application_id, {
                **base_event,
                "reasoning": response.risk_assessment.reasoning,
                "free_text_analysis": response.risk_assessment.free_text_analysis,
            })

        self._producer.flush(timeout=5)

    def _produce(self, topic: str, key: str, payload: dict):
        try:
            self._producer.produce(
                topic=topic,
                key=key.encode("utf-8"),
                value=json.dumps(payload, default=str).encode("utf-8"),
                callback=self._on_delivery,
            )
        except Exception as e:
            logger.error(f"Failed to produce to {topic}: {e}")

    @staticmethod
    def _on_delivery(err, msg):
        if err:
            logger.error(f"Kafka delivery failed [{msg.topic()}]: {err}")
        else:
            logger.debug(f"Delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

    def close(self):
        self._producer.flush(timeout=10)
