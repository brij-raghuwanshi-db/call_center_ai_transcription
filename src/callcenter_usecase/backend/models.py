from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from .. import __version__


class VersionOut(BaseModel):
    version: str

    @classmethod
    def from_metadata(cls):
        return cls(version=__version__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class CallStatus(str, Enum):
    READY = "ready"
    ACTIVE = "active"
    ENDED = "ended"


class Speaker(str, Enum):
    AGENT = "Agent"
    PATIENT = "Patient"
    UNKNOWN = "Unknown"


class FeedbackType(str, Enum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    WRONG = "wrong"
    USED = "used"
    IGNORED = "ignored"


class CadenceMode(str, Enum):
    EVERY_FEW_SECONDS = "every_few_seconds"
    COMPLETED_SENTENCE = "completed_sentence"


class DemoMode(str, Enum):
    SYNTHETIC = "synthetic"
    UPLOAD = "upload"
    MICROPHONE = "microphone"
    REPLAY = "replay"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Scenario(BaseModel):
    id: str
    title: str
    description: str
    patient_name: str
    intent: str
    expected_risk_level: RiskLevel


class TranscriptSegment(BaseModel):
    segment_id: str = Field(default_factory=lambda: new_id("seg"))
    call_id: str
    speaker: Speaker = Speaker.UNKNOWN
    text: str
    is_partial: bool = False
    start_ms: int = 0
    end_ms: int = 0
    asr_latency_ms: int = 0
    confidence: float = 0.9
    created_at: datetime = Field(default_factory=utc_now)


class Citation(BaseModel):
    document_id: str
    title: str
    section: str
    quote: str
    score: float = 0.8


class Alert(BaseModel):
    code: str
    title: str
    detail: str
    risk_level: RiskLevel = RiskLevel.MEDIUM


class Recommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: new_id("rec"))
    call_id: str
    trigger_segment_id: str | None = None
    intent: str
    topic: str
    patient_state: str
    risk_level: RiskLevel
    urgency_level: RiskLevel
    recommended_response: str
    next_best_action: str
    action_rationale: str
    confidence: float
    citations: list[Citation] = Field(default_factory=list)
    alerts: list[Alert] = Field(default_factory=list)
    compliance_notes: list[str] = Field(default_factory=list)
    summary_update: str
    structured_slots: dict[str, Any] = Field(default_factory=dict)
    should_escalate: bool = False
    escalation_reason: str | None = None
    llm_latency_ms: int = 0
    created_at: datetime = Field(default_factory=utc_now)


class AgentFeedback(BaseModel):
    feedback_id: str = Field(default_factory=lambda: new_id("fb"))
    recommendation_id: str
    call_id: str
    feedback_type: FeedbackType
    free_text: str | None = None
    created_by: str = "demo-agent"
    created_at: datetime = Field(default_factory=utc_now)


class CallSettings(BaseModel):
    auto_recommendations_enabled: bool = True
    cadence_mode: CadenceMode = CadenceMode.EVERY_FEW_SECONDS
    redaction_enabled: bool = False
    demo_mode: DemoMode = DemoMode.SYNTHETIC


class ActiveCall(BaseModel):
    call_id: str
    status: CallStatus = CallStatus.ACTIVE
    scenario_id: str
    scenario_title: str
    patient_name: str
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    current_speaker: Speaker = Speaker.UNKNOWN
    latest_transcript: str = ""
    latest_intent: str = "unknown"
    current_risk_level: RiskLevel = RiskLevel.LOW
    current_recommendation_id: str | None = None
    settings: CallSettings = Field(default_factory=CallSettings)
    summary_draft: str = ""


class StartCallIn(BaseModel):
    scenario_id: str = "symptom_escalation"
    settings: CallSettings = Field(default_factory=CallSettings)


class StartCallOut(BaseModel):
    call: ActiveCall
    transcript: list[TranscriptSegment]
    recommendation: Recommendation | None = None


class AudioChunkIn(BaseModel):
    call_id: str
    chunk_id: str = Field(default_factory=lambda: new_id("chunk"))
    audio_base64: str | None = None
    transcript_text: str | None = None
    cumulative_audio: bool = False
    speaker_hint: Speaker | None = None
    sample_rate: int = 16000
    language: str = "en-US"
    mime_type: str | None = None
    filename: str | None = None


class AudioUploadOut(BaseModel):
    call_id: str
    filename: str
    bytes_received: int
    message: str
    storage_path: str | None = None


class AnalyzeIn(BaseModel):
    call_id: str
    transcript_window: str | None = None
    trigger_segment_id: str | None = None


class FeedbackIn(BaseModel):
    feedback_type: FeedbackType
    free_text: str | None = None


class DemoMetrics(BaseModel):
    active_calls: int
    total_calls: int
    transcript_segments: int
    recommendations: int
    feedback_items: int
    avg_asr_latency_ms: float
    avg_llm_latency_ms: float


class AppConfigOut(BaseModel):
    app_name: str
    llm_endpoint_name: str
    asr_endpoint_name: str
    vector_search_endpoint_name: str
    vector_search_index_name: str
    uc_catalog: str
    uc_schema: str
    delta_schema_name: str
    use_databricks_asr: bool
    use_mock_asr: bool
    use_mock_llm: bool
    use_scripted_transcript_fallback: bool
    enable_redaction: bool
    enable_acoustic_features: bool


class KnowledgeDocument(BaseModel):
    document_id: str
    title: str
    section: str
    content: str
    tags: list[str]


class EvaluationExample(BaseModel):
    scenario_id: str
    expected_intent: str
    expected_risk_level: RiskLevel
    expected_next_best_action: str
    expected_escalation: bool


class ActiveCallTable(SQLModel, table=True):
    call_id: str = SQLField(primary_key=True)
    status: str
    scenario_id: str
    scenario_title: str
    patient_name: str
    latest_transcript: str = ""
    latest_intent: str = "unknown"
    current_risk_level: str = "low"
    current_recommendation_id: str | None = None
    started_at: datetime = SQLField(default_factory=utc_now)
    ended_at: datetime | None = None


class TranscriptSegmentTable(SQLModel, table=True):
    segment_id: str = SQLField(primary_key=True)
    call_id: str = SQLField(index=True)
    speaker: str
    text: str
    is_partial: bool = False
    start_ms: int = 0
    end_ms: int = 0
    asr_latency_ms: int = 0
    confidence: float = 0.9
    created_at: datetime = SQLField(default_factory=utc_now)


class RecommendationTable(SQLModel, table=True):
    recommendation_id: str = SQLField(primary_key=True)
    call_id: str = SQLField(index=True)
    trigger_segment_id: str | None = None
    intent: str
    topic: str
    risk_level: str
    recommended_response: str
    next_best_action: str
    confidence: float
    llm_latency_ms: int = 0
    created_at: datetime = SQLField(default_factory=utc_now)


class FeedbackTable(SQLModel, table=True):
    feedback_id: str = SQLField(primary_key=True)
    recommendation_id: str = SQLField(index=True)
    call_id: str = SQLField(index=True)
    feedback_type: str
    free_text: str | None = None
    created_by: str = "demo-agent"
    created_at: datetime = SQLField(default_factory=utc_now)


class CallSummaryWindowTable(SQLModel, table=True):
    summary_id: str = SQLField(primary_key=True)
    call_id: str = SQLField(index=True)
    window_index: int
    start_seconds: int
    end_seconds: int
    summary_text: str
    source: str = "backend_transcript_rollup"
    created_at: datetime = SQLField(default_factory=utc_now)


class NextBestActionTable(SQLModel, table=True):
    action_id: str = SQLField(primary_key=True)
    recommendation_id: str = SQLField(index=True)
    call_id: str = SQLField(index=True)
    trigger_segment_id: str | None = None
    intent: str
    topic: str
    patient_state: str
    risk_level: str
    urgency_level: str
    recommended_response: str
    next_best_action: str
    action_rationale: str
    confidence: float
    should_escalate: bool = False
    escalation_reason: str | None = None
    llm_latency_ms: int = 0
    created_at: datetime = SQLField(default_factory=utc_now)


class RecommendationAlertTable(SQLModel, table=True):
    alert_row_id: str = SQLField(primary_key=True)
    recommendation_id: str = SQLField(index=True)
    call_id: str = SQLField(index=True)
    alert_index: int
    code: str
    title: str
    detail: str
    risk_level: str
    created_at: datetime = SQLField(default_factory=utc_now)


class RecommendationCitationTable(SQLModel, table=True):
    citation_row_id: str = SQLField(primary_key=True)
    recommendation_id: str = SQLField(index=True)
    call_id: str = SQLField(index=True)
    citation_index: int
    document_id: str
    title: str
    section: str
    quote: str
    score: float = 0.8
    created_at: datetime = SQLField(default_factory=utc_now)


class AudioArtifactTable(SQLModel, table=True):
    audio_artifact_id: str = SQLField(primary_key=True)
    call_id: str = SQLField(index=True)
    filename: str
    storage_path: str | None = None
    bytes_received: int
    source: str = "volume_upload"
    created_at: datetime = SQLField(default_factory=utc_now)
