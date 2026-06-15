import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from shared.models import LoanApplicationRequest, FirewallResponse
from shared.database import init_db, get_db, ApplicationLog, AuditEvent
from services.ai_sidecar.sidecar import AISidecar

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

sidecar: AISidecar | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sidecar
    logger.info("Starting BFSI Intent Firewall...")
    await init_db()
    sidecar = AISidecar()
    logger.info("AI Sidecar initialized — ready to process applications")
    yield
    if sidecar:
        await sidecar.close()
    logger.info("AI Sidecar shut down")


app = FastAPI(
    title="BFSI Intent Firewall",
    description=(
        "AI-powered sidecar that intercepts loan applications, evaluates fraud intent "
        "using Claude AI, and enforces ALLOW / BLOCK / ESCALATE / CHALLENGE decisions "
        "before forwarding to the core Loan Origination Service."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Core Endpoint ─────────────────────────────────────────────────────────────

@app.post(
    "/loan/apply",
    response_model=FirewallResponse,
    summary="Submit a loan application for intent evaluation",
    tags=["Firewall"],
)
async def apply_for_loan(
    application: LoanApplicationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Entry point for all loan applications. The AI Sidecar:
    1. Enriches context (behavioral, geo, KYC/AML)
    2. Calls Claude AI for risk/intent assessment
    3. Applies policy rules → ALLOW / BLOCK / ESCALATE / CHALLENGE
    4. Publishes events to Kafka
    5. Returns the firewall decision to the caller
    """
    return await sidecar.process(application, db)


# ─── Audit & Analytics ─────────────────────────────────────────────────────────

@app.get(
    "/audit/{application_id}",
    summary="Full audit trail for an application",
    tags=["Audit"],
)
async def get_audit_trail(application_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.application_id == application_id)
        .order_by(AuditEvent.timestamp)
    )
    events = result.scalars().all()
    if not events:
        raise HTTPException(status_code=404, detail=f"No audit trail found for application_id={application_id}")
    return {
        "application_id": application_id,
        "event_count": len(events),
        "events": [
            {"type": e.event_type, "data": e.event_data, "timestamp": e.timestamp.isoformat()}
            for e in events
        ],
    }


@app.get(
    "/analytics/recent",
    summary="Recent decision analytics",
    tags=["Analytics"],
)
async def get_recent_analytics(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApplicationLog)
        .order_by(desc(ApplicationLog.created_at))
        .limit(limit)
    )
    logs = result.scalars().all()
    actions = [l.action for l in logs]
    return {
        "total_shown": len(logs),
        "summary": {
            "ALLOW": actions.count("ALLOW"),
            "BLOCK": actions.count("BLOCK"),
            "ESCALATE": actions.count("ESCALATE"),
            "CHALLENGE": actions.count("CHALLENGE"),
        },
        "records": [
            {
                "application_id": l.application_id,
                "customer_id": l.customer_id,
                "loan_amount": l.loan_amount,
                "action": l.action,
                "risk_score": l.risk_score,
                "risk_level": l.risk_level,
                "intent": l.intent,
                "policy_rule": l.policy_rule,
                "fraud_indicators": l.fraud_indicators,
                "processing_time_ms": round(l.processing_time_ms, 1),
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ],
    }


@app.get(
    "/analytics/stats",
    summary="Aggregate fraud statistics",
    tags=["Analytics"],
)
async def get_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApplicationLog))
    logs = result.scalars().all()
    if not logs:
        return {"message": "No data yet"}
    total = len(logs)
    blocked = sum(1 for l in logs if l.action == "BLOCK")
    escalated = sum(1 for l in logs if l.action == "ESCALATE")
    avg_risk = sum(l.risk_score for l in logs) / total
    avg_time = sum(l.processing_time_ms for l in logs) / total
    return {
        "total_applications": total,
        "block_rate_pct": round(blocked / total * 100, 2),
        "escalation_rate_pct": round(escalated / total * 100, 2),
        "average_risk_score": round(avg_risk, 2),
        "average_processing_time_ms": round(avg_time, 1),
        "action_breakdown": {
            action: sum(1 for l in logs if l.action == action)
            for action in ("ALLOW", "BLOCK", "ESCALATE", "CHALLENGE")
        },
    }


@app.get("/health", tags=["System"])
async def health():
    return {"status": "healthy", "service": "BFSI Intent Firewall", "version": "1.0.0"}
