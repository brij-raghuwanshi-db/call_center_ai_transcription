from __future__ import annotations

import base64
import io
import json
import re
import time
import wave
from array import array
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
    DemoMode,
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
from .toyota_catalog import (
    DEFAULT_SCENARIO_ID,
    EVALUATION_SET,
    KNOWLEDGE_BASE,
    SCENARIOS,
    SCRIPTED_SEGMENTS,
    caller_state,
    recommendation_copy,
    run_catalog_rules,
    scenario_by_id,
)


logger = logging.getLogger(__name__)


def resolve_data_dir() -> Path:
    here = Path(__file__).resolve()
    for root in (here.parents[2], here.parents[3], Path.cwd()):
        if (root / "data" / "generated_audio").exists():
            return root / "data"
    return here.parents[3] / "data"


def resolve_audio_dir() -> Path:
    return resolve_data_dir() / "generated_audio"


def resolve_audit_dir() -> Path:
    return resolve_data_dir() / "delta_audit_mock"


def scenario_audio_path(scenario_id: str) -> Path | None:
    path = resolve_audio_dir() / f"{scenario_id}.wav"
    return path if path.exists() else None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = resolve_data_dir()
AUDIO_DIR = resolve_audio_dir()
AUDIT_DIR = resolve_audit_dir()


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
    ingest_cancelled: set[str] = field(default_factory=set)


@dataclass
class _ServingChatMessage:
    role: str
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


STATE = DemoState()


def _scenario_by_id(scenario_id: str) -> Scenario:
    return scenario_by_id(scenario_id)


def _append_audit(kind: str, payload: dict) -> None:
    audit_dir = resolve_audit_dir()
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / f"{kind}.jsonl"
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


def warm_asr_endpoint(config, ws: WorkspaceClient | None = None) -> None:
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
        ws=ws,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "ASR warmup endpoint=%s completed in %s ms with_response=%s",
        config.asr_endpoint_name,
        elapsed_ms,
        response is not None,
    )


def enable_live_microphone(call_id: str) -> ActiveCall:
    """Switch an active call to live mic and stop leftover scenario-WAV ingest."""
    call = get_call(call_id)
    call.settings.demo_mode = DemoMode.MICROPHONE
    STATE.ingest_cancelled.add(call_id)
    logger.info("Live microphone enabled; cancelled scenario ingest for call_id=%s", call_id)
    return call


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
    script = SCRIPTED_SEGMENTS.get(call.scenario_id) or SCRIPTED_SEGMENTS[DEFAULT_SCENARIO_ID]
    if index is None:
        index = len(STATE.transcripts[call.call_id])
    return script[index % len(script)]


def transcribe_chunk(
    payload: AudioChunkIn,
    config=None,
    ws: WorkspaceClient | None = None,
    *,
    dedupe_overlap: bool = True,
) -> TranscriptSegment:
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
        served = _query_serving_endpoint(
            config.asr_endpoint_name,
            {
                "call_id": call.call_id,
                "chunk_id": payload.chunk_id,
                "audio_base64": payload.audio_base64,
                "sample_rate": payload.sample_rate,
                "language": payload.language.split("-")[0] if payload.language else "en",
                "mime_type": payload.mime_type or "audio/wav",
                "filename": payload.filename or "chunk.wav",
            },
            ws=ws,
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
            elif dedupe_overlap and call.settings.demo_mode != DemoMode.MICROPHONE:
                text = _new_overlap_asr_text(call.call_id, served_text)
            else:
                text = served_text
            logger.info("ASR produced %s character(s) for call_id=%s", len(text), call.call_id)
        elif served is None:
            logger.warning(
                "ASR endpoint=%s call_id=%s returned no response",
                config.asr_endpoint_name,
                call.call_id,
            )
            raise RuntimeError(
                f"ASR endpoint {config.asr_endpoint_name} returned no response"
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
    if asr_confidence < 0.05:
        asr_confidence = 0.05
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


def ingest_scenario_audio(
    call_id: str,
    config=None,
    ws: WorkspaceClient | None = None,
    engine=None,
    *,
    chunk_seconds: float = 8.0,
) -> int:
    """Transcribe the matching scenario WAV through Databricks ASR, with script fallback."""
    call = get_call(call_id)
    if call.settings.demo_mode == DemoMode.MICROPHONE:
        logger.info("Skipping scenario audio ingest for live microphone call_id=%s", call_id)
        return 0
    script = SCRIPTED_SEGMENTS.get(call.scenario_id) or SCRIPTED_SEGMENTS[DEFAULT_SCENARIO_ID]
    audio_path = scenario_audio_path(call.scenario_id)
    produced = 0
    if audio_path is not None and getattr(config, "use_databricks_asr", False):
        logger.info("Ingesting scenario audio %s for call_id=%s", audio_path, call_id)
        for index, chunk_b64 in enumerate(_wav_base64_chunks(audio_path, chunk_seconds)):
            if call_id in STATE.ingest_cancelled or get_call(call_id).status == CallStatus.ENDED:
                logger.info("Stopping scenario ingest for call_id=%s", call_id)
                break
            speaker, fallback_text = script[index] if index < len(script) else (Speaker.PATIENT, "")
            try:
                transcribe_chunk(
                    AudioChunkIn(
                        call_id=call_id,
                        audio_base64=chunk_b64,
                        speaker_hint=speaker,
                        sample_rate=16000,
                        language="en",
                        mime_type="audio/wav",
                        filename="chunk.wav",
                        cumulative_audio=False,
                    ),
                    config=config,
                    ws=ws,
                    dedupe_overlap=False,
                )
                produced += 1
                _persist_operational_segment(engine, ws, config, call_id)
            except Exception as error:
                logger.warning(
                    "Scenario ASR chunk %s failed for call_id=%s: %s",
                    index,
                    call_id,
                    error,
                )
                if fallback_text:
                    add_transcript_segment(
                        TranscriptSegment(
                            call_id=call_id,
                            speaker=speaker,
                            text=fallback_text,
                            start_ms=index * int(chunk_seconds * 1000),
                            end_ms=(index + 1) * int(chunk_seconds * 1000),
                            asr_latency_ms=0,
                            confidence=0.72,
                        )
                    )
                    produced += 1
                    _persist_operational_segment(engine, ws, config, call_id)
    if produced == 0 and call_id not in STATE.ingest_cancelled:
        logger.warning("Seeding scripted transcript for call_id=%s scenario=%s", call_id, call.scenario_id)
        for index, (speaker, text) in enumerate(script):
            if call_id in STATE.ingest_cancelled or get_call(call_id).status == CallStatus.ENDED:
                break
            add_transcript_segment(
                TranscriptSegment(
                    call_id=call_id,
                    speaker=speaker,
                    text=text,
                    start_ms=index * 8000,
                    end_ms=(index + 1) * 8000,
                    asr_latency_ms=0,
                    confidence=0.7,
                )
            )
            produced += 1
            _persist_operational_segment(engine, ws, config, call_id)
    if produced and call.settings.auto_recommendations_enabled:
        try:
            recommendation = analyze_call(AnalyzeIn(call_id=call_id), config=config)
            from . import operational_store

            operational_store.enqueue_persist_recommendation(engine, ws, config, recommendation)
            operational_store.enqueue_persist_call(engine, ws, config, get_call(call_id))
        except Exception as error:
            logger.warning("Post-ingest recommendation failed for call_id=%s: %s", call_id, error)
    logger.info("Ingested %s transcript segment(s) for call_id=%s", produced, call_id)
    return produced


def _persist_operational_segment(engine, ws, config, call_id: str) -> None:
    from . import operational_store

    try:
        segments = transcript_for_call(call_id)
        if not segments:
            return
        operational_store.enqueue_persist_segment(engine, ws, config, segments[-1])
    except Exception as error:
        logger.warning("Operational persist failed for call_id=%s: %s", call_id, error)


def _wav_base64_chunks(path: Path, chunk_seconds: float) -> list[str]:
    chunks: list[str] = []
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        frames_per_chunk = max(1, int(sample_rate * chunk_seconds))
        min_frames = max(1, int(sample_rate * 0.8))
        while True:
            frames = source.readframes(frames_per_chunk)
            if not frames:
                break
            frame_count = len(frames) // max(1, sample_width * channels)
            if frame_count < min_frames or _pcm16_rms(frames, sample_width) < 0.012:
                continue
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as output:
                output.setnchannels(channels)
                output.setsampwidth(sample_width)
                output.setframerate(sample_rate)
                output.writeframes(frames)
            chunks.append(base64.b64encode(buffer.getvalue()).decode("ascii"))
    return chunks


def _pcm16_rms(frames: bytes, sample_width: int) -> float:
    if sample_width != 2 or len(frames) < 4:
        return 1.0
    samples = array("h")
    samples.frombytes(frames[: len(frames) - (len(frames) % 2)])
    if not samples:
        return 0.0
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    return (mean_square ** 0.5) / 32768.0


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


def run_reserved_recommendation(
    payload: AnalyzeIn,
    config=None,
    ws: WorkspaceClient | None = None,
    engine=None,
) -> Recommendation | None:
    try:
        recommendation = analyze_call(payload, config=config)
        from . import operational_store

        if recommendation is not None:
            operational_store.enqueue_persist_recommendation(engine, ws, config, recommendation)
            operational_store.enqueue_persist_call(engine, ws, config, get_call(payload.call_id))
        return recommendation
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
    audio_dir = Path(getattr(config, "audio_volume_path", None) or resolve_audio_dir()) if config else resolve_audio_dir()
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
    tokens = {t.lower().strip(".,!?") for t in query.split() if len(t) >= 3}
    scored: list[tuple[int, KnowledgeDocument]] = []
    for doc in KNOWLEDGE_BASE:
        title = doc.title.lower()
        tags = " ".join(doc.tags).lower()
        haystack = " ".join([title, doc.section, doc.content, tags]).lower()
        score = 0
        for token in tokens:
            if token in haystack:
                score += 1
            if token in tags:
                score += 2
            if token in title:
                score += 1
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
    return run_catalog_rules(text)


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
    response, action, rationale = recommendation_copy(call.scenario_id, risk_level)
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
        patient_state=_text_field(served_json, "patient_state", caller_state(call.scenario_id, transcript_window)),
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
        compliance_notes=[
            "Verify VIN and owner identity before discussing coverage or vehicle location.",
            "Recommendation only; do not execute external dispatch or dealer actions in V1.",
        ],
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
        else "High-risk vehicle safety concern detected."
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


def _query_serving_endpoint(
    endpoint_name: str,
    inputs: dict,
    ws: WorkspaceClient | None = None,
) -> object | None:
    payload = {
        key: inputs[key]
        for key in (
            "call_id",
            "chunk_id",
            "audio_base64",
            "sample_rate",
            "language",
            "mime_type",
            "filename",
        )
        if key in inputs
    }
    try:
        client = ws or WorkspaceClient()
        try:
            return client.serving_endpoints.query(name=endpoint_name, dataframe_records=[payload])
        except TypeError:
            return client.serving_endpoints.query(name=endpoint_name, inputs=payload)
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
            "Infer the actual Toyota owner-support scenario, topic, owner state, risk, and next best action from the transcript.",
            "Do not assume the initial demo scenario is correct if the transcript indicates a different issue.",
            "If the transcript contains the caller's name, return it as patient_name; otherwise return null.",
            "Use the speaker labels in the transcript to distinguish owner needs from agent responses.",
            "Never advise continued driving on a red coolant-temperature or oil-pressure warning.",
            "Never advise opening a hot radiator or coolant reservoir cap.",
            "Route immobilized highway calls to roadside or SOS before Brand Engagement warranty discussion.",
            "Automatic Collision Notification or SOS with no occupant response is emergency dispatch, not a product case.",
            "Do not keep Destination Assist or restaurant requests on the SOS emergency line.",
            "Do not quote lemon-law, buyback, payoff, or VSA claim outcomes. Transfer money calls to TFS or Extra Care.",
            "Service Connect dealer contact is opt-in. Process opt-out requests immediately.",
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
                        "You are a Toyota call-center next-best-action assistant for a human Brand Engagement, "
                        "roadside, or Safety Connect agent. Return one valid JSON object only, with no markdown, "
                        "no prose outside JSON, and values that match the required schema. Prioritize occupant "
                        "safety, stop-driving guidance, and the correct Toyota queue over destination urgency."
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
        r"(?i)^(?:a (?:healthcare|toyota)(?: call center conversation between a (?:patient|vehicle owner|caller) and an agent| owner-support call between a caller and an agent)[.\s,]*)+",
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
