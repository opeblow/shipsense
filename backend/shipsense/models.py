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
    # PageSpeed
    performance_score: Optional[int] = None
    accessibility_score: Optional[int] = None
    seo_score: Optional[int] = None
    best_practices_score: Optional[int] = None
    core_web_vitals: Optional[dict[str, Any]] = None
    pagespeed_opportunities: Optional[List[dict[str, Any]]] = None
    pagespeed_diagnostics: Optional[List[dict[str, Any]]] = None
    # Security headers
    security_headers: Optional[dict[str, Any]] = None
    content_encoding: Optional[str] = None
    cache_control: Optional[str] = None
    has_compression: Optional[bool] = None
    content_type: Optional[str] = None
    server: Optional[str] = None
    redirect_count: Optional[int] = None
    final_status: Optional[int] = None
    # Forms / conversion
    form_field_count: Optional[int] = None
    form_count: Optional[int] = None
    has_password_field: Optional[bool] = None
    has_email_field: Optional[bool] = None
    submit_button_count: Optional[int] = None
    has_guest_checkout: Optional[bool] = None
    # Tracking
    tracking_script_count: Optional[int] = None
    tracking_tools: Optional[List[str]] = None
    # Mobile
    has_mobile_viewport: Optional[bool] = None
    viewport_width: Optional[str] = None
    # SEO
    page_title: Optional[str] = None
    title_length: Optional[int] = None
    meta_description: Optional[bool] = None
    meta_description_length: Optional[int] = None
    has_canonical: Optional[bool] = None
    has_hreflang: Optional[bool] = None
    has_robots_meta: Optional[bool] = None
    og_tag_count: Optional[int] = None
    twitter_tag_count: Optional[int] = None
    has_json_ld: Optional[bool] = None
    # Headings
    h1_count: Optional[int] = None
    h2_count: Optional[int] = None
    heading_issues: Optional[List[str]] = None
    # Images
    total_images: Optional[int] = None
    images_missing_alt: Optional[int] = None
    images_missing_dimensions: Optional[int] = None
    images_lazy_loaded: Optional[int] = None
    # Links
    internal_link_count: Optional[int] = None
    external_link_count: Optional[int] = None
    broken_or_js_links: Optional[int] = None
    # Performance signals
    render_blocking_resources: Optional[int] = None
    preconnect_hints: Optional[int] = None
    preload_hints: Optional[int] = None
    has_web_fonts: Optional[bool] = None
    has_font_display: Optional[bool] = None
    # Content
    word_count: Optional[int] = None
    cta_count: Optional[int] = None
    has_cookie_banner: Optional[bool] = None
    has_popup: Optional[bool] = None
    has_autoplay_video: Optional[bool] = None
    has_hamburger_menu: Optional[bool] = None
    has_search: Optional[bool] = None
    has_footer: Optional[bool] = None
    has_nav: Optional[bool] = None
    # Accessibility
    aria_landmark_count: Optional[int] = None
    aria_labels_count: Optional[int] = None
    has_skip_link: Optional[bool] = None
    # Resources
    inline_script_count: Optional[int] = None
    external_script_count: Optional[int] = None
    inline_style_count: Optional[int] = None
    external_style_count: Optional[int] = None
    # Tech
    detected_frameworks: Optional[List[str]] = None
    # Failure signals
    scrape_failed: Optional[bool] = None


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
