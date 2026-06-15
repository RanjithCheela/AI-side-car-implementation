from shared.models import FirewallResponse, RiskAssessment, PolicyDecision, Action
from datetime import datetime


class PolicyEnforcementPoint:
    """Translates a policy decision into the final FirewallResponse sent to the caller."""

    _MESSAGES = {
        Action.ALLOW: "Application approved — forwarded to loan processing.",
        Action.BLOCK: "Application rejected — fraud risk exceeds acceptable threshold.",
        Action.ESCALATE: "Application placed on hold — escalated for manual fraud review.",
        Action.CHALLENGE: "Application paused — additional identity verification required.",
    }

    _NEXT_STEPS = {
        Action.ALLOW: [
            "Application forwarded to Loan Origination Service via Kafka",
            "Applicant notified via SMS/email: approval in progress",
            "Loan offer generated within 2 business hours",
        ],
        Action.BLOCK: [
            "Application permanently rejected",
            "Fraud alert raised and logged in risk management system",
            "Fraud operations team notified by email",
            "Applicant notified: application unsuccessful (no fraud reason disclosed)",
            "Customer flagged in behavioral risk system for 90 days",
        ],
        Action.ESCALATE: [
            "Application placed in fraud analyst review queue",
            "Fraud analyst and branch manager notified by email",
            "Application held for up to 48 working hours",
            "Applicant notified: application under review",
            "Compliance team alerted if AML-related",
        ],
        Action.CHALLENGE: [
            "Applicant notified via SMS/email with verification link",
            "72-hour window opened for verification completion",
            "Loan processing resumes automatically upon successful verification",
            "Application auto-escalates if verification not completed in 72 hours",
        ],
    }

    def enforce(
        self,
        application_id: str,
        risk: RiskAssessment,
        decision: PolicyDecision,
        processing_time_ms: float,
    ) -> FirewallResponse:
        action = decision.action
        next_steps = list(self._NEXT_STEPS.get(action, []))

        if decision.requires_verification and decision.verification_type:
            next_steps.insert(0, f"Verification method required: {decision.verification_type.upper()}")

        return FirewallResponse(
            application_id=application_id,
            timestamp=datetime.utcnow(),
            action=action,
            risk_assessment=risk,
            policy_decision=decision,
            message=self._MESSAGES.get(action, "Unknown action"),
            next_steps=next_steps,
            processing_time_ms=processing_time_ms,
        )
