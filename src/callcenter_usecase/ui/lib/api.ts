import { useQuery, useSuspenseQuery, useMutation } from "@tanstack/react-query";
import type { UseQueryOptions, UseSuspenseQueryOptions, UseMutationOptions } from "@tanstack/react-query";
export class ApiError extends Error {
    status: number;
    statusText: string;
    body: unknown;
    constructor(status: number, statusText: string, body: unknown){
        super(`HTTP ${status}: ${statusText}`);
        this.name = "ApiError";
        this.status = status;
        this.statusText = statusText;
        this.body = body;
    }
}
export interface ActiveCall {
    call_id: string;
    current_recommendation_id?: string | null;
    current_risk_level?: RiskLevel;
    current_speaker?: Speaker;
    ended_at?: string | null;
    latest_intent?: string;
    latest_transcript?: string;
    patient_name: string;
    scenario_id: string;
    scenario_title: string;
    settings?: CallSettings;
    started_at?: string;
    status?: CallStatus;
    summary_draft?: string;
}
export interface AgentFeedback {
    call_id: string;
    created_at?: string;
    created_by?: string;
    feedback_id?: string;
    feedback_type: FeedbackType;
    free_text?: string | null;
    recommendation_id: string;
}
export interface Alert {
    code: string;
    detail: string;
    risk_level?: RiskLevel;
    title: string;
}
export interface AnalyzeIn {
    call_id: string;
    transcript_window?: string | null;
    trigger_segment_id?: string | null;
}
export interface AppConfigOut {
    app_name: string;
    asr_endpoint_name: string;
    delta_schema_name: string;
    enable_acoustic_features: boolean;
    enable_redaction: boolean;
    llm_endpoint_name: string;
    uc_catalog: string;
    uc_schema: string;
    use_databricks_asr: boolean;
    use_mock_asr: boolean;
    use_mock_llm: boolean;
    use_scripted_transcript_fallback: boolean;
    vector_search_endpoint_name: string;
    vector_search_index_name: string;
}
export interface AudioChunkIn {
    audio_base64?: string | null;
    call_id: string;
    chunk_id?: string;
    cumulative_audio?: boolean;
    filename?: string | null;
    language?: string;
    mime_type?: string | null;
    sample_rate?: number;
    speaker_hint?: Speaker | null;
    transcript_text?: string | null;
}
export interface AudioUploadOut {
    bytes_received: number;
    call_id: string;
    filename: string;
    message: string;
    storage_path?: string | null;
}
export interface Body_uploadAudio {
    file: string;
}
export const CadenceMode = {
    every_few_seconds: "every_few_seconds",
    completed_sentence: "completed_sentence"
} as const;
export type CadenceMode = typeof CadenceMode[keyof typeof CadenceMode];
export interface CallSettings {
    auto_recommendations_enabled?: boolean;
    cadence_mode?: CadenceMode;
    demo_mode?: DemoMode;
    redaction_enabled?: boolean;
}
export const CallStatus = {
    ready: "ready",
    active: "active",
    ended: "ended"
} as const;
export type CallStatus = typeof CallStatus[keyof typeof CallStatus];
export interface Citation {
    document_id: string;
    quote: string;
    score?: number;
    section: string;
    title: string;
}
export interface ComplexValue {
    display?: string | null;
    primary?: boolean | null;
    ref?: string | null;
    type?: string | null;
    value?: string | null;
}
export interface DemoMetrics {
    active_calls: number;
    avg_asr_latency_ms: number;
    avg_llm_latency_ms: number;
    feedback_items: number;
    recommendations: number;
    total_calls: number;
    transcript_segments: number;
}
export const DemoMode = {
    synthetic: "synthetic",
    upload: "upload",
    microphone: "microphone",
    replay: "replay"
} as const;
export type DemoMode = typeof DemoMode[keyof typeof DemoMode];
export interface EvaluationExample {
    expected_escalation: boolean;
    expected_intent: string;
    expected_next_best_action: string;
    expected_risk_level: RiskLevel;
    scenario_id: string;
}
export interface FeedbackIn {
    feedback_type: FeedbackType;
    free_text?: string | null;
}
export const FeedbackType = {
    helpful: "helpful",
    not_helpful: "not_helpful",
    wrong: "wrong",
    used: "used",
    ignored: "ignored"
} as const;
export type FeedbackType = typeof FeedbackType[keyof typeof FeedbackType];
export interface HTTPValidationError {
    detail?: ValidationError[];
}
export interface KnowledgeDocument {
    content: string;
    document_id: string;
    section: string;
    tags: string[];
    title: string;
}
export interface Name {
    family_name?: string | null;
    given_name?: string | null;
}
export interface Recommendation {
    action_rationale: string;
    alerts?: Alert[];
    call_id: string;
    citations?: Citation[];
    compliance_notes?: string[];
    confidence: number;
    created_at?: string;
    escalation_reason?: string | null;
    intent: string;
    llm_latency_ms?: number;
    next_best_action: string;
    patient_state: string;
    recommendation_id?: string;
    recommended_response: string;
    risk_level: RiskLevel;
    should_escalate?: boolean;
    structured_slots?: Record<string, unknown>;
    summary_update: string;
    topic: string;
    trigger_segment_id?: string | null;
    urgency_level: RiskLevel;
}
export const RiskLevel = {
    low: "low",
    medium: "medium",
    high: "high",
    critical: "critical"
} as const;
export type RiskLevel = typeof RiskLevel[keyof typeof RiskLevel];
export interface Scenario {
    catalog_ids?: string[];
    coverage?: string;
    description: string;
    expected_risk_level: RiskLevel;
    family?: string;
    id: string;
    intent: string;
    location?: string;
    patient_name: string;
    queue?: string;
    title: string;
    vehicle?: string;
}
export const Speaker = {
    Agent: "Agent",
    Patient: "Patient",
    Unknown: "Unknown"
} as const;
export type Speaker = typeof Speaker[keyof typeof Speaker];
export interface StartCallIn {
    scenario_id?: string;
    settings?: CallSettings;
}
export interface StartCallOut {
    call: ActiveCall;
    recommendation?: Recommendation | null;
    transcript: TranscriptSegment[];
}
export interface TranscriptSegment {
    asr_latency_ms?: number;
    call_id: string;
    confidence?: number;
    created_at?: string;
    end_ms?: number;
    is_partial?: boolean;
    segment_id?: string;
    speaker?: Speaker;
    start_ms?: number;
    text: string;
}
export interface User {
    active?: boolean | null;
    display_name?: string | null;
    emails?: ComplexValue[] | null;
    entitlements?: ComplexValue[] | null;
    external_id?: string | null;
    groups?: ComplexValue[] | null;
    id?: string | null;
    name?: Name | null;
    roles?: ComplexValue[] | null;
    schemas?: UserSchema[] | null;
    user_name?: string | null;
}
export const UserSchema = {
    "urn:ietf:params:scim:schemas:core:2.0:User": "urn:ietf:params:scim:schemas:core:2.0:User",
    "urn:ietf:params:scim:schemas:extension:workspace:2.0:User": "urn:ietf:params:scim:schemas:extension:workspace:2.0:User"
} as const;
export type UserSchema = typeof UserSchema[keyof typeof UserSchema];
export interface ValidationError {
    ctx?: Record<string, unknown>;
    input?: unknown;
    loc: (string | number)[];
    msg: string;
    type: string;
}
export interface VersionOut {
    version: string;
}
export const processAudioChunk = async (data: AudioChunkIn, options?: RequestInit): Promise<{
    data: TranscriptSegment;
}> =>{
    const res = await fetch("/api/audio/chunk", {
        ...options,
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...options?.headers
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useProcessAudioChunk(options?: {
    mutation?: UseMutationOptions<{
        data: TranscriptSegment;
    }, ApiError, AudioChunkIn>;
}) {
    return useMutation({
        mutationFn: (data)=>processAudioChunk(data),
        ...options?.mutation
    });
}
export interface GetScenarioAudioParams {
    scenario_id: string;
}
export const getScenarioAudio = async (params: GetScenarioAudioParams, options?: RequestInit): Promise<{
    data: unknown;
}> =>{
    const res = await fetch(`/api/audio/scenario/${params.scenario_id}`, {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getScenarioAudioKey = (params?: GetScenarioAudioParams)=>{
    return [
        "/api/audio/scenario/{scenario_id}",
        params
    ] as const;
};
export function useGetScenarioAudio<TData = {
    data: unknown;
}>(options: {
    params: GetScenarioAudioParams;
    query?: Omit<UseQueryOptions<{
        data: unknown;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getScenarioAudioKey(options.params),
        queryFn: ()=>getScenarioAudio(options.params),
        ...options?.query
    });
}
export function useGetScenarioAudioSuspense<TData = {
    data: unknown;
}>(options: {
    params: GetScenarioAudioParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: unknown;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getScenarioAudioKey(options.params),
        queryFn: ()=>getScenarioAudio(options.params),
        ...options?.query
    });
}
export interface UploadAudioParams {
    call_id: string;
}
export const uploadAudio = async (params: UploadAudioParams, data: FormData, options?: RequestInit): Promise<{
    data: AudioUploadOut;
}> =>{
    const res = await fetch(`/api/audio/upload/${params.call_id}`, {
        ...options,
        method: "POST",
        headers: {
            ...options?.headers
        },
        body: data
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useUploadAudio(options?: {
    mutation?: UseMutationOptions<{
        data: AudioUploadOut;
    }, ApiError, {
        params: UploadAudioParams;
        data: FormData;
    }>;
}) {
    return useMutation({
        mutationFn: (vars)=>uploadAudio(vars.params, vars.data),
        ...options?.mutation
    });
}
export const listActiveCalls = async (options?: RequestInit): Promise<{
    data: ActiveCall[];
}> =>{
    const res = await fetch("/api/calls/active", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const listActiveCallsKey = ()=>{
    return [
        "/api/calls/active"
    ] as const;
};
export function useListActiveCalls<TData = {
    data: ActiveCall[];
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: ActiveCall[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: listActiveCallsKey(),
        queryFn: ()=>listActiveCalls(),
        ...options?.query
    });
}
export function useListActiveCallsSuspense<TData = {
    data: ActiveCall[];
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: ActiveCall[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: listActiveCallsKey(),
        queryFn: ()=>listActiveCalls(),
        ...options?.query
    });
}
export const startCall = async (data: StartCallIn, options?: RequestInit): Promise<{
    data: StartCallOut;
}> =>{
    const res = await fetch("/api/calls/start", {
        ...options,
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...options?.headers
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useStartCall(options?: {
    mutation?: UseMutationOptions<{
        data: StartCallOut;
    }, ApiError, StartCallIn>;
}) {
    return useMutation({
        mutationFn: (data)=>startCall(data),
        ...options?.mutation
    });
}
export interface GetCallParams {
    call_id: string;
}
export const getCall = async (params: GetCallParams, options?: RequestInit): Promise<{
    data: ActiveCall;
}> =>{
    const res = await fetch(`/api/calls/${params.call_id}`, {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getCallKey = (params?: GetCallParams)=>{
    return [
        "/api/calls/{call_id}",
        params
    ] as const;
};
export function useGetCall<TData = {
    data: ActiveCall;
}>(options: {
    params: GetCallParams;
    query?: Omit<UseQueryOptions<{
        data: ActiveCall;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getCallKey(options.params),
        queryFn: ()=>getCall(options.params),
        ...options?.query
    });
}
export function useGetCallSuspense<TData = {
    data: ActiveCall;
}>(options: {
    params: GetCallParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: ActiveCall;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getCallKey(options.params),
        queryFn: ()=>getCall(options.params),
        ...options?.query
    });
}
export interface EnableLiveMicrophoneParams {
    call_id: string;
}
export const enableLiveMicrophone = async (params: EnableLiveMicrophoneParams, options?: RequestInit): Promise<{
    data: ActiveCall;
}> =>{
    const res = await fetch(`/api/calls/${params.call_id}/live-microphone`, {
        ...options,
        method: "POST"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useEnableLiveMicrophone(options?: {
    mutation?: UseMutationOptions<{
        data: ActiveCall;
    }, ApiError, {
        params: EnableLiveMicrophoneParams;
    }>;
}) {
    return useMutation({
        mutationFn: (vars)=>enableLiveMicrophone(vars.params),
        ...options?.mutation
    });
}
export interface StopCallParams {
    call_id: string;
}
export const stopCall = async (params: StopCallParams, options?: RequestInit): Promise<{
    data: ActiveCall;
}> =>{
    const res = await fetch(`/api/calls/${params.call_id}/stop`, {
        ...options,
        method: "POST"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useStopCall(options?: {
    mutation?: UseMutationOptions<{
        data: ActiveCall;
    }, ApiError, {
        params: StopCallParams;
    }>;
}) {
    return useMutation({
        mutationFn: (vars)=>stopCall(vars.params),
        ...options?.mutation
    });
}
export interface GetTranscriptParams {
    call_id: string;
}
export const getTranscript = async (params: GetTranscriptParams, options?: RequestInit): Promise<{
    data: TranscriptSegment[];
}> =>{
    const res = await fetch(`/api/calls/${params.call_id}/transcript`, {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getTranscriptKey = (params?: GetTranscriptParams)=>{
    return [
        "/api/calls/{call_id}/transcript",
        params
    ] as const;
};
export function useGetTranscript<TData = {
    data: TranscriptSegment[];
}>(options: {
    params: GetTranscriptParams;
    query?: Omit<UseQueryOptions<{
        data: TranscriptSegment[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getTranscriptKey(options.params),
        queryFn: ()=>getTranscript(options.params),
        ...options?.query
    });
}
export function useGetTranscriptSuspense<TData = {
    data: TranscriptSegment[];
}>(options: {
    params: GetTranscriptParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: TranscriptSegment[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getTranscriptKey(options.params),
        queryFn: ()=>getTranscript(options.params),
        ...options?.query
    });
}
export const getConfig = async (options?: RequestInit): Promise<{
    data: AppConfigOut;
}> =>{
    const res = await fetch("/api/config", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getConfigKey = ()=>{
    return [
        "/api/config"
    ] as const;
};
export function useGetConfig<TData = {
    data: AppConfigOut;
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: AppConfigOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getConfigKey(),
        queryFn: ()=>getConfig(),
        ...options?.query
    });
}
export function useGetConfigSuspense<TData = {
    data: AppConfigOut;
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: AppConfigOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getConfigKey(),
        queryFn: ()=>getConfig(),
        ...options?.query
    });
}
export interface CurrentUserParams {
    "X-Forwarded-Host"?: string | null;
    "X-Forwarded-Preferred-Username"?: string | null;
    "X-Forwarded-User"?: string | null;
    "X-Forwarded-Email"?: string | null;
    "X-Request-Id"?: string | null;
    "X-Forwarded-Access-Token"?: string | null;
}
export const currentUser = async (params?: CurrentUserParams, options?: RequestInit): Promise<{
    data: User;
}> =>{
    const res = await fetch("/api/current-user", {
        ...options,
        method: "GET",
        headers: {
            ...(params?.["X-Forwarded-Host"] != null && {
                "X-Forwarded-Host": params["X-Forwarded-Host"]
            }),
            ...(params?.["X-Forwarded-Preferred-Username"] != null && {
                "X-Forwarded-Preferred-Username": params["X-Forwarded-Preferred-Username"]
            }),
            ...(params?.["X-Forwarded-User"] != null && {
                "X-Forwarded-User": params["X-Forwarded-User"]
            }),
            ...(params?.["X-Forwarded-Email"] != null && {
                "X-Forwarded-Email": params["X-Forwarded-Email"]
            }),
            ...(params?.["X-Request-Id"] != null && {
                "X-Request-Id": params["X-Request-Id"]
            }),
            ...(params?.["X-Forwarded-Access-Token"] != null && {
                "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"]
            }),
            ...options?.headers
        }
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const currentUserKey = (params?: CurrentUserParams)=>{
    return [
        "/api/current-user",
        params
    ] as const;
};
export function useCurrentUser<TData = {
    data: User;
}>(options?: {
    params?: CurrentUserParams;
    query?: Omit<UseQueryOptions<{
        data: User;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: currentUserKey(options?.params),
        queryFn: ()=>currentUser(options?.params),
        ...options?.query
    });
}
export function useCurrentUserSuspense<TData = {
    data: User;
}>(options?: {
    params?: CurrentUserParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: User;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: currentUserKey(options?.params),
        queryFn: ()=>currentUser(options?.params),
        ...options?.query
    });
}
export const listEvaluationExamples = async (options?: RequestInit): Promise<{
    data: EvaluationExample[];
}> =>{
    const res = await fetch("/api/evaluation/examples", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const listEvaluationExamplesKey = ()=>{
    return [
        "/api/evaluation/examples"
    ] as const;
};
export function useListEvaluationExamples<TData = {
    data: EvaluationExample[];
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: EvaluationExample[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: listEvaluationExamplesKey(),
        queryFn: ()=>listEvaluationExamples(),
        ...options?.query
    });
}
export function useListEvaluationExamplesSuspense<TData = {
    data: EvaluationExample[];
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: EvaluationExample[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: listEvaluationExamplesKey(),
        queryFn: ()=>listEvaluationExamples(),
        ...options?.query
    });
}
export const health = async (options?: RequestInit): Promise<{
    data: unknown;
}> =>{
    const res = await fetch("/api/health", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const healthKey = ()=>{
    return [
        "/api/health"
    ] as const;
};
export function useHealth<TData = {
    data: unknown;
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: unknown;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: healthKey(),
        queryFn: ()=>health(),
        ...options?.query
    });
}
export function useHealthSuspense<TData = {
    data: unknown;
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: unknown;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: healthKey(),
        queryFn: ()=>health(),
        ...options?.query
    });
}
export const listKnowledgeDocuments = async (options?: RequestInit): Promise<{
    data: KnowledgeDocument[];
}> =>{
    const res = await fetch("/api/knowledge-documents", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const listKnowledgeDocumentsKey = ()=>{
    return [
        "/api/knowledge-documents"
    ] as const;
};
export function useListKnowledgeDocuments<TData = {
    data: KnowledgeDocument[];
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: KnowledgeDocument[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: listKnowledgeDocumentsKey(),
        queryFn: ()=>listKnowledgeDocuments(),
        ...options?.query
    });
}
export function useListKnowledgeDocumentsSuspense<TData = {
    data: KnowledgeDocument[];
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: KnowledgeDocument[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: listKnowledgeDocumentsKey(),
        queryFn: ()=>listKnowledgeDocuments(),
        ...options?.query
    });
}
export const demoMetrics = async (options?: RequestInit): Promise<{
    data: DemoMetrics;
}> =>{
    const res = await fetch("/api/metrics/demo", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const demoMetricsKey = ()=>{
    return [
        "/api/metrics/demo"
    ] as const;
};
export function useDemoMetrics<TData = {
    data: DemoMetrics;
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: DemoMetrics;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: demoMetricsKey(),
        queryFn: ()=>demoMetrics(),
        ...options?.query
    });
}
export function useDemoMetricsSuspense<TData = {
    data: DemoMetrics;
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: DemoMetrics;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: demoMetricsKey(),
        queryFn: ()=>demoMetrics(),
        ...options?.query
    });
}
export const analyzeCall = async (data: AnalyzeIn, options?: RequestInit): Promise<{
    data: Recommendation;
}> =>{
    const res = await fetch("/api/recommendations/analyze", {
        ...options,
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...options?.headers
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useAnalyzeCall(options?: {
    mutation?: UseMutationOptions<{
        data: Recommendation;
    }, ApiError, AnalyzeIn>;
}) {
    return useMutation({
        mutationFn: (data)=>analyzeCall(data),
        ...options?.mutation
    });
}
export interface LatestRecommendationParams {
    call_id: string;
}
export const latestRecommendation = async (params: LatestRecommendationParams, options?: RequestInit): Promise<{
    data: Recommendation | null;
}> =>{
    const res = await fetch(`/api/recommendations/latest/${params.call_id}`, {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const latestRecommendationKey = (params?: LatestRecommendationParams)=>{
    return [
        "/api/recommendations/latest/{call_id}",
        params
    ] as const;
};
export function useLatestRecommendation<TData = {
    data: Recommendation | null;
}>(options: {
    params: LatestRecommendationParams;
    query?: Omit<UseQueryOptions<{
        data: Recommendation | null;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: latestRecommendationKey(options.params),
        queryFn: ()=>latestRecommendation(options.params),
        ...options?.query
    });
}
export function useLatestRecommendationSuspense<TData = {
    data: Recommendation | null;
}>(options: {
    params: LatestRecommendationParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: Recommendation | null;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: latestRecommendationKey(options.params),
        queryFn: ()=>latestRecommendation(options.params),
        ...options?.query
    });
}
export interface ListRecommendationsParams {
    call_id: string;
}
export const listRecommendations = async (params: ListRecommendationsParams, options?: RequestInit): Promise<{
    data: Recommendation[];
}> =>{
    const res = await fetch(`/api/recommendations/${params.call_id}`, {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const listRecommendationsKey = (params?: ListRecommendationsParams)=>{
    return [
        "/api/recommendations/{call_id}",
        params
    ] as const;
};
export function useListRecommendations<TData = {
    data: Recommendation[];
}>(options: {
    params: ListRecommendationsParams;
    query?: Omit<UseQueryOptions<{
        data: Recommendation[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: listRecommendationsKey(options.params),
        queryFn: ()=>listRecommendations(options.params),
        ...options?.query
    });
}
export function useListRecommendationsSuspense<TData = {
    data: Recommendation[];
}>(options: {
    params: ListRecommendationsParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: Recommendation[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: listRecommendationsKey(options.params),
        queryFn: ()=>listRecommendations(options.params),
        ...options?.query
    });
}
export interface SubmitFeedbackParams {
    recommendation_id: string;
}
export const submitFeedback = async (params: SubmitFeedbackParams, data: FeedbackIn, options?: RequestInit): Promise<{
    data: AgentFeedback;
}> =>{
    const res = await fetch(`/api/recommendations/${params.recommendation_id}/feedback`, {
        ...options,
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...options?.headers
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useSubmitFeedback(options?: {
    mutation?: UseMutationOptions<{
        data: AgentFeedback;
    }, ApiError, {
        params: SubmitFeedbackParams;
        data: FeedbackIn;
    }>;
}) {
    return useMutation({
        mutationFn: (vars)=>submitFeedback(vars.params, vars.data),
        ...options?.mutation
    });
}
export interface ReplayCallParams {
    call_id: string;
}
export const replayCall = async (params: ReplayCallParams, options?: RequestInit): Promise<{
    data: unknown;
}> =>{
    const res = await fetch(`/api/replay/${params.call_id}`, {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const replayCallKey = (params?: ReplayCallParams)=>{
    return [
        "/api/replay/{call_id}",
        params
    ] as const;
};
export function useReplayCall<TData = {
    data: unknown;
}>(options: {
    params: ReplayCallParams;
    query?: Omit<UseQueryOptions<{
        data: unknown;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: replayCallKey(options.params),
        queryFn: ()=>replayCall(options.params),
        ...options?.query
    });
}
export function useReplayCallSuspense<TData = {
    data: unknown;
}>(options: {
    params: ReplayCallParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: unknown;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: replayCallKey(options.params),
        queryFn: ()=>replayCall(options.params),
        ...options?.query
    });
}
export const listScenarios = async (options?: RequestInit): Promise<{
    data: Scenario[];
}> =>{
    const res = await fetch("/api/scenarios", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const listScenariosKey = ()=>{
    return [
        "/api/scenarios"
    ] as const;
};
export function useListScenarios<TData = {
    data: Scenario[];
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: Scenario[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: listScenariosKey(),
        queryFn: ()=>listScenarios(),
        ...options?.query
    });
}
export function useListScenariosSuspense<TData = {
    data: Scenario[];
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: Scenario[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: listScenariosKey(),
        queryFn: ()=>listScenarios(),
        ...options?.query
    });
}
export const version = async (options?: RequestInit): Promise<{
    data: VersionOut;
}> =>{
    const res = await fetch("/api/version", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const versionKey = ()=>{
    return [
        "/api/version"
    ] as const;
};
export function useVersion<TData = {
    data: VersionOut;
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: VersionOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: versionKey(),
        queryFn: ()=>version(),
        ...options?.query
    });
}
export function useVersionSuspense<TData = {
    data: VersionOut;
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: VersionOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: versionKey(),
        queryFn: ()=>version(),
        ...options?.query
    });
}
