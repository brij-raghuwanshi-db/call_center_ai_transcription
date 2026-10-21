from databricks.sdk.service.iam import User as UserOut
from fastapi import BackgroundTasks, File, HTTPException, Request, Response, UploadFile
from sqlmodel import Session

from .core import Dependencies, create_router, logger
from .models import (
    ActiveCall,
    AgentFeedback,
    AnalyzeIn,
    AppConfigOut,
    AudioChunkIn,
    AudioUploadOut,
    ActiveCallTable,
    DemoMetrics,
    EvaluationExample,
    FeedbackTable,
    FeedbackIn,
    KnowledgeDocument,
    Recommendation,
    RecommendationTable,
    Scenario,
    StartCallIn,
    StartCallOut,
    TranscriptSegmentTable,
    TranscriptSegment,
)
from .models import VersionOut
from . import services
from . import lakebase_persistence

router = create_router()


@router.get("/version", response_model=VersionOut, operation_id="version")
async def version():
    return VersionOut.from_metadata()


@router.get("/current-user", response_model=UserOut, operation_id="currentUser")
def me(user_ws: Dependencies.UserClient):
    return user_ws.current_user.me()


@router.get("/health", operation_id="health")
async def health():
    return {"status": "ok", "service": "callcenter_usecase"}


@router.get("/config", response_model=AppConfigOut, operation_id="getConfig")
async def get_config(config: Dependencies.Config):
    return services.app_config_out(config)


@router.get("/scenarios", response_model=list[Scenario], operation_id="listScenarios")
async def list_scenarios():
    return services.list_scenarios()


@router.get(
    "/knowledge-documents",
    response_model=list[KnowledgeDocument],
    operation_id="listKnowledgeDocuments",
)
async def list_knowledge_documents():
    return services.list_knowledge_documents()


@router.get(
    "/evaluation/examples",
    response_model=list[EvaluationExample],
    operation_id="listEvaluationExamples",
)
async def list_evaluation_examples():
    return services.list_evaluation_examples()


@router.post("/calls/start", response_model=StartCallOut, operation_id="startCall")
async def start_call(payload: StartCallIn, request: Request, config: Dependencies.Config, background_tasks: BackgroundTasks):
    result = services.start_call(payload)
    _persist_call(request, result.call)
    background_tasks.add_task(services.warm_asr_endpoint, config)
    return result


@router.post("/calls/{call_id}/stop", response_model=ActiveCall, operation_id="stopCall")
async def stop_call(call_id: str, request: Request, background_tasks: BackgroundTasks):
    try:
        call = services.stop_call(call_id)
        background_tasks.add_task(
            _persist_stopped_call,
            _engine(request),
            call,
            list(services.transcript_for_call(call.call_id)),
            list(services.recommendations_for_call(call.call_id)),
        )
        return call
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/calls/active", response_model=list[ActiveCall], operation_id="listActiveCalls")
async def list_active_calls():
    return services.active_calls()


@router.get("/calls/{call_id}", response_model=ActiveCall, operation_id="getCall")
async def get_call(call_id: str):
    try:
        return services.get_call(call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/calls/{call_id}/transcript",
    response_model=list[TranscriptSegment],
    operation_id="getTranscript",
)
async def get_transcript(call_id: str):
    try:
        return services.transcript_for_call(call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/audio/chunk",
    response_model=TranscriptSegment,
    operation_id="processAudioChunk",
)
async def process_audio_chunk(
    payload: AudioChunkIn,
    config: Dependencies.Config,
    request: Request,
    background_tasks: BackgroundTasks,
):
    try:
        segment = services.transcribe_chunk(payload, config=config)
        _persist_segment(request, segment)
        call = services.get_call(segment.call_id)
        _persist_call(request, call)
        if services.reserve_auto_recommendation(segment.call_id):
            background_tasks.add_task(
                services.run_reserved_recommendation,
                AnalyzeIn(call_id=segment.call_id, trigger_segment_id=segment.segment_id),
                config,
            )
        return segment
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError:
        return Response(status_code=204)


@router.post(
    "/audio/upload/{call_id}",
    response_model=AudioUploadOut,
    operation_id="uploadAudio",
)
async def upload_audio(call_id: str, request: Request, config: Dependencies.Config, file: UploadFile = File(...)):
    try:
        upload = await services.store_upload(call_id, file, config=config)
        lakebase_persistence.persist_audio_artifact(_engine(request), upload)
        return upload
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/recommendations/analyze",
    response_model=Recommendation,
    operation_id="analyzeCall",
)
async def analyze_call(payload: AnalyzeIn, config: Dependencies.Config, request: Request):
    try:
        rec = services.analyze_call(payload, config=config)
        _persist_recommendation(request, rec)
        _persist_call(request, services.get_call(rec.call_id))
        return rec
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/recommendations/latest/{call_id}",
    response_model=Recommendation | None,
    operation_id="latestRecommendation",
)
async def latest_recommendation(call_id: str):
    try:
        return services.latest_recommendation(call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/recommendations/{call_id}",
    response_model=list[Recommendation],
    operation_id="listRecommendations",
)
async def list_recommendations(call_id: str):
    try:
        return services.recommendations_for_call(call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/recommendations/{recommendation_id}/feedback",
    response_model=AgentFeedback,
    operation_id="submitFeedback",
)
async def submit_feedback(recommendation_id: str, payload: FeedbackIn, request: Request):
    try:
        feedback = services.store_feedback(recommendation_id, payload)
        _persist_feedback(request, feedback)
        return feedback
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/replay/{call_id}", operation_id="replayCall")
async def replay_call(call_id: str):
    try:
        return services.replay_events(call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/metrics/demo", response_model=DemoMetrics, operation_id="demoMetrics")
async def demo_metrics():
    return services.demo_metrics()


def _engine(request: Request):
    return getattr(request.app.state, "engine", None)


def _persist_stopped_call(
    engine,
    call: ActiveCall,
    transcript_segments: list[TranscriptSegment],
    recommendations: list[Recommendation],
) -> None:
    try:
        lakebase_persistence.persist_final_call_snapshot(
            engine,
            call=call,
            transcript_segments=transcript_segments,
            recommendations=recommendations,
        )
    except Exception:
        logger.exception("Failed to persist stopped call %s", call.call_id)


def _persist_call(request: Request, call: ActiveCall) -> None:
    engine = _engine(request)
    if engine is None:
        return
    with Session(engine) as session:
        session.merge(
            ActiveCallTable(
                call_id=call.call_id,
                status=call.status,
                scenario_id=call.scenario_id,
                scenario_title=call.scenario_title,
                patient_name=call.patient_name,
                latest_transcript=call.latest_transcript,
                latest_intent=call.latest_intent,
                current_risk_level=call.current_risk_level,
                current_recommendation_id=call.current_recommendation_id,
                started_at=call.started_at,
                ended_at=call.ended_at,
            )
        )
        session.commit()


def _persist_segment(request: Request, segment: TranscriptSegment) -> None:
    engine = _engine(request)
    if engine is None:
        return
    with Session(engine) as session:
        session.merge(
            TranscriptSegmentTable(
                segment_id=segment.segment_id,
                call_id=segment.call_id,
                speaker=segment.speaker,
                text=segment.text,
                is_partial=segment.is_partial,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                asr_latency_ms=segment.asr_latency_ms,
                confidence=segment.confidence,
                created_at=segment.created_at,
            )
        )
        session.commit()


def _persist_recommendation(request: Request, rec: Recommendation) -> None:
    engine = _engine(request)
    if engine is None:
        return
    with Session(engine) as session:
        session.merge(
            RecommendationTable(
                recommendation_id=rec.recommendation_id,
                call_id=rec.call_id,
                trigger_segment_id=rec.trigger_segment_id,
                intent=rec.intent,
                topic=rec.topic,
                risk_level=rec.risk_level,
                recommended_response=rec.recommended_response,
                next_best_action=rec.next_best_action,
                confidence=rec.confidence,
                llm_latency_ms=rec.llm_latency_ms,
                created_at=rec.created_at,
            )
        )
        session.commit()


def _persist_feedback(request: Request, feedback: AgentFeedback) -> None:
    engine = _engine(request)
    if engine is None:
        return
    with Session(engine) as session:
        session.merge(
            FeedbackTable(
                feedback_id=feedback.feedback_id,
                recommendation_id=feedback.recommendation_id,
                call_id=feedback.call_id,
                feedback_type=feedback.feedback_type,
                free_text=feedback.free_text,
                created_by=feedback.created_by,
                created_at=feedback.created_at,
            )
        )
        session.commit()
