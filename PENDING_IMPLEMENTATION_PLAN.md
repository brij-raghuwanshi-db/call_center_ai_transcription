# Pending Implementation Plan

This file tracks what is still pending after the current Databricks Apps POC deployment. The app is usable as a demo, and the first real Databricks ASR path is now deployed. Several Databricks-native pieces are still mocked, manually configured, or only partially wired.

## Completed So Far

- Built and deployed the Databricks App using the custom `scripts/build_databricks_app.py` bundle path because the full `apx`/React build remains blocked by local package registry issues.
- Deployed a real `faster-whisper` ASR model to Databricks Model Serving as `callcenter-asr-faster-whisper`.
- Registered the ASR model in Unity Catalog as `users.brijendra_raghuwanshi.callcenter_asr_faster_whisper`; the currently validated serving version is version `5`.
- Verified direct Model Serving audio transcription by sending base64 WAV payloads and receiving text back.
- Granted the Databricks App service principal `CAN_QUERY` on the ASR serving endpoint so the app backend can call it.
- Flipped the deployed app to `CALLCENTER_USECASE_USE_DATABRICKS_ASR=true`.
- Disabled scripted transcript fallback in deployment config with `CALLCENTER_USECASE_USE_SCRIPTED_TRANSCRIPT_FALLBACK=false`.
- Removed the `Process next segment` scripted demo button from the deployed UI.
- Removed normal UI/backend use of `scripted_segment_index`; transcripts now come from browser transcript text or Databricks ASR output only.
- Updated microphone handling so Databricks ASR receives cumulative browser audio and the backend appends only newly transcribed text.
- Verified cumulative ASR through the deployed app API: the second cumulative audio request appended only the new sentence.
- Saved microphone recordings and uploaded audio files to the UC Volume path under `/Volumes/users/brijendra_raghuwanshi/demo_assets/callcenter_audio`.
- Added `New Call / Reset UI` behavior so stopping a call preserves review state while reset clears the UI for a new session.

## 1. Real Databricks ASR

**Current state:** Completed for the POC. Microphone transcription uses browser speech recognition when `CALLCENTER_USECASE_USE_DATABRICKS_ASR=false`; the deployed app currently uses Databricks Model Serving because `CALLCENTER_USECASE_USE_DATABRICKS_ASR=true`. The project includes the original faster-whisper MLflow pyfunc wrapper, plus a self-contained serving model script in `scripts/asr_serving_model.py`. `scripts/deploy_asr_serving.py` registers `users.brijendra_raghuwanshi.callcenter_asr_faster_whisper` and deploys it to the `callcenter-asr-faster-whisper` serving endpoint. The endpoint is ready and has been validated with real audio payloads.

**Done:**

- Packaged a `faster-whisper` inference model for MLflow/Databricks Model Serving.
- Added a self-contained MLflow "model from code" script to avoid serving-time imports of the app package.
- Defined and validated the request/response contract:
  - Input: `audio_base64`, `sample_rate`, `language`, `call_id`, `chunk_id`.
  - Output: `text`, `transcript`, `confidence`, `asr_latency_ms`, `language`, and segment metadata.
- Deployed the model to Databricks Model Serving with `scripts/deploy_asr_serving.py`.
- Used Databricks serverless Jobs for model registration/deployment after confirming serverless Jobs support through `environment_key` and `environments`.
- Set deployed app environment variables:
  - `CALLCENTER_USECASE_ASR_ENDPOINT_NAME=callcenter-asr-faster-whisper`
  - `CALLCENTER_USECASE_USE_DATABRICKS_ASR=true`
  - `CALLCENTER_USECASE_USE_SCRIPTED_TRANSCRIPT_FALLBACK=false`
- Updated `src/callcenter_usecase/backend/services.py` so real ASR output drives transcript text.
- Fixed response extraction for Databricks SDK serving responses by reading `predictions`.
- Granted the app service principal `CAN_QUERY` on the ASR endpoint.
- Added clear UI status showing Browser ASR vs Databricks ASR mode.
- Removed the script-based transcript control from the deployed UI.

**Remaining work:**

- Improve confidence and timing propagation from the ASR response into `TranscriptSegment` instead of using the current fixed `confidence=0.93`.
- Add more robust error surfacing and observability for Model Serving failures instead of hiding low-level exceptions.
- Tune model size, workload size, and scale-to-zero behavior for latency and demo reliability.
- Decide whether to use a larger Whisper model for better accuracy after the POC.

**Validation:**

- Direct Model Serving query with generated speech returned transcript text.
- Deployed app API query with generated "Mic testing one two three" audio returned text.
- Cumulative audio test returned new subsequent sentence text instead of relying on scripted segments.
- Live UI no longer shows `Process next segment`.
- Confirmed no scripted text appears through the removed normal UI path.

## 2. Uploaded Audio Transcription

**Current state:** Partially implemented. Uploaded audio is saved to the UC Volume and can be played in the UI. When Databricks ASR mode is enabled, the UI sends the uploaded audio base64 to `/api/audio/chunk`, and the backend calls the ASR Model Serving endpoint. This is sufficient for short demo WAVs. A backend-driven file transcription pipeline is still pending.

**Implementation plan:**

- Keep the current browser-side uploaded audio ASR path for short demo files.
- Add backend-driven transcription for larger or production-like uploads:
  - Upload file to Volume.
  - Backend reads the file through Databricks Files API.
  - Backend splits audio into manageable chunks.
  - Backend calls ASR Model Serving for each chunk.
- Add a new endpoint such as `/api/audio/transcribe-upload/{call_id}` to start transcription for uploaded files.
- Store generated transcript segments using the existing `add_transcript_segment` flow.
- Update `ui-preview.html` so upload progress reflects actual transcription progress, not only playback progress.

**Done:**

- Uploads are saved to `/Volumes/users/brijendra_raghuwanshi/demo_assets/callcenter_audio`.
- Uploaded audio can be sent to Databricks ASR from the UI when ASR mode is enabled.
- The script-based "Process next segment" path is no longer required for uploaded audio transcription.

**Remaining work:**

- Prefer backend-driven transcription:
  - Upload file to Volume.
  - Backend reads the file through Databricks Files API.
  - Backend splits audio into manageable chunks.
  - Backend calls ASR Model Serving for each chunk.
- Add duration/chunk-size limits and progress UI for longer audio.

**Validation:**

- Upload a WAV and verify transcript segments appear from the uploaded audio.
- Verify uploaded audio remains saved under `/Volumes/users/brijendra_raghuwanshi/demo_assets/callcenter_audio`.
- Verify large files do not block the app request thread once backend-driven transcription is implemented.

## 3. Lakebase Runtime Wiring

**Current state:** Lakebase code exists, but the deployed app logs show the app resource name mismatch: `app.yml` uses `valueFrom: postgres`, while `databricks.yml` defines the app resource as `db`. The deployed app therefore falls back to in-memory state.

**Implementation plan:**

- Update `app.yml` so `LAKEBASE_ENDPOINT` references the correct Databricks Apps resource name.
- Confirm the correct syntax for Databricks Apps postgres resource injection.
- Redeploy and verify `PGHOST` or `LAKEBASE_ENDPOINT` is present in the runtime.
- Confirm SQLModel tables are created in Lakebase during startup.
- Exercise call start, transcript, recommendation, and feedback flows.
- Confirm app restart does not lose call state.

**Likely files:**

- `app.yml`
- `databricks.yml`
- `src/callcenter_usecase/backend/core/lakebase.py`
- `src/callcenter_usecase/backend/router.py`

**Validation:**

- App logs no longer show `Lakebase is not configured`.
- Active call state persists across requests and app restarts.
- `_persist_call`, `_persist_segment`, `_persist_recommendation`, and feedback persistence are actually writing to Lakebase.

## 4. Real LLM Model Serving

**Current state:** Completed for the POC. The deployed app now sets `CALLCENTER_USECASE_LLM_ENDPOINT_NAME=databricks-gpt-5-5` and `CALLCENTER_USECASE_USE_MOCK_LLM=false`, so recommendations are generated through the Databricks-hosted GPT-5.5 foundation model endpoint. The UI shows the recommendation source and reasoning endpoint, and the backend falls back to deterministic copy only if the endpoint call fails. Recommendation generation is now decoupled from transcript chunk responses so GPT-5.5 latency does not block ASR transcript updates.

**Implementation plan:**

- Done: Confirmed the Databricks-hosted GPT 5.5 endpoint name and query contract.
- Done: Set:
  - `CALLCENTER_USECASE_LLM_ENDPOINT_NAME=<gpt-5.5-endpoint>`
  - `CALLCENTER_USECASE_USE_MOCK_LLM=false`
- Done: Hardened the LLM prompt to require strict JSON.
- Done: Added response extraction/normalization for Databricks chat-completion responses.
- Done: Coerced model fields for risk, confidence, citations, alerts, booleans, and text fields before creating a `Recommendation`.
- Done: Stored model source, endpoint name, and served payload in recommendation/audit metadata.
- Done: Moved automatic recommendations to a throttled background path so `/api/audio/chunk` can return the transcript before GPT-5.5 finishes.
- Done: Added UI polling so the latest recommendation appears after the background model call completes.
- Done: Expanded the LLM transcript context from a few raw text snippets to a larger speaker-labeled transcript window.
- Remaining: Improve hard-failure behavior so demo operators can choose whether LLM failure should block the recommendation or use fallback.
- Remaining: Further tune prompt/model/cadence for lower end-to-end recommendation latency during live calls.

**Likely files:**

- `src/callcenter_usecase/backend/services.py`
- `src/callcenter_usecase/backend/models.py`
- `app.yml`
- `databricks.yml`

**Validation:**

- Recommendations come from the model endpoint; browser validation showed `Source: databricks_llm` and `Reasoning endpoint: databricks-gpt-5-5`.
- Invalid or partial model JSON is normalized before the app accepts it.
- Model latency is displayed in the UI.
- Model input/output audit records are stored in the current JSONL audit path.

## 5. Vector Search RAG

**Current state:** Databricks Vector Search is now wired into the backend recommendation path. The app uses the direct-access index `users.brijendra_raghuwanshi.knowledge_embeddings_index` and first calls the embedding endpoint `databricks-gte-large-en` to generate a query vector. If the embedding endpoint or Vector Search query fails, the backend falls back to the existing in-memory knowledge snippets so the demo can continue.

**Implementation plan:**

- Done: Created/identified the Delta source table under `users.brijendra_raghuwanshi`.
- Done: Created/identified the Databricks Vector Search index `users.brijendra_raghuwanshi.knowledge_embeddings_index`.
- Done: Replaced the primary `retrieve_knowledge` path with Databricks embedding + Vector Search retrieval.
- Done: Return retrieved chunk IDs, source document paths, quotes, and scores as recommendation citations.
- Pending hardening: Add an explicit setup script/notebook for repeatably creating the knowledge table, embeddings, permissions, and index from source PDFs.
- Pending hardening: Add UI/runtime status that shows whether citations came from Vector Search or local fallback.

**Likely files/resources:**

- `src/callcenter_usecase/backend/services.py`
- `data/knowledge_base/`
- New setup notebook or script for document parsing/index creation.
- `databricks.yml` for Vector Search resources if supported.

**Validation:**

- Done: Citations reflect retrieved chunks from Vector Search when the configured endpoints are available.
- Changing the knowledge table changes returned citations.
- Done: Recommendation output includes citation references from the real index before the LLM is prompted.

## 6. Delta Tables For History And Audit

**Current state:** Audit is written as JSONL fallback files. There are no real Delta writes for transcript history, recommendation history, feedback history, model audit, or audio metadata.

**Implementation plan:**

- Define Delta table schemas in `users.brijendra_raghuwanshi`.
- Add backend write paths for:
  - `call_events`
  - `transcript_events`
  - `recommendation_events`
  - `feedback_events`
  - `model_audit_events`
  - `audio_metadata`
- Use Databricks SQL Warehouse, SQL Connector, or a workspace job for writes from the app.
- Keep Lakebase for live state and Delta for durable history.
- Add replay/evaluation queries that read from Delta instead of JSONL.

**Validation:**

- Every call creates durable Delta records.
- Feedback and model outputs are queryable after app restart.
- Supervisor metrics can be computed from Delta.

## 7. Unity Catalog Volume Resource Management

**Current state:** The managed Volume `users.brijendra_raghuwanshi.demo_assets` was created manually and the app identity was manually granted access. Uploads and mic-recording saves now work, but the Volume and grants are not codified in the bundle. The ASR serving endpoint permission was also granted manually to the app service principal.

**Implementation plan:**

- Add the UC Volume to infrastructure setup, either through bundle resources, a setup script, or documented CLI commands.
- Add repeatable grants for the Databricks App service principal:
  - `USE_CATALOG` on `users`
  - `USE_SCHEMA` on `users.brijendra_raghuwanshi`
  - `READ_VOLUME`, `WRITE_VOLUME` on `users.brijendra_raghuwanshi.demo_assets`
  - `CAN_QUERY` on serving endpoint `callcenter-asr-faster-whisper`
- Make `CALLCENTER_USECASE_AUDIO_VOLUME_PATH` explicit in deployment configuration.

**Validation:**

- A fresh workspace deployment creates or validates the Volume.
- App can upload mic recordings without manual permission fixes.
- App can query the ASR serving endpoint without manual permission fixes.

## 8. True Streaming And Audio Chunking

**Current state:** Partially implemented. Browser mic audio is now captured for live Databricks ASR as short 16 kHz mono PCM/WAV chunks instead of WebM rolling blobs. `MediaRecorder` remains only for saving the full call recording to the UC Volume when the mic stops. This reduces decode overhead and avoids ever-growing audio payloads, but it is still HTTP chunk polling rather than true token/audio streaming. Uploaded audio playback progress is still not the same as backend transcription progress.

**Implementation plan:**

- Keep cumulative HTTP chunk POST for the POC.
- Decide on HTTP chunk POST vs WebSocket for production depending on Databricks Apps support.
- Implement chunk sequencing and idempotency:
  - `call_id`
  - `chunk_id`
  - `sequence_number`
  - `start_ms`
  - `end_ms`
- Return partial and final transcripts separately.
- Update UI to show partial transcript while a final segment is still being processed.
- Add latency measurements for capture, ASR, LLM, and total recommendation time.

**Done:**

- Implemented microphone audio capture through the browser.
- Implemented cumulative audio sending for the first Databricks ASR mode.
- Replaced ever-growing cumulative audio requests with Databricks-native 16 kHz mono PCM/WAV chunks to reduce ASR lag while preserving full-call recording upload on stop.
- Implemented transcript delta extraction to avoid repeating the full cumulative transcript.
- Verified the deployed ASR endpoint accepts short WAV payloads and can return a sample transcript in about 1.36 seconds.
- Validated that a second cumulative audio request appends the new sentence rather than using script-based text.
- Removed the scripted `Process next segment` button from the deployed UI.

**Remaining work:**

- Add explicit sequence numbers/start/end timestamps to `AudioChunkIn`.
- Add idempotency handling for retries.
- Add partial-vs-final transcript status.
- Add capture-to-ASR and ASR-to-recommendation latency breakdowns.
- Investigate WebSocket or lower-latency streaming options after the POC.

**Validation:**

- Transcript updates every few seconds from cumulative ASR audio.
- UI shows partial text before final text.
- Latency stays within the 1-2 second demo target when endpoint capacity allows it.

## 9. Speaker Diarization

**Current state:** Speaker labels are no longer scripted in the normal deployed transcript path. The app now supports a V1 speaker hint for mono browser-mic demos: the UI shows side-by-side `Patient` and `Agent` buttons, sends the selected speaker with each audio chunk, and visually highlights the current selection for fast switching during a demo. The backend also recognizes spoken prefixes such as `agent speaking`, `patient speaking`, `agent:`, and `patient:`. Mixed-channel audio is still not separated into agent and patient speakers by a true diarization model.

**Implementation plan:**

- Done for V1.5: allow UI/manual metadata to mark source speaker when sending chunks.
- Done for V1.5: replace the speaker dropdown with side-by-side speaker buttons for easier live demo switching.
- Done for V1.5: allow optional spoken speaker prefixes and strip those prefixes from stored transcript text.
- For V2, add diarization using a model or library that can run in Databricks.
- If stereo audio is available, split channels and map channel 1/2 to agent/patient.
- Store speaker labels in transcript segments.

**Validation:**

- Transcript identifies agent vs patient for uploaded or live audio.
- Recommendations focus primarily on patient utterances but can use agent context.

## 10. Acoustic Feature Extraction

**Current state:** `enable_acoustic_features` exists in config, but no acoustic features are computed or used.

**Implementation plan:**

- Reuse ideas from the previous voice analytics project without copying the codebase directly.
- Extract basic features:
  - volume/intensity
  - speech rate
  - pause duration
  - pitch variance where feasible
  - urgency/stress indicators
- Add acoustic features to transcript segment metadata or a parallel event table.
- Include high-level features in recommendation prompts.

**Validation:**

- UI can show basic voice activity/stress indicators.
- Recommendations can cite urgency indicators when relevant.

## 11. UI Configuration Transparency

**Current state:** Partially implemented in `ui-preview.html`. The UI calls `/api/config` and shows whether ASR is Browser ASR or Databricks ASR, including the ASR endpoint name. It also shows mock LLM status. Lakebase/Delta/audit status is still not fully runtime-verified in the UI.

**Implementation plan:**

- Continue calling `/api/config` when the page loads.
- Display full actual runtime mode:
  - ASR: mock, browser STT, or Databricks Model Serving.
  - LLM: mock or endpoint name.
  - Lakebase: connected or in-memory.
  - Audit: JSONL fallback or Delta.
  - Volume path.
- Add a small "Runtime Status" panel.

**Done:**

- ASR badge now switches between Browser ASR and Databricks ASR based on runtime config.
- Databricks ASR badge shows `callcenter-asr-faster-whisper`.
- LLM badge shows mock-vs-endpoint state.

**Remaining work:**

- Add explicit Lakebase connected/in-memory status from backend health.
- Add explicit audit sink status.
- Add Volume path and endpoint health in a runtime status panel.

**Validation:**

- UI accurately shows mock vs real components.
- Demo operator can explain what is live and what is fallback.

## 12. Full React Frontend Build

**Current state:** Deployment still packages `ui-preview.html` as the frontend because local `apx`/npm/PyPI build issues blocked the full React app. The static UI has continued to evolve and now includes the real Databricks ASR flow, cumulative microphone audio, Volume upload/save, runtime ASR badge, and New Call / Reset UI behavior. The React component has been partially cleaned up to remove the scripted `Process next segment` button, but it is not the deployed frontend yet.

**Implementation plan:**

- Fix local package registry/build access.
- Run the normal `apx` React build.
- Port recent `ui-preview.html` behavior into the React component:
  - mic recording
  - browser speech recognition fallback
  - Volume upload
  - New Call / Reset UI
  - runtime status panel
  - Databricks ASR cumulative audio flow
  - removal of script-based transcript controls
- Update `scripts/build_databricks_app.py` to package the real built frontend instead of the static HTML fallback.

**Validation:**

- Deployed UI comes from the React app.
- Feature parity exists between preview and React.
- Static HTML fallback remains optional only for emergency deployment.

## 13. Redaction And PHI Controls

**Current state:** Redaction config and UI toggles exist, but PHI masking is not implemented.

**Implementation plan:**

- Add a redaction service before transcript persistence and model calls.
- Mask common PHI patterns:
  - phone numbers
  - dates of birth
  - MRNs/member IDs
  - addresses
  - emails
- Add a toggle for storing raw vs redacted transcript.
- Make prompt/audit behavior explicit for HIPAA demo discussion.

**Validation:**

- PHI-like strings are masked when redaction is enabled.
- Raw audio retention and transcript masking behavior are documented.

## 14. Evaluation And MLflow

**Current state:** Feedback can be captured in the demo, but systematic evaluation and MLflow tracing are not implemented.

**Implementation plan:**

- Create a labeled evaluation set from synthetic scenarios.
- Track:
  - ASR WER
  - recommendation acceptance rate
  - escalation correctness
  - latency
  - summary quality
  - citation relevance
- Log model calls and outputs with MLflow tracing if available.
- Add a supervisor/evaluation view backed by Lakebase or Delta.

**Validation:**

- Evaluation metrics can be reproduced after a demo run.
- Feedback improves or informs prompt/model changes.

## 15. Telephony Integration

**Current state:** The demo uses browser microphone and uploaded audio. Synthetic scenario segments are no longer part of the normal deployed transcript flow. There is no real call-center telephony integration.

**Implementation plan:**

- Identify target telephony source:
  - Twilio
  - Genesys
  - Five9
  - WebRTC/SIP bridge
  - customer call recording stream
- Define audio stream ingestion contract.
- Map call/session identifiers to app call IDs.
- Implement secure token/auth handling.
- Keep the current browser demo path as a local fallback.

**Validation:**

- A real or simulated telephony stream can populate the transcript.
- Multiple call sessions can be tracked independently.

## 16. Deployment Automation And Documentation

**Current state:** Deployment works through direct CLI import/deploy. The ASR endpoint was deployed successfully using a serverless Databricks Jobs run and is now queried by the app. Some resources and grants were fixed manually, including UC Volume grants and ASR endpoint `CAN_QUERY` for the app service principal.

**Implementation plan:**

- Update deployment docs for:
  - Volume creation.
  - UC grants.
  - app identity.
  - Lakebase resource wiring.
  - Model Serving endpoint variables.
  - ASR endpoint `CAN_QUERY` permission for the app service principal.
  - Vector Search endpoint/index.
- Update `databricks.yml` where possible to declare resources.
- Add a setup script for resources not supported by bundle syntax.
- Add a smoke-test script:
  - start call
  - upload file
  - process transcript from real audio
  - generate recommendation
  - stop call
  - verify Volume/Lakebase/Delta records.

**Validation:**

- A clean deployment can be repeated without manual troubleshooting.
- Smoke test passes after every deploy.

## Recommended Implementation Order

1. Fix Lakebase runtime resource wiring.
2. Add a fuller UI runtime status panel so demos show what is live vs mocked.
3. Harden the completed ASR path with better latency, confidence, error logging, and endpoint health checks.
4. Add backend-driven uploaded-audio transcription for longer files.
5. Tune real LLM recommendation latency, prompt quality, and fallback behavior.
6. Create Delta audit/history tables.
7. Build PDF parsing and Vector Search RAG.
8. Codify Volume resources, UC grants, ASR endpoint permissions, and foundation model endpoint assumptions.
9. Port static UI work into the React frontend.
10. Add redaction, evaluation, MLflow tracing, and telephony integration.
