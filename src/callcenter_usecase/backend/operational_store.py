from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
from enum import Enum

from databricks.sdk import WorkspaceClient
from sqlalchemy import Engine
from sqlmodel import Session, select

from .core import logger
from .lakebase_persistence import (
    persist_audio_artifact,
    persist_final_call_snapshot,
)
from .models import (
    ActiveCall,
    ActiveCallTable,
    AgentFeedback,
    AudioUploadOut,
    CallClosureTable,
    CallStatus,
    FeedbackTable,
    FeedbackType,
    NextBestActionTable,
    Recommendation,
    RecommendationAlertTable,
    RecommendationCitationTable,
    TranscriptSegment,
    TranscriptSegmentTable,
    utc_now,
)
from .toyota_catalog import DEMO_SCENARIOS, scenario_by_id
from . import uc_persistence

_PERSIST_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="toyota-persist")


def persist_call(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    call: ActiveCall,
    disposition: str | None = None,
) -> None:
    scenario = scenario_by_id(call.scenario_id)
    values = {
        "call_id": call.call_id,
        "status": _value(call.status),
        "scenario_id": call.scenario_id,
        "scenario_title": call.scenario_title,
        "family": scenario.family,
        "queue": scenario.queue,
        "vehicle": scenario.vehicle,
        "location": scenario.location,
        "coverage": scenario.coverage,
        "patient_name": call.patient_name,
        "latest_transcript": call.latest_transcript,
        "latest_intent": call.latest_intent,
        "current_risk_level": _value(call.current_risk_level),
        "current_recommendation_id": call.current_recommendation_id,
        "disposition": disposition,
        "started_at": call.started_at,
        "ended_at": call.ended_at,
    }
    _safe_persist("call", call.call_id, engine, ActiveCallTable(**values), ws, config, "calls", "call_id", values)


def persist_segment(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    segment: TranscriptSegment,
) -> None:
    values = {
        "segment_id": segment.segment_id,
        "call_id": segment.call_id,
        "speaker": _value(segment.speaker),
        "text": segment.text,
        "is_partial": segment.is_partial,
        "start_ms": segment.start_ms,
        "end_ms": segment.end_ms,
        "asr_latency_ms": segment.asr_latency_ms,
        "confidence": segment.confidence,
        "created_at": segment.created_at,
    }
    _safe_persist(
        "segment",
        segment.segment_id,
        engine,
        TranscriptSegmentTable(**values),
        ws,
        config,
        "transcript_segments",
        "segment_id",
        values,
    )


def persist_recommendation(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    recommendation: Recommendation,
) -> None:
    nba_values = {
        "action_id": f"nba_{recommendation.recommendation_id}",
        "recommendation_id": recommendation.recommendation_id,
        "call_id": recommendation.call_id,
        "trigger_segment_id": recommendation.trigger_segment_id,
        "intent": recommendation.intent,
        "topic": recommendation.topic,
        "patient_state": recommendation.patient_state,
        "risk_level": _value(recommendation.risk_level),
        "urgency_level": _value(recommendation.urgency_level),
        "recommended_response": recommendation.recommended_response,
        "next_best_action": recommendation.next_best_action,
        "action_rationale": recommendation.action_rationale,
        "confidence": recommendation.confidence,
        "should_escalate": recommendation.should_escalate,
        "escalation_reason": recommendation.escalation_reason,
        "llm_latency_ms": recommendation.llm_latency_ms,
        "created_at": recommendation.created_at,
    }
    _safe_persist(
        "recommendation",
        recommendation.recommendation_id,
        engine,
        NextBestActionTable(**nba_values),
        ws,
        config,
        "next_best_actions",
        "recommendation_id",
        {key: value for key, value in nba_values.items() if key != "action_id"},
    )
    for index, alert in enumerate(recommendation.alerts):
        alert_values = {
            "alert_row_id": f"alert_{recommendation.recommendation_id}_{index}",
            "recommendation_id": recommendation.recommendation_id,
            "call_id": recommendation.call_id,
            "alert_index": index,
            "code": alert.code,
            "title": alert.title,
            "detail": alert.detail,
            "risk_level": _value(alert.risk_level),
            "created_at": recommendation.created_at,
        }
        _safe_persist(
            "alert",
            alert_values["alert_row_id"],
            engine,
            RecommendationAlertTable(**alert_values),
            ws,
            config,
            "recommendation_alerts",
            "alert_row_id",
            alert_values,
        )
    for index, citation in enumerate(recommendation.citations):
        citation_values = {
            "citation_row_id": f"cite_{recommendation.recommendation_id}_{index}",
            "recommendation_id": recommendation.recommendation_id,
            "call_id": recommendation.call_id,
            "citation_index": index,
            "document_id": citation.document_id,
            "title": citation.title,
            "section": citation.section,
            "quote": citation.quote,
            "score": citation.score,
            "created_at": recommendation.created_at,
        }
        _safe_persist(
            "citation",
            citation_values["citation_row_id"],
            engine,
            RecommendationCitationTable(**citation_values),
            ws,
            config,
            "recommendation_citations",
            "citation_row_id",
            citation_values,
        )


def persist_feedback(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    feedback: AgentFeedback,
) -> None:
    values = {
        "feedback_id": feedback.feedback_id,
        "recommendation_id": feedback.recommendation_id,
        "call_id": feedback.call_id,
        "feedback_type": _value(feedback.feedback_type),
        "free_text": feedback.free_text,
        "created_by": feedback.created_by,
        "created_at": feedback.created_at,
    }
    _safe_persist(
        "feedback",
        feedback.feedback_id,
        engine,
        FeedbackTable(**values),
        ws,
        config,
        "agent_feedback",
        "feedback_id",
        values,
    )


def persist_closure(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    call: ActiveCall,
    transcript_segments: list[TranscriptSegment],
    recommendations: list[Recommendation],
) -> None:
    scenario = scenario_by_id(call.scenario_id)
    latest = recommendations[-1] if recommendations else None
    disposition = _disposition(call, latest)
    values = {
        "call_id": call.call_id,
        "disposition": disposition,
        "family": scenario.family,
        "queue": scenario.queue,
        "intent": (latest.intent if latest else call.latest_intent),
        "risk_level": _value(latest.risk_level if latest else call.current_risk_level),
        "should_escalate": bool(latest.should_escalate) if latest else False,
        "transcript_count": len(transcript_segments),
        "recommendation_count": len(recommendations),
        "resolution_summary": (latest.next_best_action if latest else call.summary_draft) or "",
        "closed_by": "demo-agent",
        "closed_at": call.ended_at or utc_now(),
    }
    _safe_persist(
        "closure",
        call.call_id,
        engine,
        CallClosureTable(**values),
        ws,
        config,
        "call_closures",
        "call_id",
        values,
    )
    persist_call(engine, ws, config, call, disposition=disposition)


def persist_stopped_call(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    call: ActiveCall,
    transcript_segments: list[TranscriptSegment],
    recommendations: list[Recommendation],
) -> None:
    try:
        persist_final_call_snapshot(
            engine,
            call=call,
            transcript_segments=transcript_segments,
            recommendations=recommendations,
        )
        persist_closure(engine, ws, config, call, transcript_segments, recommendations)
        for segment in transcript_segments:
            persist_segment(engine, ws, config, segment)
        for recommendation in recommendations:
            persist_recommendation(engine, ws, config, recommendation)
    except Exception:
        logger.exception("Failed to persist stopped call %s", call.call_id)


def persist_upload(engine: Engine | None, upload: AudioUploadOut) -> None:
    persist_audio_artifact(engine, upload)


def enqueue_persist_call(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    call: ActiveCall,
    disposition: str | None = None,
) -> None:
    _submit("call", call.call_id, persist_call, engine, ws, config, _snapshot(call), disposition)


def enqueue_persist_segment(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    segment: TranscriptSegment,
) -> None:
    _submit("segment", segment.segment_id, persist_segment, engine, ws, config, _snapshot(segment))


def enqueue_persist_recommendation(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    recommendation: Recommendation,
) -> None:
    _submit(
        "recommendation",
        recommendation.recommendation_id,
        persist_recommendation,
        engine,
        ws,
        config,
        _snapshot(recommendation),
    )


def enqueue_persist_feedback(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    feedback: AgentFeedback,
) -> None:
    _submit("feedback", feedback.feedback_id, persist_feedback, engine, ws, config, _snapshot(feedback))


def enqueue_persist_stopped_call(
    engine: Engine | None,
    ws: WorkspaceClient | None,
    config,
    call: ActiveCall,
    transcript_segments: list[TranscriptSegment],
    recommendations: list[Recommendation],
) -> None:
    _submit(
        "stopped_call",
        call.call_id,
        persist_stopped_call,
        engine,
        ws,
        config,
        _snapshot(call),
        [_snapshot(segment) for segment in transcript_segments],
        [_snapshot(recommendation) for recommendation in recommendations],
    )


def enqueue_persist_upload(engine: Engine | None, upload: AudioUploadOut) -> None:
    _submit("upload", upload.call_id, persist_upload, engine, _snapshot(upload))


def seed_demo_history_if_empty(engine: Engine | None, ws: WorkspaceClient | None, config) -> int:
    if engine is None:
        return 0
    with Session(engine) as session:
        existing = session.exec(select(ActiveCallTable).limit(1)).first()
        if existing:
            logger.info("Lakebase already has call rows; skipping demo seed")
            return 0
    seeded = 0
    for index, demo in enumerate(DEMO_SCENARIOS):
        started = utc_now() - timedelta(days=6, hours=-(index * 5))
        ended = started + timedelta(minutes=8)
        call = ActiveCall(
            call_id=f"seed_{demo.id}",
            status=CallStatus.ENDED,
            scenario_id=demo.id,
            scenario_title=demo.title,
            patient_name=demo.patient_name,
            latest_intent=demo.intent,
            current_risk_level=demo.risk,
            latest_transcript=demo.segments[-1][1],
            summary_draft=demo.description,
            started_at=started,
            ended_at=ended,
        )
        persist_call(engine, ws, config, call)
        segments: list[TranscriptSegment] = []
        for seg_index, (speaker, text) in enumerate(demo.segments):
            segment = TranscriptSegment(
                segment_id=f"seed_{demo.id}_seg_{seg_index}",
                call_id=call.call_id,
                speaker=speaker,
                text=text,
                start_ms=seg_index * 8000,
                end_ms=(seg_index + 1) * 8000,
                asr_latency_ms=1400,
                confidence=0.91,
                created_at=started + timedelta(seconds=seg_index * 8),
            )
            persist_segment(engine, ws, config, segment)
            segments.append(segment)
        recommendation = Recommendation(
            recommendation_id=f"seed_{demo.id}_nba",
            call_id=call.call_id,
            trigger_segment_id=segments[-1].segment_id if segments else None,
            intent=demo.intent,
            topic=demo.title,
            patient_state=demo.caller_state,
            risk_level=demo.risk,
            urgency_level=demo.risk,
            recommended_response=demo.recommended_response,
            next_best_action=demo.next_best_action,
            action_rationale=demo.action_rationale,
            confidence=0.9,
            should_escalate=demo.escalate,
            escalation_reason="Safety-critical owner-support path" if demo.escalate else None,
            summary_update=demo.description,
            created_at=ended - timedelta(minutes=1),
        )
        persist_recommendation(engine, ws, config, recommendation)
        feedback_type = FeedbackType.USED if index % 3 == 0 else FeedbackType.HELPFUL
        persist_feedback(
            engine,
            ws,
            config,
            AgentFeedback(
                feedback_id=f"seed_{demo.id}_fb",
                recommendation_id=recommendation.recommendation_id,
                call_id=call.call_id,
                feedback_type=feedback_type,
                free_text="Seeded agent quality label for analytics.",
                created_at=ended,
            ),
        )
        persist_closure(engine, ws, config, call, segments, [recommendation])
        seeded += 1
    logger.info("Seeded %s Toyota demo calls into Lakebase and Unity Catalog", seeded)
    return seeded


def _safe_persist(
    kind: str,
    key: object,
    engine: Engine | None,
    row,
    ws: WorkspaceClient | None,
    config,
    table: str,
    key_column: str,
    values: Mapping[str, object],
) -> None:
    try:
        _merge_lakebase(engine, row)
    except Exception:
        logger.exception("Failed to persist %s %s to Lakebase", kind, key)
    _enqueue_uc_persist(kind, key, ws, config, table, key_column, values)


def _enqueue_uc_persist(
    kind: str,
    key: object,
    ws: WorkspaceClient | None,
    config,
    table: str,
    key_column: str,
    values: Mapping[str, object],
) -> None:
    if ws is None:
        return
    try:
        future = _PERSIST_POOL.submit(
            _persist_uc,
            kind,
            key,
            ws,
            config,
            table,
            key_column,
            dict(values),
        )
    except Exception:
        logger.exception("Failed to enqueue UC persist %s %s", kind, key)
        return
    future.add_done_callback(lambda done: _log_future("uc", kind, key, done))


def _persist_uc(
    kind: str,
    key: object,
    ws: WorkspaceClient | None,
    config,
    table: str,
    key_column: str,
    values: dict[str, object],
) -> None:
    try:
        uc_persistence.persist_row(ws, config, table, key_column, values)
    except Exception:
        logger.exception("Failed to persist %s %s to Unity Catalog", kind, key)


def _submit(kind: str, key: object, fn: Callable[..., None], *args: object) -> None:
    try:
        future = _PERSIST_POOL.submit(fn, *args)
    except Exception:
        logger.exception("Failed to enqueue persist %s %s", kind, key)
        return
    future.add_done_callback(lambda done: _log_future("persist", kind, key, done))


def _log_future(stage: str, kind: str, key: object, done: Future[None]) -> None:
    error = done.exception()
    if error is not None:
        logger.exception("Async %s %s %s failed", stage, kind, key, exc_info=error)


def _snapshot(model):
    return model.model_copy(deep=True)


def _merge_lakebase(engine: Engine | None, row) -> None:
    if engine is None:
        logger.warning("Lakebase is not configured; skipped persist for %s", type(row).__name__)
        return
    with Session(engine) as session:
        session.merge(row)
        session.commit()


def _disposition(call: ActiveCall, recommendation: Recommendation | None) -> str:
    if recommendation and recommendation.should_escalate:
        return "escalated"
    haystack = " ".join(
        [
            call.latest_intent or "",
            recommendation.next_best_action if recommendation else "",
            recommendation.intent if recommendation else "",
        ]
    ).lower()
    if "transfer" in haystack:
        return "transferred"
    if _value(call.status) == "ended":
        return "resolved"
    return "open"


def _value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)
