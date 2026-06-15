import anthropic
import json
import re
from typing import Optional
from shared.models import (
    RiskAssessment, RiskLevel, Intent, Action,
    LoanApplicationRequest, ContextObject,
)
from services.ai_risk_engine.prompts import RISK_ASSESSMENT_SYSTEM_PROMPT
from config import settings
import logging

logger = logging.getLogger(__name__)


class AIRiskEngine:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    def assess_risk(self, application: LoanApplicationRequest, context: ContextObject) -> RiskAssessment:
        prompt = self._build_prompt(application, context)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                thinking={"type": "adaptive"},
                output_config={"effort": "high"},
                system=RISK_ASSESSMENT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            thinking_summary: Optional[str] = None
            text_content = ""
            for block in response.content:
                if block.type == "thinking" and hasattr(block, "thinking"):
                    thinking_summary = block.thinking[:600] if block.thinking else None
                elif block.type == "text":
                    text_content = block.text

            return self._parse_response(text_content, thinking_summary)

        except Exception as e:
            logger.error(f"AI risk engine error: {e}")
            return self._fallback_assessment()

    def _build_prompt(self, application: LoanApplicationRequest, context: ContextObject) -> str:
        a = application.applicant
        l = application.loan
        d = application.device
        b = context.behavior
        g = context.device_geo
        k = context.kyc_aml

        dti = (l.amount / (l.monthly_income * l.tenure_months) * 100) if l.monthly_income > 0 else 999

        return f"""Analyze this loan application for fraud risk and intent classification.

## APPLICATION
- ID: {application.application_id}
- Submitted: {application.timestamp}

## APPLICANT
- Name: {a.name}
- Customer ID: {a.customer_id}
- Email: {a.email}
- Phone: {a.phone}
- DOB: {a.date_of_birth}
- Address: {a.address}

## LOAN REQUEST
- Amount: ₹{l.amount:,.2f}
- Purpose: {l.purpose}
- Tenure: {l.tenure_months} months
- Stated Monthly Income: ₹{l.monthly_income:,.2f}
- Employment: {l.employment_type} @ {l.employer_name or 'Not stated'}
- Debt-to-Income Ratio: {dti:.1f}%

## CUSTOMER'S FREE TEXT (their own words)
"{l.free_text_reason or '[Not provided]'}"

## DEVICE & BEHAVIORAL SIGNALS
- Form Fill Duration: {d.form_fill_duration_seconds or 'Unknown'} seconds
- Field Corrections: {d.field_corrections}
- Suspicious Pauses Detected: {d.suspicious_pauses}
- IP Address: {d.ip_address}
- User Agent: {d.user_agent}

## GEO-INTELLIGENCE
- IP Country/City: {g.ip_country} / {g.ip_city}
- VPN: {g.ip_is_vpn} | Proxy: {g.ip_is_proxy}
- IP Risk Score: {g.ip_risk_score}/100
- Device Previously Seen: {g.device_seen_before}
- Location Matches Profile: {g.location_matches_profile}

## BEHAVIORAL HISTORY (this customer)
- Applications (24h / 7d / 30d): {b.applications_last_24h} / {b.applications_last_7d} / {b.applications_last_30d}
- Previous Defaults: {b.previous_defaults}
- Previous Fraud Flags: {b.previous_fraud_flags}
- Devices Used (30d): {b.devices_used}
- IP Changes (7d): {b.ip_changes_last_7d}

## KYC / AML STATUS
- KYC Verified: {k.kyc_verified}
- AML Status: {k.aml_status}
- Sanctions List Match: {k.sanctions_list}
- PEP Status: {k.pep_status}
- Adverse Media: {k.adverse_media}

Return your risk assessment as strict JSON per the format in your instructions."""

    def _parse_response(self, text: str, thinking_summary: Optional[str]) -> RiskAssessment:
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            data = json.loads(json_match.group() if json_match else text)

            return RiskAssessment(
                risk_score=float(data.get("risk_score", 50)),
                risk_level=RiskLevel(data.get("risk_level", "medium")),
                intent=Intent(data.get("intent", "suspicious")),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                fraud_indicators=data.get("fraud_indicators", []),
                recommended_action=Action(data.get("recommended_action", "ESCALATE")),
                free_text_analysis=data.get("free_text_analysis"),
                thinking_summary=thinking_summary,
            )
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}\nRaw: {text[:500]}")
            return self._fallback_assessment()

    def _fallback_assessment(self) -> RiskAssessment:
        return RiskAssessment(
            risk_score=55.0,
            risk_level=RiskLevel.MEDIUM,
            intent=Intent.SUSPICIOUS,
            confidence=0.3,
            reasoning="AI risk engine unavailable — applying conservative escalation.",
            fraud_indicators=["ai_engine_unavailable"],
            recommended_action=Action.ESCALATE,
        )
