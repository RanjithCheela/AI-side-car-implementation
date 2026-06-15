from shared.models import RiskAssessment, PolicyDecision, Action, RiskLevel, Intent


class PolicyDecisionPoint:
    """
    Evaluates risk assessments against ordered policy rules.
    First matching rule wins — order matters (hardest blocks first).
    """

    POLICIES = [
        {
            "rule": "BLOCK_SANCTIONS_MATCH",
            "condition": lambda r, ctx: ctx.get("sanctions_list", False),
            "action": Action.BLOCK,
            "reason": "Applicant matches OFAC/UN/domestic sanctions list",
            "manual_review": False,
            "verification": False,
        },
        {
            "rule": "BLOCK_CRITICAL_RISK",
            "condition": lambda r, ctx: r.risk_score >= 85,
            "action": Action.BLOCK,
            "reason": "Critical risk score — automatic rejection",
            "manual_review": False,
            "verification": False,
        },
        {
            "rule": "BLOCK_SYNTHETIC_IDENTITY",
            "condition": lambda r, ctx: r.intent == Intent.SYNTHETIC_IDENTITY and r.confidence >= 0.80,
            "action": Action.BLOCK,
            "reason": "High-confidence synthetic identity detection",
            "manual_review": False,
            "verification": False,
        },
        {
            "rule": "ESCALATE_AML_FLAGGED",
            "condition": lambda r, ctx: ctx.get("aml_flagged", False),
            "action": Action.ESCALATE,
            "reason": "AML watchlist flag requires compliance review",
            "manual_review": True,
            "verification": False,
        },
        {
            "rule": "ESCALATE_HIGH_RISK",
            "condition": lambda r, ctx: r.risk_score >= 70,
            "action": Action.ESCALATE,
            "reason": "High risk score — fraud analyst review required",
            "manual_review": True,
            "verification": False,
        },
        {
            "rule": "ESCALATE_POSSIBLE_FRAUD",
            "condition": lambda r, ctx: r.intent == Intent.POSSIBLE_FRAUD and r.confidence >= 0.70,
            "action": Action.ESCALATE,
            "reason": "Possible fraud intent with high confidence — investigation required",
            "manual_review": True,
            "verification": False,
        },
        {
            "rule": "ESCALATE_PARALLEL_APPLICATION",
            "condition": lambda r, ctx: r.intent == Intent.PARALLEL_APPLICATION,
            "action": Action.ESCALATE,
            "reason": "Parallel application stacking detected",
            "manual_review": True,
            "verification": False,
        },
        {
            "rule": "CHALLENGE_KYC_UNVERIFIED",
            "condition": lambda r, ctx: not ctx.get("kyc_verified", True),
            "action": Action.CHALLENGE,
            "reason": "KYC verification incomplete — document submission required",
            "manual_review": False,
            "verification": True,
            "verification_type": "full_kyc",
        },
        {
            "rule": "CHALLENGE_MEDIUM_RISK",
            "condition": lambda r, ctx: 40 <= r.risk_score < 70,
            "action": Action.CHALLENGE,
            "reason": "Medium risk — additional verification required",
            "manual_review": False,
            "verification": True,
            "verification_type": "video_kyc",
        },
        {
            "rule": "CHALLENGE_LOW_CONFIDENCE",
            "condition": lambda r, ctx: r.confidence < 0.55,
            "action": Action.CHALLENGE,
            "reason": "Low AI confidence — OTP and selfie verification required",
            "manual_review": False,
            "verification": True,
            "verification_type": "otp_and_selfie",
        },
        {
            "rule": "ALLOW_LOW_RISK",
            "condition": lambda r, ctx: r.risk_score < 40 and r.intent == Intent.GENUINE,
            "action": Action.ALLOW,
            "reason": "Low risk genuine application — approved for processing",
            "manual_review": False,
            "verification": False,
        },
    ]

    def decide(self, risk: RiskAssessment, context: dict) -> PolicyDecision:
        for policy in self.POLICIES:
            try:
                if policy["condition"](risk, context):
                    return PolicyDecision(
                        action=policy["action"],
                        policy_rule=policy["rule"],
                        reason=policy["reason"],
                        requires_manual_review=policy.get("manual_review", False),
                        requires_verification=policy.get("verification", False),
                        verification_type=policy.get("verification_type"),
                    )
            except Exception:
                continue

        return PolicyDecision(
            action=Action.ESCALATE,
            policy_rule="DEFAULT_ESCALATE",
            reason="No policy matched — conservative default escalation applied",
            requires_manual_review=True,
        )
