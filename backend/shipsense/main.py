import os
import sys
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from .models import (
    OnboardRequest, OnboardResponse,
    AuditUrlRequest, AuditUrlResponse,
    BehaviorEvent, BehaviorIngestRequest, BehaviorIngestResponse,
    BehaviorResponse, ActionDetail,
    ChatRequest, ChatResponse,
    InsightsResponse, RecommendedAction,
    MetricsResponse, ProductResponse,
    HealthResponse, DecisionResponse,
    WorkspaceResponse, ProductSummary,
    CriticalFlowRequest, CriticalFlowResponse,
    ProductContextRequest, ProductContextResponse,
    ExperimentCreateRequest, ExperimentResponse,
    CollectorStatusResponse, CollectorKeyResponse,
    InstrumentationReadinessResponse,
    SampleProductResponse,
    AnalystContextResponse, AnalystCitation,
)
from . import db
from . import analyzer
from . import decisions
from . import experiments
from .auditor import run_full_audit
from .url_security import UnsafeUrlError, validate_public_url
import agent
from agent.context import (
    build_analyst_context,
    build_evidence_registry,
    suggested_questions,
)

load_dotenv()


@asynccontextmanager
async def lifespan(_app):
    db.init_db()
    yield


app = FastAPI(
    title="ShipSense API",
    description="AI Product Analytics Agent",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# The ShipSense Event Collector posts events to /api/behavior/ingest from
# customer origins, so the API currently accepts any origin. Authentication and
# scoped collector keys will replace this during the durable-storage phase.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        version="0.1.0",
        database=db.database_status(),
    )


def require_workspace(x_workspace_key: str | None = Header(default=None)):
    workspace = db.get_workspace_by_key(x_workspace_key)
    if not workspace:
        raise HTTPException(status_code=401, detail="A valid workspace key is required")
    return workspace


def require_product(product_id, workspace):
    product = db.get_owned_product(product_id, workspace["id"])
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in this workspace")
    return product


def experiment_response(experiment, product):
    return ExperimentResponse(
        id=experiment["public_id"],
        product_id=product["public_id"],
        decision_id=experiment["decision_id"],
        name=experiment["name"],
        hypothesis=experiment["hypothesis"],
        target_metric=experiment["target_metric"],
        baseline_value=experiment["baseline_value"],
        status=experiment["status"],
        shipped_at=experiment["shipped_at"],
        result=experiment["result"],
        created_at=experiment["created_at"],
    )


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

@app.post("/api/workspaces", response_model=WorkspaceResponse)
def create_workspace():
    workspace = db.create_workspace()
    return WorkspaceResponse(
        workspace_id=workspace["public_id"],
        workspace_key=workspace["workspace_key"],
    )


@app.get("/api/products", response_model=list[ProductSummary])
def list_workspace_products(workspace=Depends(require_workspace)):
    return [
        ProductSummary(
            id=product["public_id"],
            url=product["url"],
            product_type=product["product_type"],
            core_action=product["core_action"],
            critical_flow=product["critical_flow"],
            product_context=product["product_context"],
            is_sample=product["user_id"] == "shipsense-sample",
            created_at=product["created_at"],
        )
        for product in db.list_products(workspace["id"])
    ]


# ---------------------------------------------------------------------------
# Audit URL
# ---------------------------------------------------------------------------

@app.post("/api/audit-url")
def audit_url(req: AuditUrlRequest, _workspace=Depends(require_workspace)):
    try:
        validate_public_url(req.url)
        result = run_full_audit(req.url)
        return result
    except UnsafeUrlError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


# ---------------------------------------------------------------------------
# Onboard
# ---------------------------------------------------------------------------

@app.post("/api/onboard", response_model=OnboardResponse)
def onboard(req: OnboardRequest, workspace=Depends(require_workspace)):
    try:
        validate_public_url(req.url)
        created = db.create_product(
            url=req.url,
            product_type=req.product_type,
            core_action=req.core_action,
            user_id=req.user_id,
            workspace_id=workspace["id"],
            critical_flow=req.critical_flow,
            product_context=req.product_context.model_dump(),
        )
        product = db.get_product(created["id"])
        product_id = product["id"]

        audit_data = req.audit_data
        if not audit_data:
            try:
                audit_data = run_full_audit(req.url)
            except Exception:
                pass
        if audit_data:
            db.save_audit(product_id, audit_data)

        events = db.get_events(product_id)
        top_actions = analyzer.get_top_actions(events)
        drop_offs = analyzer.calculate_drop_off(
            events,
            steps=product["critical_flow"] or None,
        )
        active_users = analyzer.get_active_users(events)
        avg_session = analyzer.get_avg_session(events)
        patterns = analyzer.detect_patterns(events)
        instrumentation_readiness = analyzer.get_instrumentation_readiness(
            events,
            product["critical_flow"],
        )

        insights = agent.generate_insights(
            product, top_actions, drop_offs,
            active_users, avg_session, patterns,
            audit_data=audit_data,
        )
        db.save_insight(product_id, insights["summary"], insights["recommended_actions"])
        decision = decisions.build_decision(
            product,
            audit_data,
            top_actions,
            drop_offs,
            active_users,
            instrumentation_readiness,
        )
        db.save_decision(product_id, decision)

        return OnboardResponse(
            product_id=product["public_id"],
            collector_key=created["collector_key"],
            critical_flow=product["critical_flow"],
            initial_insights=insights["summary"],
            audit_data=audit_data,
            audit_received=audit_data is not None,
        )
    except HTTPException:
        raise
    except UnsafeUrlError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Onboarding failed: {str(e)}")


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

@app.get("/api/product/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, workspace=Depends(require_workspace)):
    product = require_product(product_id, workspace)
    internal_id = product["id"]

    events = db.get_events(internal_id)
    active_users = analyzer.get_active_users(events)
    avg_session = analyzer.get_avg_session(events)
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(
        events,
        steps=product["critical_flow"] or None,
    )

    return ProductResponse(
        id=product["public_id"],
        url=product["url"],
        product_type=product["product_type"],
        core_action=product["core_action"],
        critical_flow=product["critical_flow"],
        product_context=product["product_context"],
        is_sample=product["user_id"] == "shipsense-sample",
        created_at=product["created_at"],
        active_users=active_users,
        avg_session=avg_session,
        drop_off_rate=drop_offs[0]["drop_off_rate"] if drop_offs else "0%",
        top_action=top_actions[0]["action"] if top_actions else "N/A",
    )


@app.post("/api/demo/sample-product", response_model=SampleProductResponse)
def create_sample_product(workspace=Depends(require_workspace)):
    """Create an explicitly labelled, persisted demonstration of the full loop."""
    created = db.create_product(
        url="https://example.com",
        product_type="b2b",
        core_action="complete sample signup",
        user_id="shipsense-sample",
        workspace_id=workspace["id"],
        critical_flow=["landing", "signup"],
        product_context={
            "target_user": "Solo software builders launching web products",
            "user_problem": "They cannot tell which onboarding friction to fix first.",
            "value_proposition": "Turn behavioral evidence into one measurable product decision.",
            "business_goal": "Increase completed signups",
            "constraints": "Small traffic sample and no dedicated product analyst",
        },
    )
    product = db.get_product(created["id"])
    db.save_audit(product["id"], {
        "url": product["url"],
        "performance_score": 78,
        "accessibility_score": 94,
        "seo_score": 91,
        "best_practices_score": 88,
        "has_mobile_viewport": True,
        "images_missing_alt": 0,
        "security_headers": {"security_score": 75},
        "sample_data": True,
    })

    baseline_start = datetime.now(timezone.utc) - timedelta(hours=3)
    baseline_events = []
    for index in range(5):
        event_time = baseline_start + timedelta(minutes=index)
        baseline_events.append(BehaviorEvent(
            event_id=f"sample-before-{product['public_id']}-{index}-landing",
            action="landing",
            user_id=f"sample-before-{index}",
            timestamp=event_time.isoformat(),
        ))
        if index < 2:
            baseline_events.append(BehaviorEvent(
                event_id=f"sample-before-{product['public_id']}-{index}-signup",
                action="signup",
                user_id=f"sample-before-{index}",
                timestamp=(event_time + timedelta(seconds=30)).isoformat(),
            ))
    db.insert_events(product["id"], baseline_events)

    baseline_drop_offs = analyzer.calculate_drop_off(
        db.get_events(product["id"]),
        steps=product["critical_flow"],
    )
    baseline_readiness = analyzer.get_instrumentation_readiness(
        db.get_events(product["id"]),
        product["critical_flow"],
    )
    decision = decisions.build_decision(
        product,
        db.get_audit(product["id"])["audit_json"],
        analyzer.get_top_actions(db.get_events(product["id"])),
        baseline_drop_offs,
        analyzer.get_active_users(db.get_events(product["id"])),
        baseline_readiness,
    )
    decision_id, _ = db.save_decision(product["id"], decision)
    experiment = db.create_experiment(
        product_id=product["id"],
        decision_id=decision_id,
        name="Sample: simplify the signup continuation",
        hypothesis=(
            "If we make signup the obvious next action, then more users "
            "continue from landing to signup."
        ),
        target_metric=decision["target_metric"],
        baseline_value=decision["baseline_value"],
    )
    shipped_at = datetime.now(timezone.utc) - timedelta(hours=1)
    experiment = db.mark_experiment_shipped(
        experiment["id"],
        shipped_at.isoformat(),
    )

    post_ship_events = []
    for index in range(5):
        event_time = shipped_at + timedelta(minutes=index + 1)
        post_ship_events.append(BehaviorEvent(
            event_id=f"sample-after-{product['public_id']}-{index}-landing",
            action="landing",
            user_id=f"sample-after-{index}",
            timestamp=event_time.isoformat(),
        ))
        if index < 4:
            post_ship_events.append(BehaviorEvent(
                event_id=f"sample-after-{product['public_id']}-{index}-signup",
                action="signup",
                user_id=f"sample-after-{index}",
                timestamp=(event_time + timedelta(seconds=30)).isoformat(),
            ))
    db.insert_events(product["id"], post_ship_events)
    status, result = experiments.evaluate_experiment(
        experiment,
        product,
        db.get_events(product["id"], since=experiment["shipped_at"]),
        db.get_audit(product["id"])["audit_json"],
    )
    db.save_experiment_result(experiment["id"], status, result)

    # Store a fresh current decision after the sample experiment result so the
    # demo opens without an artificial stale-state warning.
    _build_and_save_decision(db.get_product(product["id"]))

    return SampleProductResponse(
        product_id=product["public_id"],
        label="ShipSense sample product — all behavioral and experiment data is synthetic",
    )


# ---------------------------------------------------------------------------
# Behavior ingest
# ---------------------------------------------------------------------------

@app.post("/api/behavior/ingest", response_model=BehaviorIngestResponse)
def ingest_behavior(req: BehaviorIngestRequest):
    product = db.verify_collector_key(req.product_id, req.collector_key)
    if not product:
        raise HTTPException(
            status_code=401,
            detail="Invalid product or collector key",
        )
    try:
        count = db.insert_events(product["id"], req.events)
        return BehaviorIngestResponse(ingested=True, count=count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest events: {str(e)}")


# ---------------------------------------------------------------------------
# Behavior query
# ---------------------------------------------------------------------------

@app.get("/api/behavior/{product_id}", response_model=BehaviorResponse)
def get_behavior(product_id: str, workspace=Depends(require_workspace)):
    product = require_product(product_id, workspace)

    events = db.get_events(product["id"])
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(
        events,
        steps=product["critical_flow"] or None,
    )
    active_users = analyzer.get_active_users(events)
    session_summary = analyzer.get_session_summary(events)

    # Real events only — no estimated/hallucinated fallback.
    return BehaviorResponse(
        top_actions=[
            ActionDetail(
                action=a["action"],
                event_count=a["event_count"],
                unique_users=a["unique_users"],
                event_frequency=a["event_frequency"],
                user_frequency=a["user_frequency"],
                dropoff_after=next(
                    (d["drop_off_rate"] for d in drop_offs if d["step"] == a["action"]),
                    "0%",
                ),
            )
            for a in top_actions
        ],
        drop_off_points=drop_offs,
        event_count=len(events),
        avg_session=session_summary["average_duration"],
        active_users=active_users,
        session_count=session_summary["session_count"],
        measurable_session_count=session_summary["measurable_session_count"],
    )


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

@app.get("/api/insights/{product_id}", response_model=InsightsResponse)
def get_insights(product_id: str, workspace=Depends(require_workspace)):
    product = require_product(product_id, workspace)
    internal_id = product["id"]

    saved = db.get_latest_insight(internal_id)
    if saved:
        return InsightsResponse(
            summary=saved["summary"],
            recommended_actions=[
                RecommendedAction(**a) for a in json.loads(saved["actions"])
            ],
        )

    events = db.get_events(internal_id)
    active_users = analyzer.get_active_users(events)
    avg_session = analyzer.get_avg_session(events)
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(
        events,
        steps=product["critical_flow"] or None,
    )
    patterns = analyzer.detect_patterns(events)

    # Real audit data only — no simulated fallback.
    saved_audit = db.get_audit(internal_id)
    audit_data = saved_audit["audit_json"] if saved_audit else None

    insights = agent.generate_insights(
        product, top_actions, drop_offs,
        active_users, avg_session, patterns,
        audit_data=audit_data,
    )
    db.save_insight(internal_id, insights["summary"], insights["recommended_actions"])

    return InsightsResponse(
        summary=insights["summary"],
        recommended_actions=[
            RecommendedAction(**a) for a in insights["recommended_actions"]
        ],
    )


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

def _build_and_save_decision(product):
    internal_id = product["id"]

    events = db.get_events(internal_id)
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(
        events,
        steps=product["critical_flow"] or None,
    )
    active_users = analyzer.get_active_users(events)
    instrumentation_readiness = analyzer.get_instrumentation_readiness(
        events,
        product["critical_flow"],
    )
    saved_audit = db.get_audit(internal_id)
    audit_data = saved_audit["audit_json"] if saved_audit else None

    decision = decisions.build_decision(
        product,
        audit_data,
        top_actions,
        drop_offs,
        active_users,
        instrumentation_readiness,
    )
    decision_id, version = db.save_decision(internal_id, decision)
    refreshed_product = db.get_product(internal_id)
    return DecisionResponse(
        decision_id=decision_id,
        version=version,
        **db.get_decision_freshness(refreshed_product, decision),
        **decision,
    )


@app.get("/api/decision/{product_id}", response_model=DecisionResponse)
def get_decision(product_id: str, workspace=Depends(require_workspace)):
    product = require_product(product_id, workspace)
    saved = db.get_latest_decision(product["id"])
    if saved:
        return DecisionResponse(
            **saved,
            **db.get_decision_freshness(product, saved),
        )
    return _build_and_save_decision(product)


@app.post("/api/decision/{product_id}/refresh", response_model=DecisionResponse)
def refresh_decision(product_id: str, workspace=Depends(require_workspace)):
    product = require_product(product_id, workspace)
    return _build_and_save_decision(product)


# ---------------------------------------------------------------------------
# Agent chat
# ---------------------------------------------------------------------------

def _build_analyst_state(product):
    internal_id = product["id"]
    event_data = db.get_events(internal_id)
    top_actions = analyzer.get_top_actions(event_data)
    drop_offs = analyzer.calculate_drop_off(
        event_data,
        steps=product["critical_flow"] or None,
    )
    active_users = analyzer.get_active_users(event_data)
    avg_session = analyzer.get_avg_session(event_data)
    saved_audit = db.get_audit(internal_id)
    audit_data = saved_audit["audit_json"] if saved_audit else None
    decision = db.get_latest_decision(internal_id)
    experiment_data = db.list_experiments(internal_id)
    registry = build_evidence_registry(
        product=product,
        top_actions=top_actions,
        drop_offs=drop_offs,
        active_users=active_users,
        avg_session=avg_session,
        audit_data=audit_data,
        decision=decision,
        experiments=experiment_data,
    )
    context = build_analyst_context(
        product=product,
        decision=decision,
        experiments=experiment_data,
        evidence_registry=registry,
    )
    return {
        "context": context,
        "registry": registry,
        "decision": decision,
        "experiments": experiment_data,
    }


def _analyst_confidence(citations, reply):
    if not citations:
        if "not enough" in reply.lower() or "no conclusive" in reply.lower():
            return 1.0, ["The answer explicitly reports the limit of available evidence."]
        return 0.35, ["No measured evidence was cited."]

    scores = []
    reasons = []
    for citation in citations:
        source = citation["source_type"]
        sample = citation.get("sample_size")
        if source == "experiment":
            scores.append(0.9)
            reasons.append("An evaluated experiment result was cited.")
        elif source == "funnel":
            score = 0.78 if sample and sample >= 20 else 0.62 if sample and sample >= 10 else 0.48
            scores.append(score)
            reasons.append(f"The funnel citation is based on {sample or 0} unique users.")
        elif source == "technical_audit":
            scores.append(0.82)
            reasons.append("A live technical-audit measurement was cited.")
        elif source == "product_context":
            scores.append(0.4)
            reasons.append("Owner-declared product context was cited.")
        else:
            score = 0.68 if sample and sample >= 10 else 0.5
            scores.append(score)
            reasons.append("A real behavior measurement was cited.")
    return round(sum(scores) / len(scores), 2), list(dict.fromkeys(reasons))


@app.get(
    "/api/agent/context/{product_id}",
    response_model=AnalystContextResponse,
)
def get_analyst_context(
    product_id: str,
    workspace=Depends(require_workspace),
):
    product = require_product(product_id, workspace)
    state = _build_analyst_state(product)
    decision = state["decision"]
    return AnalystContextResponse(
        current_decision=(
            {
                "decision_id": decision["decision_id"],
                "version": decision["version"],
                "title": decision["title"],
                "problem": decision["problem"],
                "target_metric": decision["target_metric"],
                "confidence": decision["confidence"],
            }
            if decision
            else None
        ),
        experiments=[
            {
                "id": item["public_id"],
                "name": item["name"],
                "status": item["status"],
                "result": item["result"],
            }
            for item in state["experiments"]
        ],
        suggested_questions=suggested_questions(
            state["decision"],
            state["experiments"],
        ),
        evidence_count=len(state["registry"]),
    )


@app.post("/api/agent/chat", response_model=ChatResponse)
def chat(req: ChatRequest, workspace=Depends(require_workspace)):
    product = require_product(req.product_id, workspace)
    internal_id = product["id"]

    chat_history = db.get_chat_history(internal_id, req.user_id)
    db.save_chat_message(internal_id, req.user_id, "user", req.message)
    state = _build_analyst_state(product)
    result = agent.chat_with_agent(
        message=req.message,
        analyst_context=state["context"],
        chat_history=chat_history,
    )
    db.save_chat_message(internal_id, req.user_id, "assistant", result["reply"])
    citations = [
        state["registry"][citation_id]
        for citation_id in result["citation_ids"]
        if citation_id in state["registry"]
    ]
    confidence, confidence_reasons = _analyst_confidence(
        citations,
        result["reply"],
    )

    return ChatResponse(
        reply=result["reply"],
        citations=[AnalystCitation(**citation) for citation in citations],
        follow_up=result["follow_up"],
        suggested_questions=suggested_questions(
            state["decision"],
            state["experiments"],
        ),
        confidence=confidence,
        confidence_reasons=confidence_reasons,
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@app.get("/api/metrics/{product_id}", response_model=MetricsResponse)
def get_metrics(product_id: str, workspace=Depends(require_workspace)):
    product = require_product(product_id, workspace)

    events = db.get_events(product["id"])
    active_users = analyzer.get_active_users(events)
    avg_session = analyzer.get_avg_session(events)
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(
        events,
        steps=product["critical_flow"] or None,
    )

    # Real tracked events only — no simulated metrics.
    return MetricsResponse(
        active_users=active_users,
        avg_session=avg_session,
        drop_off_rate=drop_offs[0]["drop_off_rate"] if drop_offs else "0%",
        top_action=top_actions[0]["action"] if top_actions else "N/A",
    )


# ---------------------------------------------------------------------------
# Audit data (real scraped fields)
# ---------------------------------------------------------------------------

@app.get("/api/audit/{product_id}")
def get_audit(product_id: str, workspace=Depends(require_workspace)):
    product = require_product(product_id, workspace)

    saved_audit = db.get_audit(product["id"])
    if not saved_audit:
        raise HTTPException(status_code=404, detail="No audit data found. Re-run the audit from the onboarding page.")

    return {"product_id": product["public_id"], "url": product["url"], "audit": saved_audit["audit_json"]}


# ---------------------------------------------------------------------------
# Critical flow
# ---------------------------------------------------------------------------

@app.put("/api/product/{product_id}/critical-flow", response_model=CriticalFlowResponse)
def update_critical_flow(
    product_id: str,
    req: CriticalFlowRequest,
    workspace=Depends(require_workspace),
):
    product = require_product(product_id, workspace)
    db.update_critical_flow(product["id"], req.steps)
    return CriticalFlowResponse(product_id=product["public_id"], steps=req.steps)


@app.put(
    "/api/product/{product_id}/context",
    response_model=ProductContextResponse,
)
def update_product_context(
    product_id: str,
    req: ProductContextRequest,
    workspace=Depends(require_workspace),
):
    product = require_product(product_id, workspace)
    context = req.model_dump()
    db.update_product_context(product["id"], context)
    return ProductContextResponse(
        product_id=product["public_id"],
        context=context,
    )


# ---------------------------------------------------------------------------
# Collector integration
# ---------------------------------------------------------------------------

@app.get(
    "/api/product/{product_id}/collector/status",
    response_model=CollectorStatusResponse,
)
def get_collector_status(
    product_id: str,
    workspace=Depends(require_workspace),
):
    product = require_product(product_id, workspace)
    status = db.get_collector_status(product["id"])
    return CollectorStatusResponse(
        product_id=product["public_id"],
        **status,
    )


@app.get(
    "/api/product/{product_id}/instrumentation-readiness",
    response_model=InstrumentationReadinessResponse,
)
def get_instrumentation_readiness(
    product_id: str,
    workspace=Depends(require_workspace),
):
    product = require_product(product_id, workspace)
    readiness = analyzer.get_instrumentation_readiness(
        db.get_events(product["id"]),
        product["critical_flow"],
    )
    return InstrumentationReadinessResponse(
        product_id=product["public_id"],
        **readiness,
    )


@app.post(
    "/api/product/{product_id}/collector/rotate",
    response_model=CollectorKeyResponse,
)
def rotate_collector_key(
    product_id: str,
    workspace=Depends(require_workspace),
):
    product = require_product(product_id, workspace)
    collector_key = db.rotate_collector_key(product["id"])
    return CollectorKeyResponse(
        product_id=product["public_id"],
        collector_key=collector_key,
    )


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------

@app.post("/api/experiments", response_model=ExperimentResponse)
def create_experiment(
    req: ExperimentCreateRequest,
    workspace=Depends(require_workspace),
):
    product = require_product(req.product_id, workspace)
    decision = db.get_decision(product["id"], req.decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found for this product")

    target_metric = decision["target_metric"]
    if target_metric.startswith("funnel:") and target_metric.endswith(":completion_rate"):
        _, step, next_step, _ = target_metric.split(":", 3)
        readiness = analyzer.get_instrumentation_readiness(
            db.get_events(product["id"]),
            [step, next_step],
        )
        transition = readiness["transitions"][0]
        if not readiness["decision_ready"] or not transition["ready"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "invalid_behavior_baseline",
                    "message": (
                        "This behavioral experiment does not have a valid "
                        "instrumented baseline."
                    ),
                    "next_actions": readiness["next_actions"],
                },
            )
    elif not target_metric.startswith("technical_audit:"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "unsupported_experiment_baseline",
                "message": (
                    "This decision is a data-readiness action, not a measurable "
                    "product experiment."
                ),
                "next_actions": [
                    "Complete instrumentation, refresh the Decision Card, then create an experiment."
                ],
            },
        )

    experiment = db.get_experiment_for_decision(
        product["id"],
        decision["decision_id"],
    )
    if not experiment:
        experiment = db.create_experiment(
            product_id=product["id"],
            decision_id=decision["decision_id"],
            name=req.name or decision["title"],
            hypothesis=(
                f"If we implement this decision, then {decision['expected_outcome']}"
            ),
            target_metric=decision["target_metric"],
            baseline_value=decision["baseline_value"],
        )
    return experiment_response(experiment, product)


@app.get("/api/product/{product_id}/experiments", response_model=list[ExperimentResponse])
def list_product_experiments(
    product_id: str,
    workspace=Depends(require_workspace),
):
    product = require_product(product_id, workspace)
    return [
        experiment_response(experiment, product)
        for experiment in db.list_experiments(product["id"])
    ]


@app.post("/api/experiments/{experiment_id}/ship", response_model=ExperimentResponse)
def ship_experiment(
    experiment_id: str,
    workspace=Depends(require_workspace),
):
    experiment = db.get_owned_experiment(experiment_id, workspace["id"])
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    product = db.get_product(experiment["product_id"])
    shipped = db.mark_experiment_shipped(
        experiment["id"],
        datetime.now(timezone.utc).isoformat(),
    )
    return experiment_response(shipped, product)


@app.post("/api/experiments/{experiment_id}/evaluate", response_model=ExperimentResponse)
def evaluate_experiment(
    experiment_id: str,
    workspace=Depends(require_workspace),
):
    experiment = db.get_owned_experiment(experiment_id, workspace["id"])
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    product = db.get_product(experiment["product_id"])
    event_data = db.get_events(product["id"], since=experiment["shipped_at"])
    saved_audit = db.get_audit(product["id"])
    audit_data = saved_audit["audit_json"] if saved_audit else None
    status, result = experiments.evaluate_experiment(
        experiment,
        product,
        event_data,
        audit_data,
    )
    evaluated = db.save_experiment_result(experiment["id"], status, result)
    return experiment_response(evaluated, product)


@app.post("/api/audit/{product_id}/refresh")
def refresh_audit(product_id: str, workspace=Depends(require_workspace)):
    product = require_product(product_id, workspace)
    try:
        validate_public_url(product["url"])
        result = run_full_audit(product["url"])
    except UnsafeUrlError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.save_audit(product["id"], result)
    return {
        "product_id": product["public_id"],
        "url": product["url"],
        "audit": result,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("shipsense.main:app", host="0.0.0.0", port=8000, reload=True)
