import os
import sys
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from .models import (
    OnboardRequest, OnboardResponse,
    AuditUrlRequest, AuditUrlResponse,
    BehaviorIngestRequest, BehaviorIngestResponse,
    BehaviorResponse, ActionDetail,
    ChatRequest, ChatResponse,
    InsightsResponse, RecommendedAction,
    MetricsResponse, ProductResponse,
    HealthResponse,
)
from . import db
from . import analyzer
from . import estimator
from .auditor import run_full_audit
import agent

load_dotenv()

app = FastAPI(
    title="ShipSense API",
    description="AI Product Analytics Agent",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://shipsense-knrs.onrender.com",
        "http://localhost:5173",
        "http://localhost:3000",
        "https://shipsense-nine.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
def startup():
    db.init_db()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", version="0.1.0")


# ---------------------------------------------------------------------------
# Audit URL
# ---------------------------------------------------------------------------

@app.post("/api/audit-url")
def audit_url(req: AuditUrlRequest):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_full_audit(req.url))
        loop.close()
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback, sys
        exc_type, exc_value, exc_tb = sys.exc_info()
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        raise HTTPException(
            status_code=500,
            detail=f"Audit failed: {str(e)}\n{''.join(tb_lines)}"
        )


@app.get("/api/audit-test")
def audit_test():
    result = {"imports_ok": {}}
    try:
        import httpx
        result["imports_ok"]["httpx"] = True
    except Exception as e:
        result["imports_ok"]["httpx"] = str(e)
    try:
        from bs4 import BeautifulSoup
        result["imports_ok"]["bs4"] = True
    except Exception as e:
        result["imports_ok"]["bs4"] = str(e)
    try:
        import lxml
        result["imports_ok"]["lxml"] = True
    except Exception as e:
        result["imports_ok"]["lxml"] = str(e)
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><p>test</p></body></html>", "lxml")
        result["imports_ok"]["lxml_parse"] = True
    except Exception as e:
        result["imports_ok"]["lxml_parse"] = str(e)
    try:
        soup = BeautifulSoup("<html><body><input></body></html>", "lxml")
        inputs = soup.select("input")
        result["imports_ok"]["css_select"] = len(inputs)
    except Exception as e:
        result["imports_ok"]["css_select"] = str(e)
    return result


# ---------------------------------------------------------------------------
# Onboard
# ---------------------------------------------------------------------------

@app.post("/api/onboard", response_model=OnboardResponse)
def onboard(req: OnboardRequest):
    try:
        product_id = db.create_product(
            url=req.url,
            product_type=req.product_type,
            core_action=req.core_action,
            user_id=req.user_id,
        )
        product = db.get_product(product_id)

        audit_data = req.audit_data
        if audit_data:
            db.save_audit(product_id, audit_data)

        events = db.get_events(product_id)
        top_actions = analyzer.get_top_actions(events)
        drop_offs = analyzer.calculate_drop_off(events)
        active_users = analyzer.get_active_users(events)
        avg_session = analyzer.get_avg_session(events)
        patterns = analyzer.detect_patterns(events)

        insights = agent.generate_insights(
            product, top_actions, drop_offs,
            active_users, avg_session, patterns,
            audit_data=audit_data,
        )
        db.save_insight(product_id, insights["summary"], insights["recommended_actions"])

        return OnboardResponse(
            product_id=product_id,
            initial_insights=insights["summary"],
            audit_data=audit_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Onboarding failed: {str(e)}")


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

@app.get("/api/product/{product_id}", response_model=ProductResponse)
def get_product(product_id: int):
    product = db.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product #{product_id} not found")

    events = db.get_events(product_id)
    active_users = analyzer.get_active_users(events)
    avg_session = analyzer.get_avg_session(events)
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(events)

    return ProductResponse(
        id=product["id"],
        url=product["url"],
        product_type=product["product_type"],
        core_action=product["core_action"],
        created_at=product["created_at"],
        active_users=active_users,
        avg_session=avg_session,
        drop_off_rate=drop_offs[0]["drop_off_rate"] if drop_offs else "0%",
        top_action=top_actions[0]["action"] if top_actions else "N/A",
    )


# ---------------------------------------------------------------------------
# Behavior ingest
# ---------------------------------------------------------------------------

@app.post("/api/behavior/ingest", response_model=BehaviorIngestResponse)
def ingest_behavior(req: BehaviorIngestRequest):
    product = db.get_product(req.product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product #{req.product_id} not found. Have you onboarded it yet?",
        )
    try:
        count = db.insert_events(req.product_id, req.events)
        return BehaviorIngestResponse(ingested=True, count=count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest events: {str(e)}")


# ---------------------------------------------------------------------------
# Behavior query
# ---------------------------------------------------------------------------

@app.get("/api/behavior/{product_id}", response_model=BehaviorResponse)
def get_behavior(product_id: int):
    product = db.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product #{product_id} not found")

    events = db.get_events(product_id)
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(events)
    active_users = analyzer.get_active_users(events)
    avg_session = analyzer.get_avg_session(events)

    if active_users < 1000 and len(events) < 200:
        est = estimator.estimate_behavior(product)
        if est:
            return BehaviorResponse(
                top_actions=[
                    ActionDetail(
                        action=a["action"],
                        users=a["users"],
                        frequency=a["frequency"],
                        dropoff_after=a["dropoff_after"],
                    )
                    for a in est["top_actions"]
                ],
                drop_off_points=est["drop_off_points"],
                avg_session=est["avg_session"],
                active_users=est["active_users"],
            )

    return BehaviorResponse(
        top_actions=[
            ActionDetail(
                action=a["action"],
                users=a["count"],
                frequency=a["frequency"],
                dropoff_after=next(
                    (d["drop_off_rate"] for d in drop_offs if d["step"] == a["action"]),
                    "0%",
                ),
            )
            for a in top_actions
        ],
        drop_off_points=drop_offs,
        avg_session=avg_session,
        active_users=active_users,
    )


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

@app.get("/api/insights/{product_id}", response_model=InsightsResponse)
def get_insights(product_id: int):
    product = db.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product #{product_id} not found")

    events = db.get_events(product_id)
    active_users = analyzer.get_active_users(events)
    avg_session = analyzer.get_avg_session(events)
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(events)
    patterns = analyzer.detect_patterns(events)

    if active_users < 1000 and len(events) < 200:
        est = estimator.estimate_behavior(product)
        if est:
            active_users = est["active_users"]
            avg_session = est["avg_session"]
            top_actions = [
                {"action": a["action"], "count": a["users"], "frequency": a["frequency"]}
                for a in est["top_actions"]
            ]
            drop_offs = est["drop_off_points"]
            patterns = []

    insights = agent.generate_insights(
        product, top_actions, drop_offs,
        active_users, avg_session, patterns,
    )
    db.save_insight(product_id, insights["summary"], insights["recommended_actions"])

    return InsightsResponse(
        summary=insights["summary"],
        recommended_actions=[
            RecommendedAction(**a) for a in insights["recommended_actions"]
        ],
    )


# ---------------------------------------------------------------------------
# Agent chat
# ---------------------------------------------------------------------------

@app.post("/api/agent/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    product = db.get_product(req.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product #{req.product_id} not found")

    db.save_chat_message(req.product_id, req.user_id, "user", req.message)

    events = db.get_events(req.product_id)
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(events)
    active_users = analyzer.get_active_users(events)
    avg_session = analyzer.get_avg_session(events)
    patterns = analyzer.detect_patterns(events)
    chat_history = db.get_chat_history(req.product_id, req.user_id)

    if active_users < 1000 and len(events) < 200:
        est = estimator.estimate_behavior(product)
        if est:
            active_users = est["active_users"]
            avg_session = est["avg_session"]
            top_actions = [
                {"action": a["action"], "count": a["users"], "frequency": a["frequency"]}
                for a in est["top_actions"]
            ]
            drop_offs = est["drop_off_points"]
            patterns = []

    reply, data_point = agent.chat_with_agent(
        product, req.message,
        top_actions, drop_offs,
        active_users, avg_session,
        patterns, chat_history,
    )

    db.save_chat_message(req.product_id, req.user_id, "assistant", reply)

    return ChatResponse(reply=reply, data_point=data_point, confidence=0.85)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@app.get("/api/metrics/{product_id}", response_model=MetricsResponse)
def get_metrics(product_id: int):
    product = db.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product #{product_id} not found")

    events = db.get_events(product_id)
    active_users = analyzer.get_active_users(events)
    avg_session = analyzer.get_avg_session(events)
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(events)

    if active_users < 1000 and len(events) < 200:
        est = estimator.estimate_metrics(product)
        if est:
            return MetricsResponse(
                active_users=est["active_users"],
                avg_session=est["avg_session"],
                drop_off_rate=est["drop_off_rate"],
                top_action=est["top_action"],
            )

    return MetricsResponse(
        active_users=active_users,
        avg_session=avg_session,
        drop_off_rate=drop_offs[0]["drop_off_rate"] if drop_offs else "0%",
        top_action=top_actions[0]["action"] if top_actions else "N/A",
    )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("shipsense.main:app", host="0.0.0.0", port=8000, reload=True)
