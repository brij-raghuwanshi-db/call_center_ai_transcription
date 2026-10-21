# Call Center Use Case

Databricks-native POC for a healthcare call-center assistant. The app helps a human call center agent during a live or simulated patient call by showing a running transcript, intent, risk alerts, RAG citations, suggested response, next-best action, supervisor metrics, and feedback capture.

## What Is Implemented

- React + FastAPI Databricks App scaffolded with `apx`.
- Synthetic healthcare call scenarios:
  - Appointment retention.
  - Medication concern.
  - Billing confusion.
  - Symptom escalation.
  - Care navigation.
- Generated 60-second WAV files for every scenario under `data/generated_audio/`.
- Script metadata with speaker labels under `data/synthetic_scripts/`.
- Synthetic healthcare knowledge base in text and PDF form under `data/knowledge_base/`.
- FastAPI endpoints for call lifecycle, transcript, audio upload/chunks, recommendation analysis, feedback, replay, config, scenarios, knowledge documents, and demo metrics.
- Mock ASR fallback that returns speaker-labeled scripted segments.
- Optional Databricks Model Serving hooks for ASR and GPT reasoning when mock flags are disabled.
- Deterministic healthcare guardrail rules for urgent symptoms, medication adherence, retention risk, and HIPAA reminders.
- Vector Search-style local retrieval fallback over synthetic knowledge snippets.
- Lakebase-compatible SQLModel tables plus in-memory fallback when `PGAPPNAME`/PGlite is not configured.
- Delta-style audit fallback as JSONL files under `data/delta_audit_mock/`.
- Agent console with mic, upload, generated scenario controls, transcript, recommendation, citations, alerts, feedback, and summary.
- Supervisor panel with active calls and meta metrics.

## Architecture

```text
React Databricks App
  -> FastAPI backend
  -> ASR Model Serving endpoint or scripted mock ASR
  -> deterministic healthcare rules
  -> Vector Search or local RAG fallback
  -> GPT 5.5 Model Serving endpoint or mock recommendation engine
  -> Unity Catalog target users.brijendra_raghuwanshi
  -> Lakebase live state when configured
  -> Delta-style JSONL audit fallback for local demo
```

## Environment Variables

The `apx` config uses the app slug prefix. Set these as needed:

```bash
CALLCENTER_USECASE_UC_CATALOG=users
CALLCENTER_USECASE_UC_SCHEMA=brijendra_raghuwanshi
CALLCENTER_USECASE_DELTA_SCHEMA_NAME=brijendra_raghuwanshi
CALLCENTER_USECASE_LLM_ENDPOINT_NAME=databricks-gpt-5-5
CALLCENTER_USECASE_ASR_ENDPOINT_NAME=callcenter-asr-faster-whisper
CALLCENTER_USECASE_VECTOR_SEARCH_ENDPOINT_NAME=<your-vector-search-endpoint>
CALLCENTER_USECASE_VECTOR_SEARCH_INDEX_NAME=<your-index>
CALLCENTER_USECASE_USE_DATABRICKS_ASR=false
CALLCENTER_USECASE_USE_MOCK_ASR=true
CALLCENTER_USECASE_USE_MOCK_LLM=false
CALLCENTER_USECASE_USE_SCRIPTED_TRANSCRIPT_FALLBACK=false
CALLCENTER_USECASE_ENABLE_REDACTION=false
CALLCENTER_USECASE_ENABLE_ACOUSTIC_FEATURES=true
```

By default, the app targets Unity Catalog catalog `users` and schema `brijendra_raghuwanshi` for demo Delta tables, parsed document chunks, and Vector Search source tables. Keep those defaults unless you intentionally deploy into another UC namespace.

For Databricks Apps deployment, configure model serving, Lakebase, volumes, and permissions through Databricks App resources or bundle resources. Local development can run without Lakebase; the app falls back to in-memory state.

## Generate Demo Assets

Assets are already generated, but you can regenerate them:

```bash
python3 scripts/generate_demo_assets.py
```

This uses macOS `say` and `afconvert` when available. If unavailable, it writes deterministic tone-placeholder WAVs so the file pipeline still works.

## Run Locally

Install dependencies when package registries are reachable:

```bash
apx dev start
```

If `apx` is not on your `PATH`, use:

```bash
/Users/brijendra.raghuwanshi/.local/bin/apx dev start
```

Useful commands:

```bash
apx dev logs -f
apx dev status
apx dev check
apx dev stop
```

## Deploy Databricks ASR

The app can use browser speech recognition for the demo or a Databricks-hosted ASR endpoint. Browser mode is active when:

```bash
CALLCENTER_USECASE_USE_DATABRICKS_ASR=false
```

To register and deploy the faster-whisper ASR model to Unity Catalog Model Registry and Model Serving, run the deployment script from a Databricks-capable Python environment:

```bash
python3 scripts/deploy_asr_serving.py \
  --model-name users.brijendra_raghuwanshi.callcenter_asr_faster_whisper \
  --endpoint-name callcenter-asr-faster-whisper \
  --whisper-model-size base.en \
  --workload-size Small
```

After the serving endpoint is ready, set:

```bash
CALLCENTER_USECASE_ASR_ENDPOINT_NAME=callcenter-asr-faster-whisper
CALLCENTER_USECASE_USE_DATABRICKS_ASR=true
CALLCENTER_USECASE_USE_SCRIPTED_TRANSCRIPT_FALLBACK=false
```

The ASR endpoint accepts DataFrame records with `audio_base64`, `language`, `call_id`, and `chunk_id`, and returns `text`/`transcript`, confidence, timing, and segment metadata.

## Demo Runbook

1. Open the app.
2. Choose `Symptom Escalation` for the highest-impact demo.
3. Click `Start`.
4. Click `Start mic` and speak naturally, or upload a WAV file.
5. Watch the real ASR transcript, alerts, citations, recommendation, and summary update.
6. Click `used`, `helpful`, `wrong`, `ignored`, or `not helpful` to store feedback.
7. Show the supervisor dashboard metrics.
8. Stop the call.
9. If live ASR or Model Serving is unavailable, keep mock flags enabled and use the same UI flow.

## Deploy

Build and deploy with Databricks Asset Bundles:

```bash
python3 scripts/build_databricks_app.py
databricks bundle deploy -p <your-profile>
```

For this demo, use the `east-fe` profile and target. Unset Databricks environment variables inline so they do not override the profile host/token:

```bash
env -u DATABRICKS_HOST -u DATABRICKS_TOKEN -u DATABRICKS_AUTH_TYPE \
  databricks current-user me -p east-fe

env -u DATABRICKS_HOST -u DATABRICKS_TOKEN -u DATABRICKS_AUTH_TYPE \
  databricks bundle validate -t east-fe -p east-fe

env -u DATABRICKS_HOST -u DATABRICKS_TOKEN -u DATABRICKS_AUTH_TYPE \
  databricks bundle deploy -t east-fe -p east-fe
```

The generated `databricks.yml` includes a Lakebase database instance, Databricks App resource, and an `east-fe` target pointing to `https://adb-984752964297111.11.azuredatabricks.net`. Add serving/vector resources for a production-like workspace demo.

Note: the bundle uses `scripts/build_databricks_app.py` instead of `apx build` so deployment is not blocked by local PyPI/npm access. The fallback build packages the FastAPI backend and serves `ui-preview.html` as the frontend until the full React build can run.

## Production Gaps

This is a POC. Before production, add real PHI controls, redaction, retention policies, service principal hardening, Unity Catalog permissions, audit review, real telephony integration, true diarization for mixed audio, full Model Serving deployment automation for ASR, and MLflow evaluation/tracing.
