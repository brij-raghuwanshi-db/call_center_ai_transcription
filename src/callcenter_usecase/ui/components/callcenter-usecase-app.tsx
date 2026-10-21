import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, BarChart3, Mic, Play, Square, Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type RiskLevel = "low" | "medium" | "high" | "critical";
type FeedbackType = "helpful" | "not_helpful" | "wrong" | "used" | "ignored";

type Scenario = {
  id: string;
  title: string;
  description: string;
  patient_name: string;
  intent: string;
  expected_risk_level: RiskLevel;
};

type ActiveCall = {
  call_id: string;
  status: string;
  scenario_id: string;
  scenario_title: string;
  patient_name: string;
  latest_transcript: string;
  latest_intent: string;
  current_risk_level: RiskLevel;
  current_recommendation_id?: string;
  summary_draft: string;
};

type TranscriptSegment = {
  segment_id: string;
  call_id: string;
  speaker: "Agent" | "Patient" | "Unknown";
  text: string;
  is_partial: boolean;
  start_ms: number;
  end_ms: number;
  asr_latency_ms: number;
  confidence: number;
};

type Citation = {
  document_id: string;
  title: string;
  section: string;
  quote: string;
  score: number;
};

type Recommendation = {
  recommendation_id: string;
  call_id: string;
  intent: string;
  topic: string;
  patient_state: string;
  risk_level: RiskLevel;
  urgency_level: RiskLevel;
  recommended_response: string;
  next_best_action: string;
  action_rationale: string;
  confidence: number;
  citations: Citation[];
  alerts: Array<{ code: string; title: string; detail: string; risk_level: RiskLevel }>;
  compliance_notes: string[];
  summary_update: string;
  structured_slots: Record<string, unknown>;
  should_escalate: boolean;
  escalation_reason?: string;
  llm_latency_ms: number;
};

type Metrics = {
  active_calls: number;
  total_calls: number;
  transcript_segments: number;
  recommendations: number;
  feedback_items: number;
  avg_asr_latency_ms: number;
  avg_llm_latency_ms: number;
};

const API = "/api";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (response.status === 204) {
    return undefined as T;
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

const TARGET_SAMPLE_RATE = 16000;
const SLICE_SECONDS = 3.6;
const OVERLAP_SECONDS = 1.2;
const SILENCE_RMS = 0.005;
const MAX_PENDING_SLICES = 8;

function downsample(input: Float32Array, inRate: number, outRate: number): Float32Array {
  if (inRate === outRate) return input;
  const ratio = inRate / outRate;
  const outLen = Math.max(1, Math.floor(input.length / ratio));
  const output = new Float32Array(outLen);
  for (let index = 0; index < outLen; index += 1) {
    const position = index * ratio;
    const left = Math.min(Math.floor(position), input.length - 1);
    const right = Math.min(left + 1, input.length - 1);
    const fraction = position - left;
    output[index] = input[left] * (1 - fraction) + input[right] * fraction;
  }
  return output;
}

function concatFloat32(chunks: Float32Array[]): Float32Array {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const output = new Float32Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.length;
  }
  return output;
}

function rms(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let index = 0; index < samples.length; index += 1) {
    sum += samples[index] * samples[index];
  }
  return Math.sqrt(sum / samples.length);
}

function encodeWavPcm16(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeString = (offset: number, value: string) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);
  let offset = 44;
  for (let index = 0; index < samples.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += 2;
  }
  return new Blob([buffer], { type: "audio/wav" });
}

function riskBadgeVariant(risk: RiskLevel): "default" | "secondary" | "destructive" | "outline" {
  if (risk === "high" || risk === "critical") return "destructive";
  if (risk === "medium") return "default";
  return "secondary";
}

function formatMs(ms: number) {
  return `${Math.round(ms)} ms`;
}

export default function CallCenterUseCaseApp() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenarioId, setScenarioId] = useState("symptom_escalation");
  const [speakerHint, setSpeakerHint] = useState<"Patient" | "Agent">("Patient");
  const [call, setCall] = useState<ActiveCall | null>(null);
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [activeCalls, setActiveCalls] = useState<ActiveCall[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [autoRecommend, setAutoRecommend] = useState(true);
  const [cadenceMode, setCadenceMode] = useState<"every_few_seconds" | "completed_sentence">("every_few_seconds");
  const [redactionEnabled, setRedactionEnabled] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState("Ready to start a Call Center demo call.");
  const speakerHintRef = useRef(speakerHint);
  const callIdRef = useRef<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const captureNodesRef = useRef<AudioNode[]>([]);
  const pcmRef = useRef<Float32Array[]>([]);
  const nativeRateRef = useRef(48000);
  const sendingRef = useRef(false);
  const pendingWavRef = useRef<Blob[]>([]);
  const stoppingRef = useRef(false);
  const stoppedCallIdsRef = useRef<Set<string>>(new Set());

  const currentScenario = useMemo(
    () => scenarios.find((scenario) => scenario.id === scenarioId),
    [scenarioId, scenarios],
  );
  const groupedTranscript = useMemo(() => {
    return transcript.reduce<TranscriptSegment[]>((groups, segment) => {
      const previous = groups.at(-1);
      if (previous?.speaker === segment.speaker) {
        previous.text = `${previous.text} ${segment.text}`.trim();
        previous.end_ms = segment.end_ms;
        previous.asr_latency_ms = segment.asr_latency_ms;
        previous.confidence = segment.confidence;
        return groups;
      }
      groups.push({ ...segment });
      return groups;
    }, []);
  }, [transcript]);

  useEffect(() => {
    void refreshBootstrap();
  }, []);

  useEffect(() => {
    speakerHintRef.current = speakerHint;
  }, [speakerHint]);

  useEffect(() => {
    callIdRef.current = call?.call_id ?? null;
  }, [call?.call_id]);

  useEffect(() => {
    if (!call) return;
    const timer = window.setInterval(() => {
      void refreshCall(call.call_id);
      void refreshSupervisor();
    }, 1500);
    return () => window.clearInterval(timer);
  }, [call?.call_id]);

  async function refreshBootstrap() {
    const [scenarioData, metricData] = await Promise.all([
      api<Scenario[]>("/scenarios"),
      api<Metrics>("/metrics/demo"),
    ]);
    setScenarios(scenarioData);
    setMetrics(metricData);
  }

  async function refreshSupervisor() {
    const [calls, metricData] = await Promise.all([
      api<ActiveCall[]>("/calls/active"),
      api<Metrics>("/metrics/demo"),
    ]);
    setActiveCalls(calls);
    setMetrics(metricData);
  }

  async function refreshCall(callId: string) {
    try {
      const [callData, transcriptData, latestRecommendation] = await Promise.all([
        api<ActiveCall>(`/calls/${callId}`),
        api<TranscriptSegment[]>(`/calls/${callId}/transcript`),
        api<Recommendation | null>(`/recommendations/latest/${callId}`),
      ]);
      setTranscript(transcriptData);
      setRecommendation(latestRecommendation);
      if (stoppedCallIdsRef.current.has(callId) || stoppingRef.current) {
        setIsRunning(false);
        if (callData.status !== "active") {
          setCall(callData);
        }
        return;
      }
      setCall(callData);
      setIsRunning(callData.status === "active");
    } catch {
      // Keep the current on-screen call if a poll fails mid-demo.
    }
  }

  async function startCall() {
    stoppingRef.current = false;
    try {
      const result = await api<{ call: ActiveCall; transcript: TranscriptSegment[]; recommendation: Recommendation | null }>("/calls/start", {
        method: "POST",
        body: JSON.stringify({
          scenario_id: scenarioId,
          settings: {
            auto_recommendations_enabled: autoRecommend,
            cadence_mode: cadenceMode,
            redaction_enabled: redactionEnabled,
            demo_mode: "synthetic",
          },
        }),
      });
      setCall(result.call);
      setTranscript(result.transcript);
      setRecommendation(result.recommendation);
      setIsRunning(true);
      setStatus(`Started ${result.call.scenario_title} call for ${result.call.patient_name}.`);
      await refreshSupervisor();
    } catch (error) {
      setIsRunning(false);
      setStatus(error instanceof Error ? error.message : "Failed to start call.");
    }
  }

  async function stopCall() {
    if (!call) return;
    stoppingRef.current = true;
    stoppedCallIdsRef.current.add(call.call_id);
    stopMicrophone();
    setIsRunning(false);
    setCall({ ...call, status: "ended" });
    setStatus("Call stopped.");
    try {
      const stopped = await api<ActiveCall>(`/calls/${call.call_id}/stop`, { method: "POST" });
      setCall(stopped);
      setStatus("Call stopped. Replay and audit events remain available.");
      await refreshSupervisor();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Call stopped locally, but the server stop failed.");
    } finally {
      stoppingRef.current = false;
    }
  }

  async function forceAnalyze() {
    if (!call) return;
    const rec = await api<Recommendation>("/recommendations/analyze", {
      method: "POST",
      body: JSON.stringify({ call_id: call.call_id, trigger_segment_id: transcript.at(-1)?.segment_id }),
    });
    setRecommendation(rec);
    setStatus("Generated manual next-best-action recommendation.");
    await refreshSupervisor();
  }

  async function submitFeedback(feedbackType: FeedbackType) {
    if (!recommendation) return;
    await api(`/recommendations/${recommendation.recommendation_id}/feedback`, {
      method: "POST",
      body: JSON.stringify({ feedback_type: feedbackType }),
    });
    setStatus(`Stored feedback: ${feedbackType.replace("_", " ")}.`);
    await refreshSupervisor();
  }

  async function uploadAudio(file?: File) {
    if (!call || !file) return;
    const form = new FormData();
    form.append("file", file);
    await api(`/audio/upload/${call.call_id}`, { method: "POST", body: form });
    try {
      const base64 = await blobToBase64(file);
      const segment = await api<TranscriptSegment | undefined>("/audio/chunk", {
        method: "POST",
        body: JSON.stringify({
          call_id: call.call_id,
          audio_base64: base64,
          speaker_hint: speakerHintRef.current,
          sample_rate: 16000,
          cumulative_audio: true,
        }),
      });
      setStatus(
        segment?.text
          ? `Uploaded and transcribed ${file.name}.`
          : `Uploaded ${file.name}. Whisper did not return new transcript text.`,
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : `Uploaded ${file.name}, but transcription failed.`);
    }
    await refreshCall(call.call_id);
  }

  function stopMicrophone() {
    try {
      flushRemainingPcm();
    } catch {
      pcmRef.current = [];
    }
    captureNodesRef.current.forEach((node) => {
      try {
        node.disconnect();
      } catch {
        // already disconnected
      }
    });
    captureNodesRef.current = [];
    void audioContextRef.current?.close();
    audioContextRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setIsRecording(false);
  }

  function flushRemainingPcm() {
    const nativeRate = nativeRateRef.current || TARGET_SAMPLE_RATE;
    const joined = concatFloat32(pcmRef.current);
    pcmRef.current = [];
    if (joined.length < Math.floor(0.6 * nativeRate)) return;
    queueWavFromPcm(new Float32Array(joined), nativeRate);
  }

  function queueWavFromPcm(slice: Float32Array, nativeRate: number) {
    queueMicrotask(() => {
      const wavSamples = downsample(slice, nativeRate, TARGET_SAMPLE_RATE);
      if (rms(wavSamples) < SILENCE_RMS) return;
      enqueueWavSlice(encodeWavPcm16(wavSamples, TARGET_SAMPLE_RATE));
    });
  }

  function enqueuePcm(frame: Float32Array) {
    pcmRef.current.push(frame);
    const nativeRate = nativeRateRef.current || TARGET_SAMPLE_RATE;
    const needed = Math.floor(SLICE_SECONDS * nativeRate);
    const overlap = Math.floor(OVERLAP_SECONDS * nativeRate);
    let joined = concatFloat32(pcmRef.current);
    while (joined.length >= needed) {
      const slice = new Float32Array(joined.subarray(0, needed));
      joined = joined.subarray(Math.max(0, needed - overlap));
      queueWavFromPcm(slice, nativeRate);
    }
    pcmRef.current = joined.length ? [new Float32Array(joined)] : [];
  }

  function enqueueWavSlice(blob: Blob) {
    if (stoppingRef.current) return;
    const queue = pendingWavRef.current;
    queue.push(blob);
    if (queue.length > MAX_PENDING_SLICES) {
      queue.shift();
      setStatus("Whisper is catching up; kept the latest audio slices.");
    }
    void drainWavQueue();
  }

  async function drainWavQueue() {
    if (sendingRef.current) return;
    sendingRef.current = true;
    try {
      while (pendingWavRef.current.length > 0) {
        if (stoppingRef.current) {
          pendingWavRef.current = [];
          break;
        }
        const current = pendingWavRef.current.shift();
        if (!current) break;
        const callId = callIdRef.current;
        if (!callId) continue;
        const base64 = await blobToBase64(current);
        const segment = await api<TranscriptSegment | undefined>("/audio/chunk", {
          method: "POST",
          body: JSON.stringify({
            call_id: callId,
            audio_base64: base64,
            speaker_hint: speakerHintRef.current,
            sample_rate: TARGET_SAMPLE_RATE,
            mime_type: "audio/wav",
            filename: "chunk.wav",
            cumulative_audio: false,
          }),
        });
        if (segment?.text) {
          setTranscript((previous) => [...previous, segment]);
          setStatus(`Transcribed: ${segment.text}`);
          void refreshCall(callId);
        }
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Microphone transcription failed.");
    } finally {
      sendingRef.current = false;
      if (pendingWavRef.current.length > 0 && !stoppingRef.current) {
        void drainWavQueue();
      }
    }
  }

  async function toggleMic() {
    if (!call || call.status === "ended") return;
    if (isRecording) {
      stopMicrophone();
      setStatus("Microphone recording stopped.");
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: false,
        autoGainControl: true,
        channelCount: 1,
      },
    });
    const AudioContextCtor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextCtor) {
      setStatus("This browser does not support AudioContext capture.");
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    let context: AudioContext;
    try {
      context = new AudioContextCtor({ sampleRate: TARGET_SAMPLE_RATE });
    } catch {
      context = new AudioContextCtor();
    }
    await context.resume();
    nativeRateRef.current = context.sampleRate || 48000;
    pcmRef.current = [];
    pendingWavRef.current = [];
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (event) => {
      enqueuePcm(new Float32Array(event.inputBuffer.getChannelData(0)));
    };
    const silent = context.createGain();
    silent.gain.value = 0;
    source.connect(processor);
    processor.connect(silent);
    silent.connect(context.destination);
    audioContextRef.current = context;
    streamRef.current = stream;
    captureNodesRef.current = [source, processor, silent];
    setIsRecording(true);
    setStatus("Microphone streaming overlapping 3.6-second WAV slices to Whisper.");
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b px-6 py-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold">Call Center Use Case</h1>
            <p className="text-sm text-muted-foreground">
              Databricks-native live call assistant for patient retention, triage, and next-best actions.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={isRunning ? "default" : "secondary"}>{isRunning ? "Call active" : "Ready"}</Badge>
            <Badge variant="outline">GPT 5.5 via env</Badge>
            <Badge variant="outline">ASR Model Serving</Badge>
            <Badge variant="outline">Lakebase + Delta</Badge>
          </div>
        </div>
      </header>

      <main className="grid gap-4 p-4 xl:grid-cols-[360px_minmax(0,1fr)_380px]">
        <section className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Demo Call Controls</CardTitle>
              <CardDescription>Use generated healthcare audio, upload a WAV, or test microphone chunks.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <label className="space-y-2 text-sm font-medium">
                Scenario
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={scenarioId}
                  onChange={(event) => setScenarioId(event.target.value)}
                  disabled={isRunning}
                >
                  {scenarios.map((scenario) => (
                    <option key={scenario.id} value={scenario.id}>{scenario.title}</option>
                  ))}
                </select>
              </label>
              {currentScenario && (
                <p className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
                  {currentScenario.description}
                </p>
              )}
              <div className="grid grid-cols-2 gap-2">
                <Button onClick={() => void startCall()} disabled={isRunning}>
                  <Play className="h-4 w-4" /> Start
                </Button>
                <Button
                  variant="outline"
                  onClick={() => void stopCall()}
                  disabled={!call || (call.status !== "active" && !isRunning && !isRecording)}
                >
                  <Square className="h-4 w-4" /> Stop
                </Button>
              </div>
              <Button
                variant={isRecording ? "destructive" : "outline"}
                className="w-full"
                onClick={() => void toggleMic()}
                disabled={!call || call.status === "ended"}
              >
                <Mic className="h-4 w-4" /> {isRecording ? "Stop mic" : "Start mic"}
              </Button>
              <div>
                <span className="mb-2 block text-sm font-medium">Current speaker</span>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    type="button"
                    variant={speakerHint === "Patient" ? "default" : "outline"}
                    disabled={!call}
                    onClick={() => setSpeakerHint("Patient")}
                  >
                    Patient
                  </Button>
                  <Button
                    type="button"
                    variant={speakerHint === "Agent" ? "default" : "outline"}
                    disabled={!call}
                    onClick={() => setSpeakerHint("Agent")}
                  >
                    Agent
                  </Button>
                </div>
                <span className="mt-1 block text-xs text-muted-foreground">
                  For the mono mic demo, choose the speaker or say "agent speaking" / "patient speaking".
                </span>
              </div>
              <label className="block">
                <span className="mb-2 flex items-center gap-2 text-sm font-medium"><Upload className="h-4 w-4" /> Upload WAV</span>
                <Input type="file" accept="audio/wav,audio/*" disabled={!call} onChange={(event) => void uploadAudio(event.target.files?.[0])} />
              </label>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Live Toggles</CardTitle>
              <CardDescription>These settings are stored with the call state.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <ToggleRow label="Automatic recommendations" checked={autoRecommend} onChange={setAutoRecommend} />
              <ToggleRow label="Future redaction switch" checked={redactionEnabled} onChange={setRedactionEnabled} />
              <label className="space-y-2 font-medium">
                Recommendation cadence
                <select className="w-full rounded-md border bg-background px-3 py-2 text-sm" value={cadenceMode} onChange={(event) => setCadenceMode(event.target.value as typeof cadenceMode)}>
                  <option value="every_few_seconds">Every few seconds</option>
                  <option value="completed_sentence">Every completed sentence</option>
                </select>
              </label>
            </CardContent>
          </Card>

          <StatusCard status={status} />
        </section>

        <section className="space-y-4">
          <Card>
            <CardHeader className="flex-row items-start justify-between gap-4">
              <div>
                <CardTitle>Running Transcript</CardTitle>
                <CardDescription>Partial/final speaker-labeled transcript stream.</CardDescription>
              </div>
              {call && <Badge variant={riskBadgeVariant(call.current_risk_level)}>{call.current_risk_level}</Badge>}
            </CardHeader>
            <CardContent className="space-y-3">
              {groupedTranscript.length === 0 ? (
                <p className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
                  Start a call and process a segment to populate the transcript.
                </p>
              ) : (
                groupedTranscript.map((segment) => (
                  <div key={segment.segment_id} className="rounded-lg border p-3">
                    <div className="mb-1 flex items-center justify-between">
                      <Badge variant={segment.speaker === "Patient" ? "default" : "secondary"}>{segment.speaker}</Badge>
                      <span className="text-xs text-muted-foreground">ASR {formatMs(segment.asr_latency_ms)} · confidence {Math.round(segment.confidence * 100)}%</span>
                    </div>
                    <p className="text-sm leading-6">{segment.text}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Next-Best Action</CardTitle>
              <CardDescription>Strict JSON-style recommendation from the reasoning layer.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {recommendation ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant={riskBadgeVariant(recommendation.risk_level)}>Risk: {recommendation.risk_level}</Badge>
                    <Badge variant="outline">Intent: {recommendation.intent}</Badge>
                    <Badge variant="outline">Confidence {Math.round(recommendation.confidence * 100)}%</Badge>
                    <Badge variant="outline">Source: {String(recommendation.structured_slots?.model_source ?? "unknown")}</Badge>
                    {recommendation.should_escalate && <Badge variant="destructive">Escalate</Badge>}
                  </div>
                  <Panel title="Reasoning endpoint" body={String(recommendation.structured_slots?.llm_endpoint ?? "not configured")} />
                  <Panel title="Suggested response" body={recommendation.recommended_response} />
                  <Panel title="Next-best action" body={recommendation.next_best_action} />
                  <Panel title="Rationale" body={recommendation.action_rationale} />
                  <div className="flex flex-wrap gap-2">
                    {(["helpful", "not_helpful", "wrong", "used", "ignored"] as FeedbackType[]).map((type) => (
                      <Button key={type} size="sm" variant="outline" onClick={() => void submitFeedback(type)}>
                        {type.replace("_", " ")}
                      </Button>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No recommendation yet.</p>
              )}
              <Button variant="secondary" onClick={forceAnalyze} disabled={!call}>
                Analyze now
              </Button>
            </CardContent>
          </Card>
        </section>

        <section className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Alerts and Citations</CardTitle>
              <CardDescription>Deterministic rules plus Databricks Vector Search evidence.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {recommendation?.alerts.map((alert) => (
                <div key={alert.code} className="rounded-lg border p-3">
                  <div className="mb-1 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    <span className="font-medium">{alert.title}</span>
                    <Badge variant={riskBadgeVariant(alert.risk_level)}>{alert.risk_level}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{alert.detail}</p>
                </div>
              )) || <p className="text-sm text-muted-foreground">Alerts appear after analysis.</p>}
              {recommendation?.citations.map((citation) => (
                <div key={citation.document_id} className="rounded-lg bg-muted/40 p-3">
                  <p className="text-sm font-medium">{citation.title} · {citation.section}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{citation.quote}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Customer Profile and Summary</CardTitle>
              <CardDescription>Synthetic patient context for the demo.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <span className="text-muted-foreground">Patient</span>
                <span className="font-medium">{call?.patient_name || currentScenario?.patient_name || "Not started"}</span>
                <span className="text-muted-foreground">Scenario</span>
                <span className="font-medium">{call?.scenario_title || currentScenario?.title || "None"}</span>
                <span className="text-muted-foreground">Intent</span>
                <span className="font-medium">{call?.latest_intent || currentScenario?.intent || "unknown"}</span>
              </div>
              <div className="rounded-md border p-3">
                {call?.summary_draft || "Summary draft appears as the call progresses."}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Supervisor Dashboard</CardTitle>
              <CardDescription>Active calls and meta-evaluation metrics.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <Metric label="Active calls" value={metrics?.active_calls ?? 0} />
                <Metric label="Recommendations" value={metrics?.recommendations ?? 0} />
                <Metric label="Feedback" value={metrics?.feedback_items ?? 0} />
                <Metric label="Avg latency" value={`${metrics?.avg_asr_latency_ms ?? 0}/${metrics?.avg_llm_latency_ms ?? 0} ms`} />
              </div>
              <div className="space-y-2">
                {activeCalls.map((active) => (
                  <div key={active.call_id} className="rounded-lg border p-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{active.patient_name}</span>
                      <Badge variant={riskBadgeVariant(active.current_risk_level)}>{active.current_risk_level}</Badge>
                    </div>
                    <p className="mt-1 text-muted-foreground">{active.scenario_title}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}

function ToggleRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center justify-between rounded-md border p-3">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
    </label>
  );
}

function StatusCard({ status }: { status: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Activity className="h-4 w-4" /> Status</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{status}</p>
      </CardContent>
    </Card>
  );
}

function Panel({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border p-3">
      <p className="mb-1 text-sm font-medium">{title}</p>
      <p className="text-sm leading-6 text-muted-foreground">{body}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground"><BarChart3 className="h-3 w-3" /> {label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(String(reader.result).split(",", 2)[1] || "");
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
