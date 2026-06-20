# Behavioral Intent Firewall (BIF)

### *What if every microservice could see the full truth about who is asking — before it ever answered?*

**Author:** Ranjith Cheela · Technical Program Manager · BFSI Payments · AWS · Kafka · AI/ML
**Published:** June 17, 2026 · **Status:** MVP — Active Development
**Stack:** `Java` `Python` `Apache Kafka` `Docker` `Ollama (Local LLM)

---

## The Story Behind This

I've spent 15 years working inside BFSI and payment systems. In that time, one thing has always bothered me.

Every microservice we build is brilliant at its job — but completely blind to context. A loan approval service doesn't know this is the customer's third medical emergency loan this year, and their salary hasn't credited in 90 days. A refund service doesn't know this user has claimed damaged milk 7 out of their last 10 orders. A SaaS billing system doesn't know this "new user" has spun up 14 trial accounts from the same device.

Each individual request looks legitimate. The pattern tells a completely different story.

**BIF is my answer to that problem.**

It's a plug-and-play intelligence layer that sits before any microservice, reads the full behavioral context of every incoming request, and makes a pass-or-block decision — before a single line of business logic executes. The microservice stays completely untouched. It just lives in a cleaner, smarter world.

---

## How It Works — In Plain English

Think of BIF like an experienced loan officer who has seen everything. When a customer walks in, they don't just check the documents. They read the room. They remember that this person was here last month. They notice the inconsistency in what's being said versus what the records show. They act on pattern — not just the paperwork in front of them.

BIF does exactly that, at machine speed, for every API request across your entire microservice fleet.

```
Every API Request
       │
       ▼
┌──────────────────────────────────────────┐
│         BEHAVIORAL INTENT FIREWALL       │
│                                          │
│  ① Fingerprint Cache      → < 1ms        │
│    "Have I seen this pattern before?"    │
│                                          │
│  ② Fast Rules Engine      → < 5ms        │
│    "Does this break any known pattern?"  │
│                                          │
│  ③ Ollama Behavioral LLM  → 50–300ms     │
│    "What does their history tell me      │
│     about what they actually want?"      │
│                                          │
│  → Anomaly Intelligence Score  0–100     │
└──────────────────────────────────────────┘
         │                      │
     Score ≥ 40             Score < 40
         │                      │
         ▼                      ▼
   MICROSERVICE           REQUEST ABSORBED
   Receives clean          The microservice
   request, proceeds       never sees this
   as normal               request at all
```

**85% of traffic gets a decision in under 5ms.**
The expensive LLM inference only fires when it genuinely needs to.

---

## The Architecture

> *This diagram shows the full BIF flow — from the user's device, through the AI Intent Firewall Sidecar, to the Policy Decision and Enforcement points, and finally to the protected microservices and downstream systems.*

![BIF Architecture — AI Intent Firewall Sidecar](architecture.png)

**What you're seeing:**
- **Top half** — The user request flows through the API Gateway into the BIF Sidecar
- **Sidecar core** — Context Enrichment (user history, device, KYC/AML signals) and AI Risk & Intent Engine (Ollama-powered scoring) run in parallel, feeding the Policy Decision Point
- **Middle** — The Policy Enforcement Point makes the final routing call: Block, Allow, or Escalate to Manual Review
- **Bottom** — All decisions flow to Fraud & Risk Analytics and Monitoring/Logging, creating a continuous learning feedback loop

---

## What the Score Means

BIF doesn't give you a binary yes or no. It gives you a nuanced, explainable score — because real-world decisions rarely are binary.

| Score | What BIF Thinks | What Happens |
|-------|----------------|--------------|
| **75–100** | Clean. Consistent. Expected. | Request reaches microservice unchanged |
| **50–74** | Something's slightly off. Worth a second look. | Request passes, but a review is quietly queued |
| **30–49** | This doesn't add up. Intervention needed. | Microservice blocked. User gets a helpful alternate path |
| **0–29** | High confidence anomaly. Don't touch this. | Hard block. Internal escalation with full context report |

---

## The BFSI Use Case That Started This

A customer applies for a ₹2 lakh personal loan through a bank's mobile app. Standard workflow. The eligibility check passes. Credit score: fine. Documents: valid. KYC: clean.

But BIF notices something the microservice never could:

- This is their **3rd loan application in 6 months**, all for "medical emergencies"
- Their **salary hasn't credited in 87 days**
- The form was completed in **14 seconds** — faster than anyone reads the terms
- The employer details are **different from last month's application**

```json
{
  "anomaly_intelligence_score": 91,
  "intent": "possible synthetic identity fraud",
  "action": "ESCALATE",
  "reason": "3 loan applications in 24 hours with varying employer details",
  "signals": {
    "salary_credit_gap_days": 87,
    "loan_applications_30_days": 3,
    "form_completion_seconds": 14,
    "employer_detail_variations": 3,
    "stated_reason_risk_pattern": "HIGH"
  },
  "recommended_action": "Manual review + Video KYC",
  "explainability": "SHAP rationale available for compliance"
}
```

The loan microservice never processes this request. The bank avoids a near-certain NPA. The customer gets a pathway to speak to a human advisor.

**Everyone is better off.**

---

## This Isn't Just a BFSI Problem

I documented 9 industry verticals in the full white paper where BIF applies directly:

| Industry | The Invisible Pattern BIF Catches |
|----------|----------------------------------|
|  **BFSI — Loans** | Salary gap + repeat medical loans = trajectory risk the microservice never sees |
|  **Q-Commerce** | 7 damaged milk claims in 10 orders = statistically impossible if genuine |
|  **SaaS** | 14 trial accounts, same device, same typing pattern = serial abuse |
|  **Healthcare** | 6 doctors in 60 days for the same prescription = doctor shopping |
|  **Insurance** | Claim values escalating across 3 years = manipulation pattern |
|  **EdTech** | 8 certifications in 72 hours, all 95%+ scores = answer key exploit |
|  **Ride-Hailing** | Cancellations always just before the penalty window = policy gaming |
|  **E-Commerce** | Returns always on day 29 of a 30-day window = systematic exploitation |
|  **Telecom** | New SIM offer redeemed, used intensively, churned at day 31 = offer farming |

---

## Repository Structure

```
ai-sidecar-implementation/
│
├── sidecar-core/                   # Python — BIF interception and scoring engine
│   ├── fingerprint_engine.py       # Layer 1: Behavioral fingerprint cache
│   ├── rules_engine.py             # Layer 2: Fast deterministic rules
│   ├── ollama_client.py            # Layer 3: Local LLM inference client
│   └── decision_engine.py          # Anomaly Intelligence Score calculator
│
├── bfsi-loan-service/              # Java — Protected sample loan microservice
│   ├── LoanController.java
│   ├── LoanEligibilityService.java
│   └── LoanApplication.java
│
├── behavioral-history-store/       # Python — User trajectory persistence layer
│   ├── history_store.py
│   └── signal_aggregator.py
│
├── kafka-pipeline/                 # Kafka — Event streaming backbone
│   ├── request_interceptor/
│   ├── score_publisher/
│   └── alert_consumer/
│
├── docker/                         # Full stack containerisation
│   ├── docker-compose.yml
│   ├── Dockerfile.sidecar
│   └── Dockerfile.loan-service
│
├── architecture.png                # System architecture diagram
├── plan.md                         # 5-phase implementation roadmap
└── README.md
```

---

## Try It Yourself

```bash
# Clone and start the full stack
git clone https://github.com/RanjithCheela/ai-sidecar-implementation.git
cd ai-sidecar-implementation
docker-compose up --build

# Send a clean request — should score 75+
curl -X POST http://localhost:8080/api/loan/apply \
  -H "Content-Type: application/json" \
  -d '{"user_id": "USR001", "amount": 50000, "reason": "Home renovation"}'

# Send a suspicious request — should score below 40
curl -X POST http://localhost:8080/api/loan/apply \
  -H "Content-Type: application/json" \
  -d '{"user_id": "USR002", "amount": 200000, "reason": "Medical emergency"}'
```

---

## Implementation Roadmap

| Phase | What Gets Built | Duration |
|-------|----------------|----------|
| **Phase 1** | Kafka pipeline, BIF intercept layer, security baseline | 3 weeks |
| **Phase 2** | 50+ behavioral signal features: device, geo, NLP, velocity | 3 weeks |
| **Phase 3** | ML model training: XGBoost + Neural Networks + Ollama fine-tuning | 5 weeks |
| **Phase 4** | Full integration, latency optimisation, load testing at scale | 3 weeks |
| **Phase 5** | Canary deployment, SHAP explainability, monitoring feedback loops | 2 weeks |

**Target: Production-ready MVP in 16 weeks**

---

## What Success Looks Like

| Metric | Target |
|--------|--------|
| Fraud Detection Rate | 80%+ |
| False Positive Rate | < 5% |
| System Availability | 99.95% |
| p99 Latency (BIF layer) | < 100ms |
| ROI on Fraud Prevention | 10:1 |
| Regulatory Explainability | SHAP/LIME on every blocked decision |

---

## The Bigger Picture

BIF doesn't replace your KYC engine, your AML tools, or your credit bureau integrations. It works alongside them — as the intelligence layer they never had. It adds the one thing rules-based systems fundamentally cannot: **the ability to understand trajectory, not just eligibility.**

A rules engine sees each request in isolation.
BIF sees each request in the context of everything that came before it.

That difference is worth billions to the right organisations. And it deploys in a single Docker command.

---

## Intellectual Property

**Concept Author:** Ranjith Cheela
**Conception & Publication Date:** June 17, 2026
**Prior Art:** Established via timestamped white paper, email record, and this repository commit history

The specific combination of pre-microservice behavioral interception, trajectory-based LLM intent scoring, product-agnostic plug-and-play deployment, and graduated anomaly score decision spectrum is original to this author as of the date above.

*White paper available on request. Pilot programme and collaboration enquiries welcome.*

---

## Let's Talk

If you're building microservices that make consequential decisions — in banking, commerce, healthcare, insurance, or anywhere else — I'd genuinely love to hear whether this resonates with a problem you're living with.

**Ranjith Cheela**
Technical Program Manager · 15+ Years BFSI & Payments · AWS Certified · PGD AI/ML IIIT Bangalore
Hyderabad, India

(https://linkedin.com/in/ranjith-cheela)

---

*© 2026 Ranjith Cheela. All rights reserved. Prior art established June 17, 2026.*
