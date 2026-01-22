// P0 API contract helper (backend snake_case -> frontend camelCase)
//
// 목적:
// - 백엔드는 Python 표준(snake_case)을 유지
// - 프론트는 이 어댑터에서 camelCase로 변환하여 UI 전역에서는 camelCase만 사용
//
// 사용 예시:
// const raw = await fetch('/api/chat', { method: 'POST', body: JSON.stringify({ query: '...' })}).then(r => r.json())
// const data = normalizeChatResponse(raw)

export type QueryType = 'ontology' | 'hybrid' | 'rag' | string
export type NodeState = 'normal' | 'warning' | 'critical' | string

export interface OntologyPath {
  path: string[]
  relations: string[]
  confidence?: number
}

export interface DocumentRef {
  docId?: string
  page?: number
  chunkId?: string
  relevance?: number
  // 백엔드가 다른 키를 줄 수도 있어 열어둠
  [k: string]: unknown
}

export interface GraphNode {
  id: string
  type: string
  label: string
  state?: NodeState
  [k: string]: unknown
}

export interface GraphEdge {
  source: string
  target: string
  relation: string
  [k: string]: unknown
}

export interface ChatEvidence {
  ontologyPathObjects?: OntologyPath[]
  documentRefs?: DocumentRef[]
  similarEvents?: string[]
  // 필요하면 확장
  [k: string]: unknown
}

export interface ChatResponse {
  traceId: string
  queryType: QueryType
  answer: string
  abstain: boolean
  abstainReason?: string

  analysis?: Record<string, unknown>
  reasoning?: Record<string, unknown>
  prediction?: Record<string, unknown>
  recommendation?: Record<string, unknown>

  evidence?: ChatEvidence
  graph?: {
    nodes: GraphNode[]
    edges: GraphEdge[]
  }

  timestamp?: string
  [k: string]: unknown
}

type AnyRecord = Record<string, any>

function asArray<T = any>(value: any): T[] {
  if (Array.isArray(value)) return value
  return []
}

function mapOntologyPathObject(item: any): OntologyPath {
  // 백엔드가 { path: [...], relations: [...] } 형태를 준다는 전제
  return {
    path: Array.isArray(item?.path) ? item.path : [],
    relations: Array.isArray(item?.relations) ? item.relations : [],
    confidence: typeof item?.confidence === 'number' ? item.confidence : undefined,
  }
}

function mapDocumentRef(item: any): DocumentRef {
  // 흔한 snake_case 키를 camelCase로 보정
  const docId = item?.doc_id ?? item?.docId
  const chunkId = item?.chunk_id ?? item?.chunkId
  const relevance = item?.relevance ?? item?.score

  return {
    ...item,
    docId: typeof docId === 'string' ? docId : undefined,
    chunkId: typeof chunkId === 'string' ? chunkId : undefined,
    page: typeof item?.page === 'number' ? item.page : undefined,
    relevance: typeof relevance === 'number' ? relevance : undefined,
  }
}

function mapGraphNode(item: any): GraphNode {
  return {
    ...item,
    id: String(item?.id ?? ''),
    type: String(item?.type ?? ''),
    label: String(item?.label ?? ''),
    state: item?.state,
  }
}

function mapGraphEdge(item: any): GraphEdge {
  return {
    ...item,
    source: String(item?.source ?? ''),
    target: String(item?.target ?? ''),
    relation: String(item?.relation ?? ''),
  }
}

/**
 * 백엔드(snake_case) 응답을 프론트(camelCase)로 정규화.
 *
 * 핵심 매핑:
 * - trace_id -> traceId
 * - query_type -> queryType
 * - abstain_reason -> abstainReason
 * - evidence.ontology_paths -> evidence.ontologyPathObjects
 * - evidence.document_refs -> evidence.documentRefs
 * - evidence.similar_events -> evidence.similarEvents
 */
export function normalizeChatResponse(raw: unknown): ChatResponse {
  const r = (raw ?? {}) as AnyRecord

  const traceId = r.trace_id ?? r.traceId
  const queryType = r.query_type ?? r.queryType
  const abstainReason = r.abstain_reason ?? r.abstainReason

  const evidence = (r.evidence ?? {}) as AnyRecord
  const ontologyPathObjectsRaw = evidence.ontology_paths ?? evidence.ontologyPathObjects
  const documentRefsRaw = evidence.document_refs ?? evidence.documentRefs
  const similarEventsRaw = evidence.similar_events ?? evidence.similarEvents

  const graph = (r.graph ?? {}) as AnyRecord
  const nodesRaw = graph.nodes
  const edgesRaw = graph.edges

  return {
    ...r,
    traceId: String(traceId ?? ''),
    queryType: (queryType ?? '') as QueryType,
    answer: String(r.answer ?? ''),
    abstain: Boolean(r.abstain),
    abstainReason: typeof abstainReason === 'string' ? abstainReason : undefined,

    evidence: {
      ...evidence,
      ontologyPathObjects: asArray(ontologyPathObjectsRaw).map(mapOntologyPathObject),
      documentRefs: asArray(documentRefsRaw).map(mapDocumentRef),
      similarEvents: asArray(similarEventsRaw).map((x) => String(x)),
    },

    graph: {
      nodes: asArray(nodesRaw).map(mapGraphNode),
      edges: asArray(edgesRaw).map(mapGraphEdge),
    },

    timestamp: typeof r.timestamp === 'string' ? r.timestamp : undefined,
  }
}

export interface ChatRequest {
  // 프론트는 message를 우선으로 쓰되, 백엔드가 query/message 모두 받으므로 둘 중 하나만 넣어도 됨
  message?: string
  query?: string
  context?: Record<string, unknown>
}

/**
 * 프론트 요청을 백엔드와 호환되게 구성.
 *
 * 권장: 프론트 내부에서는 message를 표준으로 사용.
 * - message가 있으면 message만 전송
 * - 없으면 query 전송
 */
export function buildChatRequest(req: ChatRequest): AnyRecord {
  const message = typeof req.message === 'string' ? req.message : undefined
  const query = typeof req.query === 'string' ? req.query : undefined

  return {
    ...(message ? { message } : {}),
    ...(!message && query ? { query } : {}),
    context: req.context ?? undefined,
  }
}
