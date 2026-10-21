from __future__ import annotations

import base64
import io
import json
import re
import time
import wave
from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Iterable

from databricks.sdk import WorkspaceClient
from fastapi import UploadFile

from .models import (
    ActiveCall,
    AgentFeedback,
    Alert,
    AnalyzeIn,
    AppConfigOut,
    AudioChunkIn,
    AudioUploadOut,
    CallSettings,
    CallStatus,
    Citation,
    DemoMetrics,
    EvaluationExample,
    FeedbackIn,
    KnowledgeDocument,
    Recommendation,
    RiskLevel,
    Scenario,
    Speaker,
    StartCallIn,
    StartCallOut,
    TranscriptSegment,
    new_id,
    utc_now,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
AUDIO_DIR = DATA_DIR / "generated_audio"
AUDIT_DIR = DATA_DIR / "delta_audit_mock"
logger = logging.getLogger(__name__)


SCENARIOS: list[Scenario] = [
    Scenario(
        id="appointment_retention",
        title="Appointment Retention",
        description="Patient wants to cancel a follow-up visit because they feel overwhelmed.",
        patient_name="Maria Johnson",
        intent="appointment_retention",
        expected_risk_level=RiskLevel.MEDIUM,
    ),
    Scenario(
        id="medication_concern",
        title="Medication Concern",
        description="Patient is worried about side effects and may stop taking medication.",
        patient_name="Robert Ellis",
        intent="medication_concern",
        expected_risk_level=RiskLevel.MEDIUM,
    ),
    Scenario(
        id="billing_confusion",
        title="Billing Confusion",
        description="Patient is frustrated about a bill and threatens to stop care.",
        patient_name="Denise Walker",
        intent="billing_confusion",
        expected_risk_level=RiskLevel.LOW,
    ),
    Scenario(
        id="symptom_escalation",
        title="Symptom Escalation",
        description="Patient describes worsening symptoms and needs triage escalation.",
        patient_name="James Miller",
        intent="symptom_escalation",
        expected_risk_level=RiskLevel.HIGH,
    ),
    Scenario(
        id="care_navigation",
        title="Care Navigation",
        description="Patient is unsure what to do after discharge and needs next steps.",
        patient_name="Linda Chen",
        intent="care_navigation",
        expected_risk_level=RiskLevel.LOW,
    ),
]


SCRIPTED_SEGMENTS: dict[str, list[tuple[Speaker, str]]] = {
    "appointment_retention": [
        (Speaker.AGENT, "Thank you for calling Call Center, this is Ava. How can I help today?"),
        (Speaker.PATIENT, "I think I need to cancel my follow-up appointment. I cannot keep missing work."),
        (Speaker.AGENT, "I understand. Missing work is stressful. Can I ask what time windows are easiest for you?"),
        (Speaker.PATIENT, "Early morning might work, but I am not sure the appointment is even worth it."),
        (Speaker.AGENT, "Your follow-up helps the care team catch issues early. I can look for an earlier slot and confirm transportation options."),
        (Speaker.PATIENT, "If you can find something before work, I would probably keep it."),
    ],
    "medication_concern": [
        (Speaker.AGENT, "Thank you for calling Call Center. What medication question can I help route today?"),
        (Speaker.PATIENT, "This new medicine makes me dizzy. I am thinking about stopping it."),
        (Speaker.AGENT, "I am sorry that is happening. Please do not stop a prescribed medication without clinical guidance."),
        (Speaker.PATIENT, "I just feel off and I do not know if that is normal."),
        (Speaker.AGENT, "I can connect you with a nurse to review symptoms and next steps. Are you having trouble breathing or chest pain?"),
        (Speaker.PATIENT, "No chest pain, but I would like to talk with a nurse."),
    ],
    "billing_confusion": [
        (Speaker.AGENT, "Call Center, this is Ava. How can I help you today?"),
        (Speaker.PATIENT, "I got a bill I do not understand. If this is how it works, I am done with these visits."),
        (Speaker.AGENT, "I hear how frustrating that is. Let us separate the billing question from the care you still need."),
        (Speaker.PATIENT, "Nobody explained why I owe this much."),
        (Speaker.AGENT, "I can route the billing review and keep your care plan moving while that is checked."),
        (Speaker.PATIENT, "Okay, I just do not want to be surprised again."),
    ],
    "symptom_escalation": [
        (Speaker.AGENT, "Thank you for calling Call Center. Tell me what is going on today."),
        (Speaker.PATIENT, "My chest feels tight and I have been short of breath since this morning."),
        (Speaker.AGENT, "I am sorry you are feeling that. Because you mentioned chest tightness and shortness of breath, I need to escalate this right away."),
        (Speaker.PATIENT, "I was hoping it would pass, but it is getting worse."),
        (Speaker.AGENT, "If symptoms are severe or worsening, please call emergency services now. I can also get a nurse on the line immediately."),
        (Speaker.PATIENT, "Please get the nurse. I am scared."),
    ],
    "care_navigation": [
        (Speaker.AGENT, "Call Center, this is Ava. What can I help with?"),
        (Speaker.PATIENT, "I was discharged yesterday and I do not know who I am supposed to call next."),
        (Speaker.AGENT, "I can help organize the next step. Do you have your discharge paperwork nearby?"),
        (Speaker.PATIENT, "Yes, but it is confusing."),
        (Speaker.AGENT, "No problem. We can confirm your follow-up appointment, medication questions, and who to call if symptoms change."),
        (Speaker.PATIENT, "That would help a lot."),
    ],
}


KNOWLEDGE_BASE: list[KnowledgeDocument] = [
    KnowledgeDocument(
        document_id="kb_appointment_retention",
        title="Appointment Retention Playbook",
        section="Barrier discovery",
        content="When a patient wants to cancel, acknowledge the barrier, ask about scheduling or transportation constraints, and offer a concrete alternative before ending the call.",
        tags=["appointment", "retention", "scheduling"],
    ),
    KnowledgeDocument(
        document_id="kb_medication_concern",
        title="Medication Concern Handling Guide",
        section="Do not discontinue without clinical guidance",
        content="If a patient reports side effects or wants to stop medication, advise them not to discontinue prescribed therapy without clinician direction and offer nurse or pharmacist escalation.",
        tags=["medication", "side effects", "nurse"],
    ),
    KnowledgeDocument(
        document_id="kb_billing_confusion",
        title="Billing De-escalation Guide",
        section="Separate billing stress from care continuation",
        content="For billing frustration, validate the concern, route billing review, and reinforce that care continuity should not pause while the billing issue is investigated.",
        tags=["billing", "frustration", "retention"],
    ),
    KnowledgeDocument(
        document_id="kb_symptom_escalation",
        title="Symptom Escalation and Nurse Triage Policy",
        section="Chest pain or shortness of breath",
        content="Chest tightness, chest pain, severe shortness of breath, fainting, or rapidly worsening symptoms require urgent escalation to nurse triage or emergency services guidance.",
        tags=["symptom", "escalation", "urgent", "chest", "breath"],
    ),
    KnowledgeDocument(
        document_id="kb_care_navigation",
        title="Care Navigation Workflow",
        section="Post-discharge next steps",
        content="For post-discharge confusion, confirm the follow-up appointment, medication questions, warning signs, and the correct contact path for symptom changes.",
        tags=["care navigation", "discharge", "follow-up"],
    ),
    KnowledgeDocument(
        document_id="kb_hipaa",
        title="HIPAA-Safe Communication Checklist",
        section="Identity and privacy",
        content="Before discussing protected health details, verify identity using approved identifiers and avoid unnecessary disclosure of sensitive information.",
        tags=["hipaa", "privacy", "identity"],
    ),
]


EVALUATION_SET: list[EvaluationExample] = [
    EvaluationExample(
        scenario_id=scenario.id,
        expected_intent=scenario.intent,
        expected_risk_level=scenario.expected_risk_level,
        expected_next_best_action={
            "appointment_retention": "Offer an alternate appointment time and identify the scheduling barrier.",
            "medication_concern": "Escalate to a nurse or pharmacist and advise not stopping medication without guidance.",
            "billing_confusion": "Validate frustration, route billing review, and keep care plan intact.",
            "symptom_escalation": "Escalate immediately to nurse triage or emergency guidance.",
            "care_navigation": "Clarify discharge next steps and confirm follow-up plan.",
        }[scenario.id],
        expected_escalation=scenario.id in {"medication_concern", "symptom_escalation"},
    )
    for scenario in SCENARIOS
]


@dataclass
class DemoState:
    calls: dict[str, ActiveCall] = field(default_factory=dict)
    transcripts: dict[str, list[TranscriptSegment]] = field(default_factory=dict)
    recommendations: dict[str, list[Recommendation]] = field(default_factory=dict)
    cumulative_asr_text: dict[str, str] = field(default_factory=dict)
    recommendation_inflight: set[str] = field(default_factory=set)
    last_recommendation_started_at: dict[str, float] = field(default_factory=dict)
    feedback: list[AgentFeedback] = field(default_factory=list)
    uploads: dict[str, AudioUploadOut] = field(default_factory=dict)


@dataclass
class _ServingChatMessage:
    role: str
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


STATE = DemoState()


def _scenario_by_id(scenario_id: str) -> Scenario:
    return next((s for s in SCENARIOS if s.id == scenario_id), SCENARIOS[3])


def _append_audit(kind: str, payload: dict) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    path = AUDIT_DIR / f"{kind}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, default=str) + "\n")


def list_scenarios() -> list[Scenario]:
    return SCENARIOS


def list_knowledge_documents() -> list[KnowledgeDocument]:
    return KNOWLEDGE_BASE


def list_evaluation_examples() -> list[EvaluationExample]:
    return EVALUATION_SET


def start_call(payload: StartCallIn) -> StartCallOut:
    scenario = _scenario_by_id(payload.scenario_id)
    call = ActiveCall(
        call_id=new_id("call"),
        scenario_id=scenario.id,
        scenario_title=scenario.title,
        patient_name=scenario.patient_name,
        latest_intent=scenario.intent,
        current_risk_level=scenario.expected_risk_level,
        settings=payload.settings,
        summary_draft=f"Call started for {scenario.patient_name}: {scenario.description}",
    )
    STATE.calls[call.call_id] = call
    STATE.transcripts[call.call_id] = []
    STATE.recommendations[call.call_id] = []
    STATE.cumulative_asr_text[call.call_id] = ""
    STATE.last_recommendation_started_at[call.call_id] = 0
    _append_audit("call_events", {"event": "call_started", "call": call.model_dump()})
    return StartCallOut(call=call, transcript=[], recommendation=None)


def warm_asr_endpoint(config) -> None:
    if not getattr(config, "use_databricks_asr", False):
        return
    started = time.perf_counter()
    response = _query_serving_endpoint(
        config.asr_endpoint_name,
        {
            "call_id": "warmup",
            "chunk_id": "warmup",
            "audio_base64": _silent_wav_base64(),
            "sample_rate": 16000,
            "language": "en-US",
        },
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "ASR warmup endpoint=%s completed in %s ms with_response=%s",
        config.asr_endpoint_name,
        elapsed_ms,
        response is not None,
    )


def stop_call(call_id: str) -> ActiveCall:
    call = get_call(call_id)
    if call.status != CallStatus.ENDED:
        call.status = CallStatus.ENDED
        call.ended_at = utc_now()
        _append_audit("call_events", {"event": "call_ended", "call": call.model_dump()})
    return call


def get_call(call_id: str) -> ActiveCall:
    if call_id not in STATE.calls:
        raise KeyError(f"Unknown call_id {call_id}")
    return STATE.calls[call_id]


def active_calls() -> list[ActiveCall]:
    return [c for c in STATE.calls.values() if c.status == CallStatus.ACTIVE]


def transcript_for_call(call_id: str) -> list[TranscriptSegment]:
    get_call(call_id)
    return STATE.transcripts[call_id]


def recommendations_for_call(call_id: str) -> list[Recommendation]:
    get_call(call_id)
    return STATE.recommendations[call_id]


def latest_recommendation(call_id: str) -> Recommendation | None:
    recs = recommendations_for_call(call_id)
    return recs[-1] if recs else None


def _script_segment(call: ActiveCall, index: int | None) -> tuple[Speaker, str]:
    script = SCRIPTED_SEGMENTS[call.scenario_id]
    if index is None:
        index = len(STATE.transcripts[call.call_id])
    return script[index % len(script)]


def transcribe_chunk(payload: AudioChunkIn, config=None) -> TranscriptSegment:
    started = time.perf_counter()
    call = get_call(payload.call_id)
    if call.status == CallStatus.ENDED:
        raise ValueError("call already ended")
    use_databricks_asr = bool(getattr(config, "use_databricks_asr", False))
    speaker = payload.speaker_hint or Speaker.PATIENT
    text = payload.transcript_text.strip() if payload.transcript_text else ""
    served_confidence: float | None = None
    if payload.audio_base64:
        try:
            base64.b64decode(payload.audio_base64, validate=False)
        except Exception:
            pass
    if config is not None and use_databricks_asr and payload.audio_base64:
        asr_started = time.perf_counter()
        mime_type = (payload.mime_type or "").lower()
        filename = payload.filename or ("chunk.wav" if "wav" in mime_type else "chunk.webm")
        served = _query_serving_endpoint(
            config.asr_endpoint_name,
            {
                "call_id": call.call_id,
                "chunk_id": payload.chunk_id,
                "audio_base64": payload.audio_base64,
                "sample_rate": payload.sample_rate,
                "language": payload.language,
                "filename": filename,
                "mime_type": mime_type,
            },
        )
        logger.info(
            "ASR endpoint=%s call_id=%s chunk_id=%s completed in %s ms",
            config.asr_endpoint_name,
            call.call_id,
            payload.chunk_id,
            int((time.perf_counter() - asr_started) * 1000),
        )
        served_text = _extract_served_text(served)
        served_error = _extract_served_error(served)
        served_confidence = _extract_served_confidence(served)
        if served_error and not served_text:
            logger.warning(
                "ASR endpoint=%s call_id=%s chunk_id=%s error=%s",
                config.asr_endpoint_name,
                call.call_id,
                payload.chunk_id,
                served_error,
            )
            raise RuntimeError(f"ASR serving error: {served_error}")
        if served_text:
            served_text = _clean_asr_text(served_text)
            if payload.cumulative_audio:
                text = _new_cumulative_asr_text(call.call_id, served_text)
            else:
                text = _new_overlap_asr_text(call.call_id, served_text)
            logger.info("ASR produced %s character(s) for call_id=%s", len(text), call.call_id)
        elif served is None:
            logger.warning(
                "ASR endpoint=%s call_id=%s returned no response",
                config.asr_endpoint_name,
                call.call_id,
            )
    if text:
        speaker, text = _apply_speaker_label(text, speaker)
        text = _clean_asr_text(text)
    if not text:
        raise ValueError(
            "No transcript text was produced. Browser ASR mode requires transcript_text; "
            "Databricks ASR mode requires a serving endpoint response."
        )
    elapsed_ms = int((time.perf_counter() - started) * 1000) + 120
    existing = STATE.transcripts[call.call_id]
    asr_confidence = served_confidence if served_confidence is not None else 0.8
    if asr_confidence < 0.30:
        logger.info(
            "Dropping low-confidence ASR call_id=%s conf=%s text=%s",
            call.call_id,
            asr_confidence,
            text,
        )
        raise ValueError("low-confidence ASR")
    segment = TranscriptSegment(
        call_id=call.call_id,
        speaker=speaker,
        text=text,
        is_partial=False,
        start_ms=len(existing) * 8000,
        end_ms=(len(existing) + 1) * 8000,
        asr_latency_ms=elapsed_ms,
        confidence=asr_confidence,
    )
    add_transcript_segment(segment)
    return segment


def reserve_auto_recommendation(call_id: str, *, min_interval_seconds: float = 8.0) -> bool:
    call = get_call(call_id)
    if not call.settings.auto_recommendations_enabled:
        return False
    now = time.monotonic()
    if call_id in STATE.recommendation_inflight:
        return False
    last_started = STATE.last_recommendation_started_at.get(call_id, 0)
    if now - last_started < min_interval_seconds:
        return False
    STATE.recommendation_inflight.add(call_id)
    STATE.last_recommendation_started_at[call_id] = now
    return True


def run_reserved_recommendation(payload: AnalyzeIn, config=None) -> Recommendation | None:
    try:
        return analyze_call(payload, config=config)
    except Exception as error:
        logger.warning("Auto recommendation for call %s failed: %s", payload.call_id, error)
        return None
    finally:
        STATE.recommendation_inflight.discard(payload.call_id)


def _apply_speaker_label(text: str, default_speaker: Speaker) -> tuple[Speaker, str]:
    cleaned = text.strip()
    patterns = [
        (Speaker.AGENT, r"^(agent speaking|this is the agent|representative speaking|representative|agent)[:,\-\s]+"),
        (Speaker.PATIENT, r"^(patient speaking|caller speaking|customer speaking|patient|caller|customer)[:,\-\s]+"),
    ]
    for speaker, pattern in patterns:
        match = re.match(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            cleaned = cleaned[match.end() :].strip()
            return speaker, cleaned
    return default_speaker, cleaned


def _new_cumulative_asr_text(call_id: str, served_text: str) -> str:
    previous = STATE.cumulative_asr_text.get(call_id, "").strip()
    current = served_text.strip()
    if not current:
        return ""
    delta = _transcript_delta(previous, current) if previous else current
    if delta:
        STATE.cumulative_asr_text[call_id] = current
    return delta


def _transcript_delta(previous: str, current: str) -> str:
    if current == previous:
        return ""
    if current.startswith(previous):
        return current[len(previous) :].strip()
    if previous in current:
        return current.split(previous, 1)[1].strip()

    previous_tokens = _normalized_token_spans(previous)
    current_tokens = _normalized_token_spans(current)
    max_overlap = min(len(previous_tokens), len(current_tokens))
    overlap = 0
    for size in range(max_overlap, 0, -1):
        if [token for token, _start in previous_tokens[-size:]] == [
            token for token, _start in current_tokens[:size]
        ]:
            overlap = size
            break
    if overlap:
        start = current_tokens[overlap][1] if overlap < len(current_tokens) else len(current)
        return current[start:].strip(" ,.;:-")
    return current


def _normalized_token_spans(text: str) -> list[tuple[str, int]]:
    tokens: list[tuple[str, int]] = []
    for match in re.finditer(r"[A-Za-z]+|\d+", text.lower()):
        value = match.group(0)
        if value.isdigit() and len(value) > 1:
            tokens.extend((digit, match.start()) for digit in value)
        else:
            tokens.append((value, match.start()))
    return tokens


def add_transcript_segment(segment: TranscriptSegment) -> TranscriptSegment:
    call = get_call(segment.call_id)
    STATE.transcripts[segment.call_id].append(segment)
    call.current_speaker = segment.speaker
    call.latest_transcript = segment.text
    call.summary_draft = _summary_for(segment.call_id)
    _append_audit("transcript_events", segment.model_dump())
    return segment


async def store_upload(call_id: str, upload: UploadFile, config=None) -> AudioUploadOut:
    get_call(call_id)
    audio_dir = Path(getattr(config, "audio_volume_path", AUDIO_DIR)) if config else AUDIO_DIR
    content = await upload.read()
    safe_name = upload.filename or f"{call_id}.wav"
    path = audio_dir / safe_name
    if str(path).startswith("/Volumes/"):
        ws = WorkspaceClient()
        ws.files.create_directory(str(audio_dir))
        ws.files.upload(str(path), io.BytesIO(content), overwrite=True)
    else:
        audio_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    out = AudioUploadOut(
        call_id=call_id,
        filename=safe_name,
        bytes_received=len(content),
        message="Audio uploaded and stored for demo processing.",
        storage_path=str(path),
    )
    STATE.uploads[call_id] = out
    _append_audit("call_audio_metadata", out.model_dump())
    return out


def retrieve_knowledge(query: str, limit: int = 3, config=None) -> list[Citation]:
    if config and not config.vector_search_index_name.startswith("mock-"):
        citations = _retrieve_vector_search_knowledge(query, limit, config)
        if citations:
            return citations
    return _retrieve_local_knowledge(query, limit)


def _retrieve_local_knowledge(query: str, limit: int = 3) -> list[Citation]:
    tokens = {t.lower().strip(".,!?") for t in query.split() if len(t) > 3}
    scored: list[tuple[int, KnowledgeDocument]] = []
    for doc in KNOWLEDGE_BASE:
        haystack = " ".join([doc.title, doc.section, doc.content, *doc.tags]).lower()
        score = sum(1 for token in tokens if token in haystack)
        if score:
            scored.append((score, doc))
    if not scored:
        scored = [(1, KNOWLEDGE_BASE[-1])]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        Citation(
            document_id=doc.document_id,
            title=doc.title,
            section=doc.section,
            quote=doc.content,
            score=min(0.99, 0.65 + (score * 0.08)),
        )
        for score, doc in scored[:limit]
    ]


def _retrieve_vector_search_knowledge(query: str, limit: int, config) -> list[Citation]:
    try:
        ws = WorkspaceClient()
        try:
            response = ws.vector_search_indexes.query_index(
                index_name=config.vector_search_index_name,
                columns=["chunk_id", "source_document", "content"],
                query_text=query,
                num_results=limit,
            )
        except Exception as query_text_error:
            logger.warning(
                "Vector Search query_text failed for index=%s: %s; trying query_vector",
                config.vector_search_index_name,
                query_text_error,
            )
            embedding = _query_embedding_endpoint(ws, config.embedding_endpoint_name, query)
            if not embedding:
                return []
            response = ws.vector_search_indexes.query_index(
                index_name=config.vector_search_index_name,
                columns=["chunk_id", "source_document", "content"],
                query_vector=embedding,
                num_results=limit,
            )
        citations = _vector_search_response_to_citations(response)
        logger.info(
            "Vector Search returned %s citation(s) for index=%s",
            len(citations),
            config.vector_search_index_name,
        )
        return citations
    except Exception as error:
        logger.warning(
            "Vector Search query failed for endpoint=%s index=%s: %s",
            config.vector_search_endpoint_name,
            config.vector_search_index_name,
            error,
        )
        return []


def _query_embedding_endpoint(ws: WorkspaceClient, endpoint_name: str, text: str) -> list[float] | None:
    try:
        try:
            response = ws.serving_endpoints.query(name=endpoint_name, input=text)
        except TypeError:
            response = ws.serving_endpoints.query(name=endpoint_name, inputs={"input": text})
        return _extract_embedding(response)
    except Exception as error:
        logger.warning("Embedding endpoint %s query failed: %s", endpoint_name, error)
        return None


def _extract_embedding(response: object | None) -> list[float] | None:
    if response is None:
        return None
    if not isinstance(response, dict):
        as_dict = getattr(response, "as_dict", None)
        if callable(as_dict):
            return _extract_embedding(as_dict())
        data = getattr(response, "data", None)
        if data is not None:
            return _extract_embedding({"data": data})
        return None
    candidates = [
        response.get("embedding"),
        response.get("data", [{}])[0].get("embedding") if response.get("data") else None,
        response.get("predictions", [{}])[0].get("embedding") if response.get("predictions") else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, list) and candidate and all(isinstance(value, int | float) for value in candidate):
            return [float(value) for value in candidate]
    return None


def _vector_search_response_to_citations(response: object | None) -> list[Citation]:
    if response is None:
        return []
    if not isinstance(response, dict):
        as_dict = getattr(response, "as_dict", None)
        if callable(as_dict):
            response = as_dict()
        else:
            return []

    columns = [column.get("name") for column in response.get("manifest", {}).get("columns", [])]
    rows = response.get("result", {}).get("data_array", [])
    citations: list[Citation] = []
    for index, row in enumerate(rows):
        values = dict(zip(columns, row, strict=False))
        source_document = str(values.get("source_document") or "")
        content = str(values.get("content") or "").strip()
        if not content:
            continue
        document_id = str(values.get("chunk_id") or f"vector-row-{index + 1}")
        source_name = Path(source_document).name or source_document or "Vector Search knowledge"
        title = source_name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
        citations.append(
            Citation(
                document_id=f"vs_{document_id}",
                title=title,
                section=source_document or "Vector Search result",
                quote=content,
                score=_coerce_float(values.get("score"), 0.8),
            )
        )
    return citations


def _coerce_float(value: object, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def run_rules(text: str) -> list[Alert]:
    normalized = text.lower()
    alerts: list[Alert] = []
    if any(term in normalized for term in ["chest", "short of breath", "breathing", "fainting"]):
        alerts.append(
            Alert(
                code="urgent_symptom",
                title="Urgent symptom language",
                detail="Patient mentioned chest symptoms, breathing trouble, fainting, or worsening symptoms.",
                risk_level=RiskLevel.HIGH,
            )
        )
    if any(term in normalized for term in ["stopping it", "stop taking", "side effects", "dizzy"]):
        alerts.append(
            Alert(
                code="medication_adherence",
                title="Medication adherence risk",
                detail="Patient may stop medication or has possible adverse effects.",
                risk_level=RiskLevel.MEDIUM,
            )
        )
    if any(term in normalized for term in ["done with", "cancel", "not worth", "missing work"]):
        alerts.append(
            Alert(
                code="retention_risk",
                title="Patient retention risk",
                detail="Patient may disengage from care without immediate barrier resolution.",
                risk_level=RiskLevel.MEDIUM,
            )
        )
    alerts.append(
        Alert(
            code="identity_privacy",
            title="HIPAA reminder",
            detail="Verify identity before discussing protected health details.",
            risk_level=RiskLevel.LOW,
        )
    )
    return alerts


def analyze_call(payload: AnalyzeIn, config=None) -> Recommendation:
    started = time.perf_counter()
    call = get_call(payload.call_id)
    segments = transcript_for_call(call.call_id)
    transcript_window = payload.transcript_window or _format_transcript_window(segments)
    trigger = payload.trigger_segment_id or (segments[-1].segment_id if segments else None)
    citations = retrieve_knowledge(transcript_window, config=config)
    alerts = run_rules(transcript_window)
    scenario = _scenario_by_id(call.scenario_id)
    risk_level = max([scenario.expected_risk_level, *[a.risk_level for a in alerts]], key=_risk_weight)
    response, action, rationale = _recommendation_copy(call.scenario_id, risk_level)
    served_json = None
    llm_source = "deterministic"
    if config is not None and not config.use_mock_llm:
        served_json = _query_reasoning_endpoint(
            config.llm_endpoint_name,
            call=call,
            transcript_window=transcript_window,
            citations=citations,
            alerts=alerts,
        )
        if isinstance(served_json, dict):
            llm_source = "databricks_llm"
            response = str(served_json.get("recommended_response") or response)
            action = str(served_json.get("next_best_action") or action)
            rationale = str(served_json.get("action_rationale") or rationale)
            risk_level = _risk_from_text(str(served_json.get("risk_level") or risk_level.value), risk_level)
            citations = _coerce_citations(served_json.get("citations"), citations)
            alerts = _coerce_alerts(served_json.get("alerts"), alerts)
        else:
            llm_source = "deterministic_fallback"
    rec = Recommendation(
        call_id=call.call_id,
        trigger_segment_id=trigger,
        intent=_text_field(served_json, "intent", scenario.intent),
        topic=_text_field(served_json, "topic", scenario.title),
        patient_state=_text_field(served_json, "patient_state", _patient_state(call.scenario_id, transcript_window)),
        risk_level=risk_level,
        urgency_level=_risk_from_text(str(served_json.get("urgency_level") or risk_level.value), risk_level)
        if isinstance(served_json, dict)
        else risk_level,
        recommended_response=response,
        next_best_action=action,
        action_rationale=rationale,
        confidence=_coerce_confidence(served_json.get("confidence")) if isinstance(served_json, dict) else 0.88
        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        else 0.81,
        citations=citations,
        alerts=alerts,
        compliance_notes=["Verify patient identity before discussing PHI.", "Recommendation only; do not execute external actions in V1."],
        summary_update=_text_field(served_json, "summary_update", _summary_for(call.call_id)),
        structured_slots={
            "scenario": call.scenario_id,
            "patient_name": call.patient_name,
            "cadence_mode": call.settings.cadence_mode,
            "model_source": llm_source,
            "llm_endpoint": getattr(config, "llm_endpoint_name", None),
            "embedding_endpoint": getattr(config, "embedding_endpoint_name", None),
            "vector_search_endpoint": getattr(config, "vector_search_endpoint_name", None),
            "vector_search_index": getattr(config, "vector_search_index_name", None),
            "retrieved_citation_count": len(citations),
            "served_payload": served_json,
        },
        should_escalate=_coerce_bool(served_json.get("should_escalate"))
        if isinstance(served_json, dict) and served_json.get("should_escalate") is not None
        else risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL},
        escalation_reason=str(served_json.get("escalation_reason") or "")
        if isinstance(served_json, dict) and served_json.get("escalation_reason")
        else "High-risk symptom or clinical concern detected."
        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        else None,
        llm_latency_ms=int((time.perf_counter() - started) * 1000) + 250,
    )
    STATE.recommendations[call.call_id].append(rec)
    call.current_recommendation_id = rec.recommendation_id
    call.current_risk_level = rec.risk_level
    call.latest_intent = rec.intent
    call.scenario_title = rec.topic
    extracted_name = _text_field(served_json, "patient_name", "").strip()
    if extracted_name:
        call.patient_name = extracted_name
    call.summary_draft = rec.summary_update
    _append_audit("recommendation_events", rec.model_dump())
    _append_audit(
        "model_audit_events",
        {
            "call_id": call.call_id,
            "endpoint": getattr(config, "llm_endpoint_name", "mock-or-configured-gpt-5.5"),
            "model_source": llm_source,
            "input_window": transcript_window,
            "response": rec.model_dump(),
        },
    )
    return rec


def store_feedback(recommendation_id: str, payload: FeedbackIn) -> AgentFeedback:
    for recs in STATE.recommendations.values():
        for rec in recs:
            if rec.recommendation_id == recommendation_id:
                feedback = AgentFeedback(
                    recommendation_id=recommendation_id,
                    call_id=rec.call_id,
                    feedback_type=payload.feedback_type,
                    free_text=payload.free_text,
                )
                STATE.feedback.append(feedback)
                _append_audit("feedback_events", feedback.model_dump())
                return feedback
    raise KeyError(f"Unknown recommendation_id {recommendation_id}")


def demo_metrics() -> DemoMetrics:
    all_segments = [s for segments in STATE.transcripts.values() for s in segments]
    all_recs = [r for recs in STATE.recommendations.values() for r in recs]
    return DemoMetrics(
        active_calls=len(active_calls()),
        total_calls=len(STATE.calls),
        transcript_segments=len(all_segments),
        recommendations=len(all_recs),
        feedback_items=len(STATE.feedback),
        avg_asr_latency_ms=_avg(s.asr_latency_ms for s in all_segments),
        avg_llm_latency_ms=_avg(r.llm_latency_ms for r in all_recs),
    )


def app_config_out(config) -> AppConfigOut:
    return AppConfigOut(
        app_name=config.app_name,
        llm_endpoint_name=config.llm_endpoint_name,
        asr_endpoint_name=config.asr_endpoint_name,
        vector_search_endpoint_name=config.vector_search_endpoint_name,
        vector_search_index_name=config.vector_search_index_name,
        uc_catalog=config.uc_catalog,
        uc_schema=config.uc_schema,
        delta_schema_name=config.delta_schema_name,
        use_databricks_asr=config.use_databricks_asr,
        use_mock_asr=config.use_mock_asr,
        use_mock_llm=config.use_mock_llm,
        use_scripted_transcript_fallback=config.use_scripted_transcript_fallback,
        enable_redaction=config.enable_redaction,
        enable_acoustic_features=config.enable_acoustic_features,
    )


def replay_events(call_id: str) -> list[dict]:
    get_call(call_id)
    events: list[dict] = []
    for segment in STATE.transcripts[call_id]:
        events.append({"type": "transcript", "payload": segment.model_dump()})
    for rec in STATE.recommendations[call_id]:
        events.append({"type": "recommendation", "payload": rec.model_dump()})
    return events


def _risk_weight(level: RiskLevel) -> int:
    return {
        RiskLevel.LOW: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.HIGH: 3,
        RiskLevel.CRITICAL: 4,
    }[level]


def _avg(values: Iterable[int]) -> float:
    collected = list(values)
    return round(sum(collected) / len(collected), 1) if collected else 0.0


def _summary_for(call_id: str) -> str:
    call = get_call(call_id)
    segments = STATE.transcripts.get(call_id, [])
    if not segments:
        return f"{call.scenario_title} call started for {call.patient_name}."
    latest = segments[-1].text
    return f"{call.patient_name} is in a {call.scenario_title.lower()} scenario. Latest: {latest}"


def _format_transcript_window(segments: list[TranscriptSegment], max_segments: int = 12) -> str:
    recent = segments[-max_segments:]
    return "\n".join(f"{segment.speaker.value}: {segment.text}" for segment in recent)


def _patient_state(scenario_id: str, transcript_window: str) -> str:
    if scenario_id == "symptom_escalation":
        return "anxious and potentially clinically urgent"
    if scenario_id == "billing_confusion":
        return "frustrated and at risk of disengaging"
    if scenario_id == "appointment_retention":
        return "overwhelmed by scheduling barriers"
    if scenario_id == "medication_concern":
        return "concerned about medication safety"
    if "confusing" in transcript_window.lower():
        return "confused and needs clear next steps"
    return "needs guidance"


def _recommendation_copy(scenario_id: str, risk_level: RiskLevel) -> tuple[str, str, str]:
    if scenario_id == "symptom_escalation":
        return (
            "Because you mentioned chest tightness and shortness of breath, I want to get you clinical help immediately.",
            "Escalate to nurse triage now and advise emergency services if symptoms are severe or worsening.",
            "Chest tightness and shortness of breath are high-risk symptoms in the triage policy.",
        )
    if scenario_id == "medication_concern":
        return (
            "I am sorry you are feeling dizzy. Please do not stop the medication until a clinician reviews this with you.",
            "Offer nurse or pharmacist escalation and ask about severe symptoms.",
            "Medication discontinuation and side effects require clinical guidance.",
        )
    if scenario_id == "billing_confusion":
        return (
            "I hear how frustrating this bill is. Let me help route the billing review while we keep your care plan moving.",
            "Create a billing review handoff and restate the next care step.",
            "De-escalating billing frustration protects care continuity.",
        )
    if scenario_id == "appointment_retention":
        return (
            "I understand work makes this hard. Let us find a time that protects your follow-up and fits your schedule.",
            "Ask for acceptable time windows and offer an alternate appointment.",
            "Barrier discovery plus a concrete alternative reduces cancellation risk.",
        )
    return (
        "Let us walk through the next step together so you know exactly who to call and what to watch for.",
        "Confirm follow-up appointment, medication questions, warning signs, and contact path.",
        "Post-discharge confusion improves with a clear care navigation checklist.",
    )


def _text_field(payload: dict | None, key: str, default: str) -> str:
    if not isinstance(payload, dict):
        return default
    value = payload.get(key)
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _risk_from_text(value: str, default: RiskLevel) -> RiskLevel:
    normalized = value.lower().strip()
    try:
        return RiskLevel(normalized)
    except ValueError:
        return default


def _coerce_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.82
    return max(0.0, min(1.0, confidence))


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "y"}
    return bool(value)


def _coerce_citations(value: object, fallback: list[Citation]) -> list[Citation]:
    if not isinstance(value, list):
        return fallback
    citations: list[Citation] = []
    for index, item in enumerate(value):
        if isinstance(item, Citation):
            citations.append(item)
        elif isinstance(item, dict):
            citations.append(
                Citation(
                    document_id=str(item.get("document_id") or item.get("id") or f"llm-citation-{index + 1}"),
                    title=str(item.get("title") or "LLM cited guidance"),
                    section=str(item.get("section") or "Recommendation context"),
                    quote=str(item.get("quote") or item.get("content") or item.get("text") or ""),
                    score=_coerce_confidence(item.get("score", 0.8)),
                )
            )
    return citations or fallback


def _coerce_alerts(value: object, fallback: list[Alert]) -> list[Alert]:
    if not isinstance(value, list):
        return fallback
    alerts: list[Alert] = []
    for index, item in enumerate(value):
        if isinstance(item, Alert):
            alerts.append(item)
        elif isinstance(item, dict):
            risk = _risk_from_text(str(item.get("risk_level") or RiskLevel.MEDIUM.value), RiskLevel.MEDIUM)
            alerts.append(
                Alert(
                    code=str(item.get("code") or f"llm_alert_{index + 1}"),
                    title=str(item.get("title") or "LLM alert"),
                    detail=str(item.get("detail") or item.get("description") or ""),
                    risk_level=risk,
                )
            )
    return alerts or fallback


def _query_serving_endpoint(endpoint_name: str, inputs: dict) -> object | None:
    try:
        ws = WorkspaceClient()
        try:
            return ws.serving_endpoints.query(name=endpoint_name, dataframe_records=[inputs])
        except TypeError:
            return ws.serving_endpoints.query(name=endpoint_name, inputs=inputs)
    except Exception as error:
        logger.warning("Serving endpoint %s query failed: %s", endpoint_name, error)
        return None


def _silent_wav_base64(duration_seconds: float = 0.5, sample_rate: int = 16000) -> str:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * int(sample_rate * duration_seconds))
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _query_reasoning_endpoint(
    endpoint_name: str,
    *,
    call: ActiveCall,
    transcript_window: str,
    citations: list[Citation],
    alerts: list[Alert],
) -> dict | None:
    prompt = {
        "call_id": call.call_id,
        "initial_demo_scenario": call.scenario_id,
        "known_patient_name": call.patient_name,
        "latest_transcript_window": transcript_window,
        "instructions": [
            "Infer the actual call scenario, topic, patient state, risk, and next best action from the transcript.",
            "Do not assume the initial demo scenario is correct if the transcript indicates a different issue.",
            "If the transcript contains the caller's name, return it as patient_name; otherwise return null.",
            "Use the speaker labels in the transcript to distinguish patient needs from agent responses.",
        ],
        "retrieved_citations": [citation.model_dump() for citation in citations],
        "deterministic_alerts": [alert.model_dump() for alert in alerts],
        "required_output_schema": {
            "patient_name": "string or null; only if stated in the transcript",
            "intent": "string",
            "topic": "string",
            "patient_state": "string",
            "risk_level": "one of: low, medium, high, critical",
            "urgency_level": "one of: low, medium, high, critical",
            "recommended_response": "string; words the human agent can say now",
            "next_best_action": "string; concrete operational next step",
            "action_rationale": "string",
            "confidence": "number between 0 and 1",
            "citations": "array of {document_id,title,section,quote,score}",
            "alerts": "array of {code,title,detail,risk_level}",
            "summary_update": "string",
            "should_escalate": "boolean",
            "escalation_reason": "string or null",
        },
    }
    try:
        ws = WorkspaceClient()
        response = ws.serving_endpoints.query(
            name=endpoint_name,
            messages=[
                _ServingChatMessage(
                    role="system",
                    content=(
                        "You are a healthcare call-center next-best-action assistant. "
                        "Return one valid JSON object only, with no markdown, no prose outside JSON, "
                        "and values that match the required schema."
                    ),
                ),
                _ServingChatMessage(role="user", content=json.dumps(prompt, default=str)),
            ],
            max_tokens=900,
        )
        text = _extract_served_text(response)
        if not text:
            return None
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
    except Exception as error:
        logger.warning("Reasoning endpoint %s query failed: %s", endpoint_name, error)
        return None
    return None


def _new_overlap_asr_text(call_id: str, served_text: str) -> str:
    current = served_text.strip()
    if not current:
        return ""
    previous = STATE.transcripts.get(call_id) or []
    if not previous:
        return current
    last_window = " ".join(segment.text.strip() for segment in previous[-4:] if segment.text).strip()
    if not last_window:
        return current
    delta = _transcript_delta(last_window, current)
    last = previous[-1].text.strip().lower()
    if not delta or delta.strip().lower() == last or delta.strip().lower() in last:
        return ""
    return delta


def _extract_served_confidence(response: object | None) -> float | None:
    if response is None:
        return None
    if not isinstance(response, dict):
        as_dict = getattr(response, "as_dict", None)
        if callable(as_dict):
            return _extract_served_confidence(as_dict())
        return None
    predictions = response.get("predictions")
    if isinstance(predictions, list) and predictions and isinstance(predictions[0], dict):
        value = predictions[0].get("confidence")
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _clean_asr_text(text: str) -> str:
    cleaned = re.sub(r"(?:\s*//)+\s*$", "", text).strip()
    cleaned = re.sub(
        r"(?i)^(?:a healthcare call center conversation between a patient and an agent[.\s,]*)+",
        "",
        cleaned,
    ).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _extract_served_error(response: object | None) -> str | None:
    if response is None:
        return None
    if not isinstance(response, dict):
        as_dict = getattr(response, "as_dict", None)
        if callable(as_dict):
            return _extract_served_error(as_dict())
        return None
    predictions = response.get("predictions")
    if isinstance(predictions, list) and predictions and isinstance(predictions[0], dict):
        error = predictions[0].get("error")
        if error:
            return str(error)
    error = response.get("error")
    return str(error) if error else None


def _extract_served_text(response: object | None) -> str | None:
    if response is None:
        return None
    if isinstance(response, dict):
        candidates = [
            response.get("text"),
            response.get("transcript"),
            response.get("content"),
            response.get("message"),
            response.get("choices"),
            response.get("predictions", [None])[0] if response.get("predictions") else None,
        ]
    else:
        as_dict = getattr(response, "as_dict", None)
        if callable(as_dict):
            return _extract_served_text(as_dict())
        candidates = [
            getattr(response, "text", None),
            getattr(response, "transcript", None),
            getattr(response, "content", None),
            getattr(response, "predictions", None),
        ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate
        if isinstance(candidate, dict):
            nested = _extract_served_text(candidate)
            if nested:
                return nested
        if isinstance(candidate, list):
            for item in candidate:
                nested = _extract_served_text(item)
                if nested:
                    return nested
    return None
