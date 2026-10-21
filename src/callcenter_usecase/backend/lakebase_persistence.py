from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime
from enum import Enum

from sqlalchemy import Engine
from sqlmodel import Session

from .core import logger
from .models import (
    ActiveCall,
    ActiveCallTable,
    AudioArtifactTable,
    AudioUploadOut,
    CallSummaryWindowTable,
    NextBestActionTable,
    Recommendation,
    RecommendationAlertTable,
    RecommendationCitationTable,
    TranscriptSegment,
    TranscriptSegmentTable,
)


def persist_final_call_snapshot(
    engine: Engine | None,
    *,
    call: ActiveCall,
    transcript_segments: list[TranscriptSegment],
    recommendations: list[Recommendation],
) -> bool:
    """Persist all UI-visible call artifacts to Lakebase when a call stops."""
    if engine is None:
        logger.warning("Lakebase is not configured; skipped final snapshot for call_id=%s", call.call_id)
        return False

    with Session(engine) as session:
        session.merge(_call_row(call))
        for segment in transcript_segments:
            session.merge(_segment_row(segment))
        for summary in _summary_rows(call, transcript_segments):
            session.merge(summary)
        for recommendation in recommendations:
            session.merge(_next_best_action_row(recommendation))
            for index, alert in enumerate(recommendation.alerts):
                session.merge(
                    RecommendationAlertTable(
                        alert_row_id=f"alert_{recommendation.recommendation_id}_{index}",
                        recommendation_id=recommendation.recommendation_id,
                        call_id=recommendation.call_id,
                        alert_index=index,
                        code=alert.code,
                        title=alert.title,
                        detail=alert.detail,
                        risk_level=_value(alert.risk_level),
                        created_at=recommendation.created_at,
                    )
                )
            for index, citation in enumerate(recommendation.citations):
                session.merge(
                    RecommendationCitationTable(
                        citation_row_id=f"cite_{recommendation.recommendation_id}_{index}",
                        recommendation_id=recommendation.recommendation_id,
                        call_id=recommendation.call_id,
                        citation_index=index,
                        document_id=citation.document_id,
                        title=citation.title,
                        section=citation.section,
                        quote=citation.quote,
                        score=citation.score,
                        created_at=recommendation.created_at,
                    )
                )
        session.commit()
    logger.info(
        "Persisted final Lakebase snapshot call_id=%s transcript=%s recommendations=%s",
        call.call_id,
        len(transcript_segments),
        len(recommendations),
    )
    return True


def persist_audio_artifact(engine: Engine | None, upload: AudioUploadOut) -> bool:
    """Persist the UC Volume audio artifact metadata independently of call snapshot writes."""
    if engine is None:
        logger.warning("Lakebase is not configured; skipped audio artifact for call_id=%s", upload.call_id)
        return False
    digest = hashlib.sha1(f"{upload.call_id}:{upload.filename}:{upload.storage_path}".encode("utf-8")).hexdigest()[:12]
    with Session(engine) as session:
        session.merge(
            AudioArtifactTable(
                audio_artifact_id=f"audio_{digest}",
                call_id=upload.call_id,
                filename=upload.filename,
                storage_path=upload.storage_path,
                bytes_received=upload.bytes_received,
            )
        )
        session.commit()
    logger.info("Persisted audio artifact metadata call_id=%s filename=%s", upload.call_id, upload.filename)
    return True


def _summary_rows(call: ActiveCall, segments: list[TranscriptSegment]) -> list[CallSummaryWindowTable]:
    grouped: dict[int, list[TranscriptSegment]] = defaultdict(list)
    for index, segment in enumerate(segments):
        window_index = _window_index(segment, index)
        grouped[window_index].append(segment)

    rows: list[CallSummaryWindowTable] = []
    for window_index in sorted(grouped):
        window_segments = grouped[window_index]
        rows.append(
            CallSummaryWindowTable(
                summary_id=f"summary_{call.call_id}_{window_index}",
                call_id=call.call_id,
                window_index=window_index,
                start_seconds=window_index * 15,
                end_seconds=(window_index + 1) * 15,
                summary_text=_summarize_segments(window_segments),
                created_at=call.ended_at or _latest_created_at(window_segments),
            )
        )
    return rows


def _window_index(segment: TranscriptSegment, fallback_index: int) -> int:
    if segment.start_ms > 0:
        return max(0, int(segment.start_ms / 1000) // 15)
    return fallback_index // 2


def _summarize_segments(segments: list[TranscriptSegment]) -> str:
    by_speaker: dict[str, list[str]] = defaultdict(list)
    for segment in segments:
        by_speaker[_value(segment.speaker)].append(segment.text)
    return " ".join(f"{speaker}: {' '.join(texts)}" for speaker, texts in by_speaker.items())


def _latest_created_at(segments: list[TranscriptSegment]) -> datetime:
    return max((segment.created_at for segment in segments), default=datetime.utcnow())


def _call_row(call: ActiveCall) -> ActiveCallTable:
    return ActiveCallTable(
        call_id=call.call_id,
        status=_value(call.status),
        scenario_id=call.scenario_id,
        scenario_title=call.scenario_title,
        patient_name=call.patient_name,
        latest_transcript=call.latest_transcript,
        latest_intent=call.latest_intent,
        current_risk_level=_value(call.current_risk_level),
        current_recommendation_id=call.current_recommendation_id,
        started_at=call.started_at,
        ended_at=call.ended_at,
    )


def _segment_row(segment: TranscriptSegment) -> TranscriptSegmentTable:
    return TranscriptSegmentTable(
        segment_id=segment.segment_id,
        call_id=segment.call_id,
        speaker=_value(segment.speaker),
        text=segment.text,
        is_partial=segment.is_partial,
        start_ms=segment.start_ms,
        end_ms=segment.end_ms,
        asr_latency_ms=segment.asr_latency_ms,
        confidence=segment.confidence,
        created_at=segment.created_at,
    )


def _next_best_action_row(rec: Recommendation) -> NextBestActionTable:
    return NextBestActionTable(
        action_id=f"nba_{rec.recommendation_id}",
        recommendation_id=rec.recommendation_id,
        call_id=rec.call_id,
        trigger_segment_id=rec.trigger_segment_id,
        intent=rec.intent,
        topic=rec.topic,
        patient_state=rec.patient_state,
        risk_level=_value(rec.risk_level),
        urgency_level=_value(rec.urgency_level),
        recommended_response=rec.recommended_response,
        next_best_action=rec.next_best_action,
        action_rationale=rec.action_rationale,
        confidence=rec.confidence,
        should_escalate=rec.should_escalate,
        escalation_reason=rec.escalation_reason,
        llm_latency_ms=rec.llm_latency_ms,
        created_at=rec.created_at,
    )


def _value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)
