# Customer Demo Feedback Analysis

Date captured: 2026-05-27

Project: Carenet Next-Best-Action Call Center Assistant

## Purpose

This document captures feedback and discussion points from the customer demo, cleans up the repeated transcript fragments, and turns them into an actionable analysis for the next iteration of the Databricks call center assistant.

The raw comments included repeated partial ASR fragments. The cleaned notes below preserve the intent rather than every duplicate phrase.

## Cleaned Customer And Internal Comments

### 1. Requested Enhancements

The customer and internal team want the next version to be more curated and closer to real call center operations.

Requested capabilities:

- Speaker diarization: reliably separate the caller/patient voice from the human agent voice.
- Audio anonymization: anonymize or mask sensitive information from the audio and transcript.
- HIPAA and healthcare privacy posture: explain how sensitive patient data is protected.
- Cost estimation: explain how costs are calculated for this use case.
- Evidence of prior integrations: show examples or references where similar healthcare/contact-center integrations have been done.
- Deeper integrations: understand what is possible with Genesys/contact center systems and Epic/EHR systems.
- Scheduling workflow: demonstrate next-best-action moving from advice to an actual scheduling action.
- Human-agent coaching: show how transcript analysis can be used for monitoring, observability, QA, and coaching.

### 2. Cost Discussion

The customer asked how to calculate costs for this kind of use case.

Key points from the discussion:

- The assumption was that costs are mostly compute-based.
- There is no separate licensing cost for the components in the POC as framed, but actual cost depends on endpoint usage, model serving, vector search, app compute, storage, and operational workload.
- A POC is the best way to estimate cost by running representative call scenarios and measuring compute usage.
- The customer is interested in cost per call or cost per scenario.

### 3. Microsoft, Ad Astra, And Team Coordination

There have been conversations with Microsoft product teams, Brad, and the Ad Astra team around VoiceLive projects and scheduling automation.

Key points:

- The team wants to avoid disrupting parallel efforts.
- Everyone is aligned around helping CareNet.
- Next-best-action appears to be a separate lane that is not currently owned by those teams.
- Microsoft/Ad Astra conversations seem focused on cost per call, AI agent authentication, handoff to human agents, and scheduling automation.
- Databricks is being considered as part of the future state for observability, monitoring, transcript analysis, and human-agent coaching.

### 4. Contact Center And Scheduling Integration

There was a strong thread around how a call center assistant becomes operationally meaningful.

Discussion points:

- The call likely enters through a contact center platform such as Genesys.
- The assistant needs to pick up the live transcript or call stream in real time.
- The next-best-action workflow around scheduling only becomes meaningful if the assistant can read or interact with systems of record.
- Scheduling actions may require integration with Epic or other EHR/EMR systems.
- The system may need to authenticate the caller, identify the correct health system context, and hand off to the human agent with useful context.
- The team needs to understand whether Databricks has direct/native patterns for Genesys and Epic integration, or whether APIs and partner connectors are needed.

### 5. Epic / EHR Clarification

The discussion clarified what Epic means in this context.

Epic is an electronic health record system used by healthcare organizations. It can contain:

- Patient records
- Clinical notes
- Scheduling data
- Hospital and clinic workflows
- Different operational modules used by providers

The analogy used was:

- CRM is the system of record for customer/opportunity data.
- ERP is the system of record for financial and operational business processes.
- EHR/EMR is the healthcare system of record for patient care operations.
- Epic, Cerner, and Meditech are examples of major EHR/EMR systems.

For CareNet, the likely operating model is:

- A patient calls a CareNet-supported line.
- The call arrives through a contact center platform.
- The human agent may appear to the patient as a representative of a health system.
- CareNet may need to access or act against the health system's EHR, such as Epic.
- Next-best-action needs to account for the patient context, health system context, scheduling rules, and available appointments.

### 6. HIPAA, Masking, And Healthcare Expertise

The team noted that HIPAA and healthcare compliance questions need stronger support.

Specific concerns:

- Can Databricks be used in a HIPAA-sensitive workflow?
- How should protected health information be masked or redacted?
- Should the human agent see all information, partially masked information, or only structured guidance?
- How should the system handle audio anonymization versus transcript anonymization?
- Which internal healthcare experts should be brought in to validate the approach?

There was also a suggestion to reach out to healthcare account experts or AEs to identify the right internal resources.

### 7. Demo Readiness Feedback

The demo showed technical capability, but the customer expected answers that connected the demo to their operational context.

Observed gaps:

- Some questions were answered theoretically rather than through the app.
- The demo did not yet include real speaker diarization.
- The demo did not yet include audio anonymization or privacy masking.
- The demo did not show real Genesys/contact-center ingestion.
- The demo did not show real Epic/EHR scheduling integration.
- The cost model was not fully quantified.
- The workflow did not yet move from recommendation to action execution.

## Main Themes

### Theme 1: Move From Demo Assistant To Operational Workflow

The current POC demonstrates live transcription, recommendation generation, alerts, and citations. The customer is asking for the next level: a workflow that fits their actual call center environment.

That means the app should not only say "schedule a CT scan" or "escalate to nurse triage." It should also show how that action would be executed or prepared through integrations.

### Theme 2: Contact Center Context Is Critical

The customer is thinking in terms of Genesys/contact center operations:

- Where does the audio stream come from?
- Where does the call transcript come from?
- How does the agent desktop receive the recommendation?
- How does caller identity/authentication flow into the assistant?
- How does the assistant observe and analyze calls without disrupting the live agent workflow?

The next architecture should show Databricks as an intelligence and analytics layer that can consume real-time events/transcripts, enrich them, and produce recommendations or analytics.

### Theme 3: EHR Integration Determines Business Value

For scheduling use cases, the recommendation is only valuable if it can use real appointment and patient data.

The assistant needs a clear integration story for:

- Epic
- Cerner
- Meditech
- FHIR APIs
- HL7 interfaces
- Scheduling APIs
- Identity and consent boundaries

Without this, the demo remains a generic call assistant rather than a healthcare operations assistant.

### Theme 4: Privacy Must Be A First-Class Design Concern

The customer explicitly raised anonymization, masking, and HIPAA. This should not be treated as a later add-on.

The next design should include:

- Audio handling policy
- Transcript redaction
- PHI detection
- Storage controls
- Access controls
- Audit logging
- Retention policy
- Human-agent visibility rules
- Model prompt/data governance rules

### Theme 5: Cost Needs A Measurable Framework

The customer wants cost per call or cost per scenario. The answer should not stay at "it is compute."

The POC should emit enough metrics to estimate:

- App compute cost per hour
- ASR endpoint cost per audio minute
- LLM endpoint cost per recommendation
- Embedding endpoint cost per retrieval query
- Vector Search endpoint cost
- Storage cost for audio/transcripts
- Lakebase operational storage cost
- End-to-end cost per call
- Cost per 1,000 calls

## Current POC Versus Customer Expectations

### Current POC Capabilities

The current app demonstrates:

- Databricks App hosted UI and FastAPI backend.
- Browser microphone capture.
- Databricks-hosted ASR endpoint using `faster-whisper`.
- GPT-5.5 based recommendation generation.
- Vector Search based retrieval over a knowledge base.
- Alerts and citations in the UI.
- 15-second discussion summaries in the UI.
- Audio upload to Unity Catalog Volume.
- Lakebase persistence design and table models, although the current connection is not healthy.

### Current Gaps Against Feedback

| Area | Current State | Gap |
| --- | --- | --- |
| Speaker diarization | Manual speaker hint buttons and UI labels | Need automated diarization or integration with a diarized transcript source |
| Audio anonymization | Not implemented | Need audio and/or transcript PHI redaction strategy |
| HIPAA posture | Not fully documented | Need architecture, controls, and expert validation |
| Cost model | Not quantified in app | Need telemetry and cost-per-call model |
| Genesys integration | Not implemented | Need ingestion pattern and feasibility research |
| Epic/EHR integration | Not implemented | Need API/FHIR/scheduling integration design |
| Action execution | Recommendations only | Need action orchestration, approval, and system update flow |
| Agent coaching | Conceptual only | Need post-call analytics, QA metrics, and coaching workflow |
| Lakebase | Persistence code exists, connection failing | Need working operational store |

## Detailed Analysis

### 1. Speaker Diarization

#### Why It Matters

Speaker diarization is fundamental for contact center analysis. Without reliable speaker separation, the assistant may misunderstand who said what.

Examples:

- A patient saying "I have chest pain" should drive urgent escalation.
- An agent saying "Do you have chest pain?" should not be treated as the patient reporting chest pain.
- Coaching metrics require separating agent behavior from caller behavior.

#### Options

Option A: Contact center transcript diarization

- If Genesys or another contact center platform already produces speaker-labeled transcripts, use that as the primary source.
- This is often preferable for production because the contact center owns the media stream and agent/caller channels.

Option B: Channel-based diarization

- If caller and agent audio are available as separate channels, assign speaker labels by channel.
- This is more reliable than model-based diarization.

Option C: Model-based diarization

- Use a diarization model to split speakers from mixed audio.
- This is useful when only one mixed audio stream exists.
- It adds latency and complexity.

Option D: Manual speaker hinting

- Current POC uses manual speaker selection.
- Good for demos, not enough for production.

#### Recommendation

For the next customer-facing demo, show a diarization architecture even if full automation is not yet implemented:

- Short term: preserve manual speaker hint but label it as demo mode.
- Medium term: support two-channel audio or contact-center diarized transcript ingestion.
- Long term: add model-based diarization for mixed-channel recordings.

### 2. Audio Anonymization And PHI Masking

#### Why It Matters

Healthcare calls may contain PHI:

- Patient names
- Dates of birth
- Phone numbers
- Addresses
- Member IDs
- Medical record numbers
- Appointment details
- Diagnoses
- Medication names
- Provider names

The customer asked specifically about masking information so the human agent or downstream systems may not see unnecessary sensitive information.

#### Important Distinction

Audio anonymization and transcript anonymization are different.

Transcript anonymization:

- Detect PHI in text.
- Replace with placeholders such as `[PATIENT_NAME]`, `[DOB]`, `[PHONE]`.
- Easier to implement and audit.

Audio anonymization:

- Detect sensitive spans in time-aligned transcript.
- Redact or mute the matching audio regions.
- Harder because it requires word timestamps and audio post-processing.

#### Recommended POC Scope

For the next demo:

- Implement transcript redaction first.
- Show redaction in the UI.
- Store both raw and redacted versions only if governance allows it.
- Add an "agent-safe view" that shows masked PHI.
- Document future audio redaction as a post-call processing step.

#### Recommended Production Pattern

- Ingest audio.
- Transcribe with timestamps.
- Run PHI detection/redaction.
- Store raw audio in a restricted UC Volume.
- Store redacted transcript for broad operational analytics.
- Store PHI mapping only in a restricted table if reversible de-identification is required.
- Enforce access with Unity Catalog permissions.
- Log access and transformations.

### 3. Cost Model

#### Customer Question

The customer wants to know how cost is calculated and what the cost per call could be.

#### Cost Drivers

Primary cost drivers:

- Databricks App compute.
- ASR model serving compute.
- GPT-5.5 recommendation calls.
- Embedding endpoint calls.
- Vector Search endpoint.
- Lakebase instance.
- Unity Catalog Volume storage for audio.
- Storage for transcript, summaries, recommendations, alerts, citations, and audit logs.

#### POC Measurement Plan

Run representative scenarios and capture:

- Call duration.
- Number of audio chunks.
- ASR latency per chunk.
- ASR endpoint invocations per call.
- Number of recommendation generations per call.
- LLM latency and token usage if available.
- Number of embedding calls.
- Number of Vector Search queries.
- Audio bytes stored.
- Transcript bytes stored.
- App runtime duration.

#### Output Metrics To Provide

The next demo should show:

- Estimated cost per 5-minute call.
- Estimated cost per 15-minute call.
- Estimated cost per 1,000 calls.
- Breakdown by ASR, LLM, retrieval, app runtime, and storage.
- Sensitivity analysis for recommendation cadence, chunk size, and model choice.

### 4. Genesys / Contact Center Integration

#### Customer Need

The assistant should fit the real contact center environment, likely Genesys.

#### Integration Questions

Key questions to research:

- Does Genesys expose live audio streams, live transcripts, or both?
- Can Databricks receive events directly, or should there be an intermediate event bus?
- Can the agent desktop embed a Databricks App or call an API?
- How does caller authentication flow into the assistant?
- How are call IDs, agent IDs, queue IDs, and patient IDs represented?
- What are the latency requirements for real-time next-best-action?

#### Recommended Architecture Pattern

Genesys should be treated as the real-time call/event source.

Potential flow:

1. Patient calls CareNet.
2. Genesys handles telephony, routing, and agent desktop.
3. Genesys emits audio, transcript, or call events.
4. A streaming/API bridge sends events to Databricks.
5. Databricks App/backend enriches transcript and generates recommendations.
6. Recommendations are returned to the agent desktop or supervisor dashboard.
7. Post-call transcripts and analytics land in Lakehouse/Lakebase.

### 5. Epic / EHR Integration

#### Customer Need

Scheduling next-best-action requires access to appointment availability and patient context.

#### Integration Options

Option A: FHIR APIs

- Use FHIR resources for patient, appointment, practitioner, schedule, slot, encounter, and observation.
- Best if the health system exposes FHIR endpoints.

Option B: Epic APIs

- Use Epic-specific APIs for scheduling and patient lookup.
- Requires customer-specific access and credentials.

Option C: Middleware / integration engine

- Use an existing integration layer that already connects to Epic.
- Often more realistic in healthcare organizations.

Option D: Mock scheduling service for demo

- For the next demo, create a mock Epic scheduling API.
- Show the orchestration pattern without needing real Epic access.

#### Recommended Next Demo Scope

Implement a mock scheduling action:

- Patient says: "I need to schedule a CT scan."
- Assistant identifies scheduling intent.
- Assistant checks mock appointment availability.
- Assistant recommends available time slots.
- Human agent approves.
- System creates a mock appointment.
- UI shows "Action prepared" or "Appointment scheduled."

This demonstrates the operating model while avoiding real EHR integration complexity.

### 6. Next-Best-Action Evolution

Current next-best-action is advisory. The customer is asking about operational next-best-action.

#### Advisory NBA

Examples:

- "Escalate to nurse triage."
- "Offer telehealth appointment."
- "Confirm medication instructions."

#### Operational NBA

Examples:

- "Open scheduling workflow."
- "Fetch available CT scan slots."
- "Prepare Epic appointment creation."
- "Route caller to nurse line."
- "Create post-call follow-up task."

#### Recommended Design

Add an action layer:

- Intent detection.
- Policy/rule check.
- Required system lookup.
- Human approval.
- Action execution.
- Audit log.
- Rollback/error handling.

The human should stay in control for healthcare actions unless the customer explicitly wants automation.

### 7. Agent Coaching And Observability

The customer sees Databricks fitting into observability, transcript analysis, and human-agent coaching.

Potential metrics:

- Did the agent verify identity?
- Did the agent show empathy?
- Did the agent follow escalation policy?
- Did the agent offer correct scheduling options?
- Was PHI handled correctly?
- Did the agent resolve the call?
- Was there avoidable hold time?
- What was the call sentiment?
- What knowledge article was cited?
- What next-best-action was shown, accepted, ignored, or overridden?

Databricks is well positioned here because the Lakehouse can combine:

- Audio metadata
- Transcripts
- Recommendations
- Agent actions
- Feedback
- Operational outcomes
- Quality scores
- Cost metrics

## Recommended Follow-Up Demo Narrative

### Demo Story

Patient calls CareNet to schedule a CT scan after a referral.

Flow:

1. Genesys-like call event starts the session.
2. Audio/transcript streams into the assistant.
3. Speaker diarization separates patient and agent.
4. PHI redaction masks patient details in the transcript view.
5. Assistant detects scheduling intent.
6. Assistant retrieves scheduling policy and clinical workflow guidance from Vector Search.
7. Assistant calls mock Epic scheduling API.
8. Assistant shows available appointment options.
9. Human agent approves one option.
10. Assistant records the action, recommendation, transcript, and audit trail.
11. Supervisor dashboard shows call metrics and coaching signals.
12. Cost panel estimates cost per call.

### What To Show In The App

Add or improve these UI sections:

- Speaker-separated transcript with confidence.
- PHI redaction toggle: raw vs masked transcript, if authorized.
- Cost estimate panel.
- Integration status panel: ASR, LLM, Vector Search, Lakebase, Genesys mock, Epic mock.
- Action card: "Schedule CT scan" with available slots.
- Human approval buttons: approve, modify, reject.
- Post-call coaching summary.

## Recommended Roadmap

### Phase 1: Strengthen Current POC

- Fix Lakebase connection.
- Add transcript PHI redaction.
- Add cost telemetry counters.
- Add visible runtime status for ASR, LLM, Vector Search, Lakebase.
- Improve speaker diarization story with clear demo-mode labeling.

### Phase 2: Add Healthcare Workflow Simulation

- Add mock Genesys event ingestion.
- Add mock Epic scheduling API.
- Add scheduling next-best-action workflow.
- Add human approval and action audit.
- Add post-call summary persisted to Lakebase.

### Phase 3: Prepare For Customer-Specific Integration

- Research Genesys integration options.
- Research Epic/FHIR scheduling integration options.
- Identify Databricks healthcare compliance experts.
- Define HIPAA deployment architecture.
- Define data retention and access-control model.
- Define production cost model.

### Phase 4: Production Architecture

- Replace browser mic capture with contact-center audio/transcript feed.
- Use contact-center diarization or channel-based speaker labels.
- Persist all operational data in Lakebase/Lakehouse.
- Use Unity Catalog for governance and access control.
- Add monitoring, evaluation, and human-agent coaching dashboards.
- Add customer-specific EHR integration through approved APIs.

## Key Questions To Answer Before The Next Customer Meeting

### Genesys / Contact Center

- What contact center platform does CareNet use for the target workflow?
- Can it provide real-time audio streams?
- Can it provide real-time transcripts?
- Does it provide speaker labels?
- Can recommendations be embedded into the agent desktop?
- What identity and call metadata are available?

### Epic / EHR

- Which EHR systems are in scope: Epic, Cerner, Meditech, or others?
- Is scheduling available through FHIR APIs?
- Is there an existing integration engine or middleware?
- Who owns credentials and access approval?
- What actions can be automated versus only recommended?

### Compliance

- What PHI can be sent to Databricks?
- What must be masked from the human agent?
- Is raw audio allowed to be stored?
- What retention policy applies?
- Who can access raw transcript versus redacted transcript?
- Is a BAA or HIPAA-specific deployment control required?

### Cost

- What is the target call volume?
- What is the target average call duration?
- How many recommendations per call are acceptable?
- Is real-time ASR required for every call or only selected calls?
- What latency target is required for next-best-action?

## Suggested Response Back To Customer

We heard four major asks from the demo:

1. Make the assistant more operational by connecting next-best-action to scheduling workflows.
2. Show a clear integration path for Genesys/contact center and Epic/EHR systems.
3. Treat privacy, masking, anonymization, and HIPAA as first-class architecture concerns.
4. Provide a measurable cost model, ideally cost per call and cost per scenario.

For the next iteration, we should come back with a more curated demo that shows a healthcare scheduling journey end to end: diarized transcript, PHI-masked view, retrieved policy guidance, mock Epic scheduling lookup, human approval, action audit, and post-call coaching analytics.

## Immediate Action Items

| Priority | Action | Owner Type | Outcome |
| --- | --- | --- | --- |
| High | Fix Lakebase connection | Engineering | Persist call artifacts and audit trail |
| High | Add PHI redaction to transcript | Engineering / Healthcare SME | Show privacy-aware transcript |
| High | Research Genesys integration options | Engineering / Partner SME | Real-time ingestion path |
| High | Research Epic/FHIR scheduling options | Engineering / Healthcare SME | Scheduling action design |
| Medium | Add cost telemetry and cost panel | Engineering | Cost per call estimate |
| Medium | Add mock scheduling workflow | Engineering | Operational next-best-action demo |
| Medium | Add post-call coaching summary | Engineering / Product | Supervisor/QA value story |
| Medium | Identify healthcare compliance experts | Account team | HIPAA and privacy guidance |

## Bottom Line

The customer is not only asking whether Databricks can transcribe and recommend. They are asking how Databricks fits into a real healthcare call center operating model.

The next demo should therefore shift from "AI assistant prototype" to "healthcare call center workflow platform":

- Real-time call understanding
- Speaker-aware transcript
- PHI-aware data handling
- Retrieval-grounded next-best-action
- Scheduling action orchestration
- Human approval
- Audit and observability
- Cost-per-call measurement
- Post-call coaching and analytics

