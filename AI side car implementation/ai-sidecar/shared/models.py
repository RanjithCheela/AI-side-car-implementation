from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List
from datetime import datetime
import uuid


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Intent(str, Enum):
    GENUINE = "genuine"
    POSSIBLE_FRAUD = "possible_fraud"
    SYNTHETIC_IDENTITY = "synthetic_identity"
    SUSPICIOUS = "suspicious"
    INCOME_MISREPRESENTATION = "income_misrepresentation"
    DOCUMENT_MANIPULATION = "document_manipulation"
    PARALLEL_APPLICATION = "parallel_application"


class Action(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"
    CHALLENGE = "CHALLENGE"


# ─── Inbound Request Models ───────────────────────────────────────────────────

class ApplicantInfo(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: str
    date_of_birth: str
    national_id: str
    address: str


class LoanDetails(BaseModel):
    amount: float
    purpose: str
    tenure_months: int
    monthly_income: float
    employment_type: str  # salaried / self_employed / business
    employer_name: Optional[str] = None
    free_text_reason: Optional[str] = None


class DeviceMetadata(BaseModel):
    device_id: str
    ip_address: str
    user_agent: str
    session_id: str
    form_fill_duration_seconds: Optional[float] = None
    field_corrections: Optional[int] = 0
    suspicious_pauses: Optional[bool] = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class LoanApplicationRequest(BaseModel):
    application_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    applicant: ApplicantInfo
    loan: LoanDetails
    device: DeviceMetadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Context Enrichment Models ────────────────────────────────────────────────

class BehaviorHistory(BaseModel):
    applications_last_24h: int = 0
    applications_last_7d: int = 0
    applications_last_30d: int = 0
    previous_defaults: int = 0
    previous_fraud_flags: int = 0
    avg_form_fill_time_seconds: float = 300.0
    devices_used: int = 1
    ip_changes_last_7d: int = 0


class DeviceGeoInfo(BaseModel):
    ip_country: str = "IN"
    ip_city: str = "Unknown"
    ip_is_vpn: bool = False
    ip_is_proxy: bool = False
    ip_risk_score: float = 0.0
    device_seen_before: bool = False
    location_matches_profile: bool = True


class KYCAMLStatus(BaseModel):
    kyc_verified: bool = True
    aml_status: str = "clear"  # clear / flagged / under_review
    sanctions_list: bool = False
    pep_status: bool = False
    adverse_media: bool = False


class ContextObject(BaseModel):
    application_id: str
    behavior: BehaviorHistory
    device_geo: DeviceGeoInfo
    kyc_aml: KYCAMLStatus


# ─── Decision Models ──────────────────────────────────────────────────────────

class RiskAssessment(BaseModel):
    risk_score: float
    risk_level: RiskLevel
    intent: Intent
    confidence: float
    reasoning: str
    fraud_indicators: List[str] = []
    recommended_action: Action
    free_text_analysis: Optional[dict] = None
    thinking_summary: Optional[str] = None


class PolicyDecision(BaseModel):
    action: Action
    policy_rule: str
    reason: str
    requires_manual_review: bool = False
    requires_verification: bool = False
    verification_type: Optional[str] = None


class FirewallResponse(BaseModel):
    application_id: str
    timestamp: datetime
    action: Action
    risk_assessment: RiskAssessment
    policy_decision: PolicyDecision
    message: str
    next_steps: List[str] = []
    processing_time_ms: float
