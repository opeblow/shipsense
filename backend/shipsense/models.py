from pydantic import AliasChoices, BaseModel, Field, field_validator
from typing import List, Optional, Any
from datetime import datetime, timezone


# --- Request models ---

class ProductContext(BaseModel):
    target_user: str = Field(default="", max_length=240)
    user_problem: str = Field(default="", max_length=500)
    value_proposition: str = Field(default="", max_length=500)
    business_goal: str = Field(default="", max_length=240)
    constraints: str = Field(default="", max_length=500)

    @field_validator(
        "target_user",
        "user_problem",
        "value_proposition",
        "business_goal",
        "constraints",
    )
    @classmethod
    def clean_context_text(cls, value):
        return " ".join(value.strip().split())


class OnboardRequest(BaseModel):
    url: str
    product_type: str
    core_action: str
    user_id: str = "workspace-owner"
    critical_flow: List[str] = Field(default_factory=list)
    product_context: ProductContext = Field(default_factory=ProductContext)
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

    @field_validator("critical_flow")
    @classmethod
    def validate_critical_flow(cls, steps):
        cleaned = [step.strip() for step in steps if step.strip()]
        if cleaned and len(cleaned) < 2:
            raise ValueError("critical_flow must contain at least two steps")
        if len(cleaned) > 10:
            raise ValueError("critical_flow must contain 10 steps or fewer")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("critical_flow steps must be unique")
        return cleaned


class AuditUrlRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class BehaviorEvent(BaseModel):
    action: str = Field(validation_alias=AliasChoices("action", "name"))
    user_id: str = Field(validation_alias=AliasChoices("user_id", "anonymous_id"))
    timestamp: str = Field(validation_alias=AliasChoices("timestamp", "occurred_at"))
    event_id: Optional[str] = None
    schema_version: int = Field(default=1, ge=1)
    session_id: Optional[str] = None
    page_url: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action", "user_id")
    @classmethod
    def validate_required_text(cls, value):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @field_validator("action")
    @classmethod
    def validate_action_length(cls, value):
        if len(value) > 120:
            raise ValueError("action must be 120 characters or fewer")
        return value

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value):
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("timestamp must be valid ISO-8601") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()


class BehaviorIngestRequest(BaseModel):
    product_id: str
    collector_key: str
    events: List[BehaviorEvent]


class ChatRequest(BaseModel):
    product_id: str
    user_id: str
    message: str


class CriticalFlowRequest(BaseModel):
    steps: List[str]

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, steps):
        cleaned = [step.strip() for step in steps if step.strip()]
        if len(cleaned) < 2:
            raise ValueError("A critical flow requires at least two steps")
        if len(cleaned) > 10:
            raise ValueError("A critical flow supports up to 10 steps")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Critical flow steps must be unique")
        return cleaned


class ProductContextRequest(ProductContext):
    pass


# --- Response models ---

class OnboardResponse(BaseModel):
    product_id: str
    collector_key: str
    critical_flow: List[str]
    initial_insights: str
    audit_data: Optional[dict[str, Any]] = None
    audit_received: Optional[bool] = None


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
    pagespeed_error: Optional[str] = None
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
    h1_text: Optional[str] = None
    title_length: Optional[int] = None
    meta_description: Optional[bool] = None
    meta_description_text: Optional[str] = None
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
    primary_ctas: Optional[List[dict[str, Any]]] = None
    form_summaries: Optional[List[dict[str, Any]]] = None
    nav_labels: Optional[List[str]] = None
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
    id: str
    url: str
    product_type: str
    core_action: str
    critical_flow: List[str]
    product_context: ProductContext = Field(default_factory=ProductContext)
    is_sample: bool = False
    created_at: str
    active_users: int
    avg_session: str
    drop_off_rate: str
    top_action: str


class BehaviorIngestResponse(BaseModel):
    ingested: bool
    count: int


class WorkspaceResponse(BaseModel):
    workspace_id: str
    workspace_key: str


class ProductSummary(BaseModel):
    id: str
    url: str
    product_type: str
    core_action: str
    critical_flow: List[str]
    product_context: ProductContext = Field(default_factory=ProductContext)
    is_sample: bool = False
    created_at: str


class CriticalFlowResponse(BaseModel):
    product_id: str
    steps: List[str]


class ProductContextResponse(BaseModel):
    product_id: str
    context: ProductContext


class CollectorStatusResponse(BaseModel):
    product_id: str
    verified: bool
    event_count: int
    last_event_at: Optional[str] = None


class CollectorKeyResponse(BaseModel):
    product_id: str
    collector_key: str


class FlowStepReadiness(BaseModel):
    step: str
    position: int
    observed: bool
    event_count: int
    unique_users: int
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    possible_matches: List[str] = Field(default_factory=list)


class TransitionReadiness(BaseModel):
    step: str
    next_step: str
    users_who_reached: int
    users_who_continued: int
    minimum_sample: int
    sample_gap: int
    ready: bool
    orphaned_next_step_users: int
    out_of_order_users: int


class InstrumentationIssue(BaseModel):
    code: str
    severity: str
    step: Optional[str] = None
    message: str
    suggestion: str


class ObservedAction(BaseModel):
    action: str
    event_count: int
    unique_users: int


class InstrumentationReadinessResponse(BaseModel):
    product_id: str
    collector_connected: bool
    event_count: int
    last_event_at: Optional[str] = None
    flow_configured: bool
    configured_steps: List[str]
    coverage_count: int
    coverage_percent: int
    unique_users: int
    minimum_sample: int
    decision_ready: bool
    status: str
    flow_steps: List[FlowStepReadiness]
    transitions: List[TransitionReadiness]
    observed_actions: List[ObservedAction]
    issues: List[InstrumentationIssue]
    next_actions: List[str]


class SampleProductResponse(BaseModel):
    product_id: str
    label: str
    is_sample: bool = True


class ExperimentCreateRequest(BaseModel):
    product_id: str
    decision_id: int
    name: Optional[str] = None


class ExperimentResponse(BaseModel):
    id: str
    product_id: str
    decision_id: int
    name: str
    hypothesis: str
    target_metric: str
    baseline_value: str
    status: str
    shipped_at: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    created_at: str


class ActionDetail(BaseModel):
    action: str
    event_count: int
    unique_users: int
    event_frequency: str
    user_frequency: str
    dropoff_after: str


class BehaviorResponse(BaseModel):
    top_actions: List[ActionDetail]
    drop_off_points: List[dict]
    event_count: int
    avg_session: str
    active_users: int
    session_count: int
    measurable_session_count: int


class RecommendedAction(BaseModel):
    title: str
    description: str
    effort: str
    impact: str
    priority: int


class InsightsResponse(BaseModel):
    summary: str
    recommended_actions: List[RecommendedAction]


class EvidenceRecord(BaseModel):
    id: str
    source_type: str
    metric_key: str
    value: Any
    unit: str
    sample_size: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionResponse(BaseModel):
    decision_id: int
    version: int
    title: str
    problem: str
    evidence: List[EvidenceRecord]
    affected_flow: Optional[str] = None
    recommendation: str
    expected_outcome: str
    target_metric: str
    baseline_value: str
    effort: str
    impact: str
    confidence: float
    confidence_reasons: List[str]
    invalidating_conditions: List[str]
    status: str
    created_at: str
    source_snapshot_id: str
    stale: bool = False
    stale_reasons: List[str] = Field(default_factory=list)
    evidence_updated_at: Optional[str] = None
    hypotheses: List[dict[str, Any]] = Field(default_factory=list)


class AnalystCitation(BaseModel):
    id: str
    source_type: str
    label: str
    value: Any
    unit: str
    sample_size: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    reply: str
    citations: List[AnalystCitation] = Field(default_factory=list)
    follow_up: str = ""
    suggested_questions: List[str] = Field(default_factory=list)
    confidence: float
    confidence_reasons: List[str] = Field(default_factory=list)


class AnalystContextResponse(BaseModel):
    current_decision: Optional[dict[str, Any]] = None
    experiments: List[dict[str, Any]] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    evidence_count: int


class MetricsResponse(BaseModel):
    active_users: int
    avg_session: str
    drop_off_rate: str
    top_action: str


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
