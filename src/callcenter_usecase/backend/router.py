from databricks.sdk.service.iam import User as UserOut
from fastapi import BackgroundTasks, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from .core import Dependencies, create_router
from .models import (
    ActiveCall,
    AgentFeedback,
    AnalyzeIn,
    AppConfigOut,
    AudioChunkIn,
    AudioUploadOut,
    DemoMetrics,
    DemoMode,
    EvaluationExample,
    FeedbackIn,
    KnowledgeDocument,
    Recommendation,
    Scenario,
    StartCallIn,
    StartCallOut,
    TranscriptSegment,
)
from .models import VersionOut
from . import operational_store
from . import services

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
async def start_call(
    payload: StartCallIn,
    request: Request,
    config: Dependencies.Config,
    ws: Dependencies.Client,
    background_tasks: BackgroundTasks,
):
    result = services.start_call(payload)
    operational_store.enqueue_persist_call(_engine(request), ws, config, result.call)
    if payload.settings.demo_mode != DemoMode.MICROPHONE:
        background_tasks.add_task(
            services.ingest_scenario_audio,
            result.call.call_id,
            config,
            ws,
            _engine(request),
        )
    return result


@router.post(
    "/calls/{call_id}/live-microphone",
    response_model=ActiveCall,
    operation_id="enableLiveMicrophone",
)
async def enable_live_microphone(call_id: str):
    try:
        return services.enable_live_microphone(call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/calls/{call_id}/stop", response_model=ActiveCall, operation_id="stopCall")
async def stop_call(
    call_id: str,
    request: Request,
    config: Dependencies.Config,
    ws: Dependencies.Client,
):
    try:
        call = services.stop_call(call_id)
        operational_store.enqueue_persist_stopped_call(
            _engine(request),
            ws,
            config,
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
    ws: Dependencies.Client,
    request: Request,
    background_tasks: BackgroundTasks,
):
    try:
        segment = services.transcribe_chunk(payload, config=config, ws=ws)
        operational_store.enqueue_persist_segment(_engine(request), ws, config, segment)
        if services.reserve_auto_recommendation(segment.call_id):
            background_tasks.add_task(
                services.run_reserved_recommendation,
                AnalyzeIn(call_id=segment.call_id, trigger_segment_id=segment.segment_id),
                config,
                ws,
                _engine(request),
            )
        return segment
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError:
        return Response(status_code=204)


@router.get("/audio/scenario/{scenario_id}", operation_id="getScenarioAudio")
def get_scenario_audio(scenario_id: str):
    path = services.scenario_audio_path(scenario_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"No scenario audio for {scenario_id}")
    return FileResponse(path, media_type="audio/wav", filename=f"{scenario_id}.wav")


@router.post(
    "/audio/upload/{call_id}",
    response_model=AudioUploadOut,
    operation_id="uploadAudio",
)
async def upload_audio(call_id: str, request: Request, config: Dependencies.Config, file: UploadFile = File(...)):
    try:
        upload = await services.store_upload(call_id, file, config=config)
        operational_store.enqueue_persist_upload(_engine(request), upload)
        return upload
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/recommendations/analyze",
    response_model=Recommendation,
    operation_id="analyzeCall",
)
async def analyze_call(
    payload: AnalyzeIn,
    config: Dependencies.Config,
    ws: Dependencies.Client,
    request: Request,
):
    try:
        rec = services.analyze_call(payload, config=config)
        operational_store.enqueue_persist_recommendation(_engine(request), ws, config, rec)
        operational_store.enqueue_persist_call(_engine(request), ws, config, services.get_call(rec.call_id))
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
async def submit_feedback(
    recommendation_id: str,
    payload: FeedbackIn,
    request: Request,
    config: Dependencies.Config,
    ws: Dependencies.Client,
):
    try:
        feedback = services.store_feedback(recommendation_id, payload)
        operational_store.enqueue_persist_feedback(_engine(request), ws, config, feedback)
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
