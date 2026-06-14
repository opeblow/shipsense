import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from .models import (
    OnboardRequest, OnboardResponse,
    BehaviorIngestRequest, BehaviorIngestResponse,
    BehaviorResponse, ActionDetail,
    ChatRequest, ChatResponse,
    InsightsResponse, RecommendedAction,
    MetricsResponse, ProductResponse,
    HealthResponse,
)
from . import db
from . import analyzer
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
        events = db.get_events(product_id)
        top_actions = analyzer.get_top_actions(events)
        drop_offs = analyzer.calculate_drop_off(events)
        active_users = analyzer.get_active_users(events)
        avg_session = analyzer.get_avg_session(events)
        patterns = analyzer.detect_patterns(events)

        insights = agent.generate_insights(
            product, top_actions, drop_offs,
            active_users, avg_session, patterns,
        )
        db.save_insight(product_id, insights["summary"], insights["recommended_actions"])

        return OnboardResponse(
            product_id=product_id,
            initial_insights=insights["summary"],
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
    top_actions = analyzer.get_top_actions(events)
    drop_offs = analyzer.calculate_drop_off(events)
    active_users = analyzer.get_active_users(events)
    avg_session = analyzer.get_avg_session(events)
    patterns = analyzer.detect_patterns(events)

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
