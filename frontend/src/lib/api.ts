/**
 * API Client with snake_case to camelCase adapter
 * Backend uses snake_case (Python), Frontend uses camelCase (TypeScript)
 */

import type { ChatRequest, ChatResponse, GraphNode, GraphEdge, OntologyPath, DocumentRef } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

// Helper functions
function asArray<T = unknown>(value: unknown): T[] {
  if (Array.isArray(value)) return value as T[];
  return [];
}

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function mapOntologyPath(value: unknown): OntologyPath {
  const item = asRecord(value);
  return {
    path: Array.isArray(item?.path) ? item.path as string[] : [],
    relations: Array.isArray(item?.relations) ? item.relations as string[] : [],
    confidence: typeof item?.confidence === 'number' ? item.confidence : undefined,
  };
}

function mapDocumentRef(value: unknown): DocumentRef {
  const item = asRecord(value);
  const docId = (item?.doc_id ?? item?.docId) as string | undefined;
  const chunkId = (item?.chunk_id ?? item?.chunkId) as string | undefined;
  const relevance = (item?.relevance ?? item?.score) as number | undefined;

  return {
    docId: typeof docId === 'string' ? docId : undefined,
    chunkId: typeof chunkId === 'string' ? chunkId : undefined,
    page: typeof item?.page === 'number' ? item.page : undefined,
    relevance: typeof relevance === 'number' ? relevance : undefined,
  };
}

function mapGraphNode(value: unknown): GraphNode {
  const item = asRecord(value);
  return {
    id: String(item?.id ?? ''),
    type: String(item?.type ?? ''),
    label: String(item?.label ?? ''),
    state: item?.state as GraphNode['state'],
  };
}

function mapGraphEdge(value: unknown): GraphEdge {
  const item = asRecord(value);
  return {
    source: String(item?.source ?? ''),
    target: String(item?.target ?? ''),
    relation: String(item?.relation ?? ''),
  };
}

/**
 * Normalize backend response (snake_case) to frontend (camelCase)
 */
export function normalizeChatResponse(raw: Record<string, unknown>): ChatResponse {
  const r = raw ?? {};

  const traceId = (r.trace_id ?? r.traceId) as string;
  const queryType = (r.query_type ?? r.queryType) as ChatResponse['queryType'];
  const abstainReason = (r.abstain_reason ?? r.abstainReason) as string | undefined;

  const partialEvidenceRaw = (r.partial_evidence ?? r.partialEvidence) as Record<string, unknown> | undefined;
  const suggestedQuestionsRaw = (r.suggested_questions ?? r.suggestedQuestions) as unknown;

  const evidence = (r.evidence ?? {}) as Record<string, unknown>;
  const ontologyPathsRaw = evidence.ontology_paths ?? evidence.ontologyPathObjects;
  const documentRefsRaw = evidence.document_refs ?? evidence.documentRefs;
  const similarEventsRaw = evidence.similar_events ?? evidence.similarEvents;

  const graph = (r.graph ?? {}) as Record<string, unknown>;
  const nodesRaw = graph.nodes;
  const edgesRaw = graph.edges;

  // Map analysis (snake_case to camelCase)
  const analysisRaw = r.analysis as Record<string, unknown> | undefined;
  const analysis = analysisRaw ? {
    entity: analysisRaw.entity as string | undefined,
    value: analysisRaw.value as number | undefined,
    unit: analysisRaw.unit as string | undefined,
    state: analysisRaw.state as string | undefined,
    normalRange: analysisRaw.normal_range as number[] | undefined,
    deviation: analysisRaw.deviation as string | undefined,
  } : undefined;

  // Map reasoning
  const reasoningRaw = r.reasoning as Record<string, unknown> | undefined;
  const reasoning = reasoningRaw ? {
    confidence: (reasoningRaw.confidence as number) ?? 0,
    pattern: reasoningRaw.pattern as string | undefined,
    patternConfidence: (reasoningRaw.pattern_confidence ?? reasoningRaw.patternConfidence) as number | undefined,
    cause: reasoningRaw.cause as string | undefined,
    causeConfidence: (reasoningRaw.cause_confidence ?? reasoningRaw.causeConfidence) as number | undefined,
  } : undefined;

  // Map prediction
  const predictionRaw = r.prediction as Record<string, unknown> | undefined;
  const prediction = predictionRaw ? {
    errorCode: (predictionRaw.error_code ?? predictionRaw.errorCode) as string | undefined,
    probability: predictionRaw.probability as number | undefined,
    timeframe: predictionRaw.timeframe as string | undefined,
  } : undefined;

  // Map recommendation
  const recommendationRaw = r.recommendation as Record<string, unknown> | undefined;
  const recommendation = recommendationRaw ? {
    immediate: recommendationRaw.immediate as string | undefined,
    reference: recommendationRaw.reference as string | undefined,
  } : undefined;

  return {
    traceId: String(traceId ?? ''),
    queryType: queryType ?? 'rag',
    answer: String(r.answer ?? ''),
    abstain: Boolean(r.abstain),
    abstainReason: typeof abstainReason === 'string' ? abstainReason : undefined,
    partialEvidence: partialEvidenceRaw
      ? {
          found: asArray(partialEvidenceRaw.found).map((x) => String(x)),
          missing: asArray(partialEvidenceRaw.missing).map((x) => String(x)),
        }
      : undefined,
    suggestedQuestions: asArray(suggestedQuestionsRaw).map((x) => String(x)),
    analysis,
    reasoning,
    prediction,
    recommendation,
    evidence: {
      ontologyPathObjects: asArray(ontologyPathsRaw).map(mapOntologyPath),
      documentRefs: asArray(documentRefsRaw).map(mapDocumentRef),
      similarEvents: asArray(similarEventsRaw).map((x) => String(x)),
    },
    graph: {
      nodes: asArray(nodesRaw).map(mapGraphNode),
      edges: asArray(edgesRaw).map(mapGraphEdge),
    },
    timestamp: typeof r.timestamp === 'string' ? r.timestamp : undefined,
  };
}

/**
 * Build chat request for backend
 */
export function buildChatRequest(req: ChatRequest): Record<string, unknown> {
  const message = typeof req.message === 'string' ? req.message : undefined;
  const query = typeof req.query === 'string' ? req.query : undefined;
  const normalizedQuery = query ?? message;

  return {
    ...(normalizedQuery ? { query: normalizedQuery } : {}),
    ...(message ? { message } : {}),
    context: req.context ?? undefined,
  };
}

// API Functions
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(buildChatRequest(request)),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const raw = await response.json();
  return normalizeChatResponse(raw);
}

export async function getEvidence(traceId: string) {
  const response = await fetch(`${API_BASE_URL}/api/evidence/${traceId}`);

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}

export async function getOntologySummary() {
  const response = await fetch(`${API_BASE_URL}/api/ontology/summary`);
  return response.json();
}

// ============================================================
// Sensor API
// ============================================================

export interface SensorReadingRaw {
  timestamp: string;
  Fx: number;
  Fy: number;
  Fz: number;
  Tx: number;
  Ty: number;
  Tz: number;
  status?: string;
  task_mode?: string;
}

export interface SensorReadingsResponse {
  readings: SensorReadingRaw[];
  total: number;
  time_range: { start: string; end: string };
}

export interface PatternRaw {
  id: string;
  type: string;
  timestamp: string;
  confidence: number;
  metrics: Record<string, unknown>;
  related_error_codes: string[];
}

export interface PatternsResponse {
  patterns: PatternRaw[];
  total: number;
}

export interface EventRaw {
  event_id: string;
  scenario: string;
  event_type: string;
  start_time: string;
  end_time: string;
  duration_s: number;
  error_code?: string;
  description: string;
}

export interface EventsResponse {
  events: EventRaw[];
  total: number;
}

export async function getSensorReadings(limit = 60, offset = 0): Promise<SensorReadingsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/sensors/readings?limit=${limit}&offset=${offset}`
  );
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export async function getSensorPatterns(limit = 10): Promise<PatternsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/sensors/patterns?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export async function getSensorEvents(limit = 20): Promise<EventsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/sensors/events?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

// 시간 범위 기반 샘플링 데이터 조회
export interface SensorRangeResponse {
  readings: SensorReadingRaw[];
  total: number;
  sampled: number;
  hours: number;
  time_range: { start: string; end: string };
}

export async function getSensorReadingsRange(hours = 1, samples = 200): Promise<SensorRangeResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/sensors/readings/range?hours=${hours}&samples=${samples}`
  );
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

// ============================================================
// 이기종 결합 예측 API (Axia80 + UR5e 온톨로지)
// ============================================================

export interface PredictionItem {
  error_code: string;
  probability: number;
  pattern: string;
  cause?: string;
  timeframe?: string;
  recommendation?: string;
}

export interface RealtimePrediction {
  timestamp: string;
  sensor_value: number;
  state: 'normal' | 'warning' | 'critical';
  pattern_detected?: string;
  predictions: PredictionItem[];
  ontology_path?: string;
}

export interface PredictionsResponse {
  predictions: RealtimePrediction[];
  total_patterns: number;
  high_risk_count: number;
}

export async function getPredictions(limit = 10): Promise<PredictionsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/sensors/predictions?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

// ============================================================
// 온톨로지 그래프 탐색 API (팔란티어 스타일)
// ============================================================

export interface OntologyGraphNode {
  id: string;
  type: string;
  label: string;
  domain?: string;
  properties?: Record<string, unknown>;
}

export interface OntologyGraphEdge {
  source: string;
  target: string;
  relation: string;
  properties?: Record<string, unknown>;
}

export interface AllEntitiesResponse {
  entities: OntologyGraphNode[];
  total: number;
  by_type: Record<string, number>;
  by_domain: Record<string, number>;
}

export interface EntityDetailResponse {
  id: string;
  type: string;
  name: string;
  domain?: string;
  properties?: Record<string, unknown>;
  description?: string;
}

export interface NeighborsResponse {
  center: OntologyGraphNode;
  nodes: OntologyGraphNode[];
  edges: OntologyGraphEdge[];
  total_neighbors: number;
}

export interface SubgraphResponse {
  nodes: OntologyGraphNode[];
  edges: OntologyGraphEdge[];
  center_id: string;
  depth: number;
  total_nodes: number;
  total_edges: number;
}

/**
 * 전체 엔티티 목록 조회
 */
export async function getOntologyEntities(): Promise<AllEntitiesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ontology/entities`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * 특정 엔티티 상세 정보 조회
 */
export async function getOntologyEntity(entityId: string): Promise<EntityDetailResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ontology/entity/${encodeURIComponent(entityId)}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * 이웃 노드 조회 (1-hop 탐색)
 */
export async function getOntologyNeighbors(
  entityId: string,
  direction: 'outgoing' | 'incoming' | 'both' = 'both'
): Promise<NeighborsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/ontology/neighbors/${encodeURIComponent(entityId)}?direction=${direction}`
  );
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * 서브그래프 조회 (팔란티어 스타일 그래프 탐색)
 */
export async function getOntologyGraph(
  centerId: string,
  depth: number = 2,
  direction: 'outgoing' | 'incoming' | 'both' = 'both'
): Promise<SubgraphResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/ontology/graph?center=${encodeURIComponent(centerId)}&depth=${depth}&direction=${direction}`
  );
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}
