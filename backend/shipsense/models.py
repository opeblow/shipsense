from pydantic import BaseModel, field_validator
from typing import List, Optional, Any
from datetime import datetime


# --- Request models ---

class OnboardRequest(BaseModel):
    url: str
    product_type: str
    core_action: str
    user_id: str
    audit_data: Optional[dict[str, Any]] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("product_type")
    @classmethod
    def validate_product_type(cls, v):
        allowed = {"consumers", "b2b", "internal tool"}
        if v.lower() not in allowed:
            raise ValueError(f"product_type must be one of: {', '.join(allowed)}")
        return v.lower()


class AuditUrlRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class BehaviorEvent(BaseModel):
    action: str
    user_id: str
    timestamp: str


class BehaviorIngestRequest(BaseModel):
    product_id: int
    events: List[BehaviorEvent]


class ChatRequest(BaseModel):
    product_id: int
    user_id: str
    message: str


# --- Response models ---

class OnboardResponse(BaseModel):
    product_id: int
    initial_insights: str
    audit_data: Optional[dict[str, Any]] = None


class AuditUrlResponse(BaseModel):
    url: str
    performance_score: Optional[int] = None
    accessibility_score: Optional[int] = None
    seo_score: Optional[int] = None
    core_web_vitals: Optional[dict[str, Any]] = None
    pagespeed_opportunities: Optional[List[dict[str, Any]]] = None
    form_field_count: Optional[int] = None
    has_guest_checkout: Optional[bool] = None
    tracking_script_count: Optional[int] = None
    has_mobile_viewport: Optional[bool] = None
    page_title: Optional[str] = None
    meta_description: Optional[bool] = None
    ctas_above_fold: Optional[int] = None
    has_cookie_banner: Optional[bool] = None
    has_popup: Optional[bool] = None
    has_autoplay_video: Optional[bool] = None
    pagespeed_error: Optional[str] = None
    scrape_error: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    url: str
    product_type: str
    core_action: str
    created_at: str
    active_users: int
    avg_session: str
    drop_off_rate: str
    top_action: str


class BehaviorIngestResponse(BaseModel):
    ingested: bool
    count: int


class ActionDetail(BaseModel):
    action: str
    users: int
    frequency: str
    dropoff_after: str


class BehaviorResponse(BaseModel):
    top_actions: List[ActionDetail]
    drop_off_points: List[dict]
    avg_session: str
    active_users: int


class RecommendedAction(BaseModel):
    title: str
    description: str
    effort: str
    impact: str
    priority: int


class InsightsResponse(BaseModel):
    summary: str
    recommended_actions: List[RecommendedAction]


class ChatResponse(BaseModel):
    reply: str
    data_point: str
    confidence: float


class MetricsResponse(BaseModel):
    active_users: int
    avg_session: str
    drop_off_rate: str
    top_action: str


class HealthResponse(BaseModel):
    status: str
    version: str
