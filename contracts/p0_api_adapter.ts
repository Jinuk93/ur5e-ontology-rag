// P0 API Contract - Type Definitions Only
//
// 이 파일은 백엔드-프론트엔드 간 API 계약을 정의하는 **타입 전용** 파일입니다.
//
// ========================================
// 런타임 어댑터 로직(정본):
//   frontend/src/lib/api.ts
//   - normalizeChatResponse(): snake_case → camelCase 변환
//   - buildChatRequest(): 요청 구성
// ========================================
//
// 이 파일의 역할:
// - API 계약 문서화 (타입/인터페이스 정의)
// - 백엔드 응답 스키마 참조용
// - 프론트엔드 타입 참조용 (실제 타입은 frontend/src/types/api.ts 사용 권장)
//
// 스키마 변경 시:
// 1. 백엔드 스키마 수정 (src/api/main.py)
// 2. 프론트 타입 수정 (frontend/src/types/api.ts)
// 3. 프론트 어댑터 수정 (frontend/src/lib/api.ts)
// 4. 이 파일은 문서화 목적으로 동기화 (선택)

// ============================================================
// Type Definitions
// ============================================================

export type QueryType = 'ontology' | 'hybrid' | 'rag' | string;
export type NodeState = 'normal' | 'warning' | 'critical' | string;

// ============================================================
// Evidence Types
// ============================================================

export interface OntologyPath {
  path: string[];
  relations: string[];
  confidence?: number;
}

export interface DocumentRef {
  docId?: string;
  page?: number;
  chunkId?: string;
  relevance?: number;
}

export interface ChatEvidence {
  ontologyPathObjects?: OntologyPath[];
  documentRefs?: DocumentRef[];
  similarEvents?: string[];
}

// ============================================================
// Graph Types
// ============================================================

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  state?: NodeState;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

// ============================================================
// ABSTAIN Types (P3-4)
// ============================================================

export interface PartialEvidence {
  found: string[];
  missing: string[];
}

// ============================================================
// Chat Request/Response
// ============================================================

/**
 * 프론트엔드 → 백엔드 요청 스키마
 *
 * 백엔드는 query와 message 모두 수용 (query 우선)
 */
export interface ChatRequest {
  message?: string;
  query?: string;
  context?: {
    selectedEntity?: string;
    currentValue?: number;
    timeRange?: string;
    recentEvents?: string[];
    currentView?: 'live' | 'graph' | 'history';
  };
}

/**
 * 백엔드 → 프론트엔드 응답 스키마 (camelCase 정규화 후)
 *
 * 백엔드 원본은 snake_case (trace_id, query_type, abstain_reason 등)
 * 프론트 어댑터에서 camelCase로 변환
 */
export interface ChatResponse {
  traceId: string;
  queryType: QueryType;
  answer: string;
  abstain: boolean;
  abstainReason?: string;

  // ABSTAIN 개선 UI 지원 (P3-4)
  partialEvidence?: PartialEvidence;
  suggestedQuestions?: string[];

  // 분석 결과
  analysis?: {
    entity?: string;
    value?: number;
    unit?: string;
    state?: string;
    normalRange?: number[];
    deviation?: string;
  };

  // 추론 결과
  reasoning?: {
    confidence: number;
    pattern?: string;
    patternConfidence?: number;
    cause?: string;
    causeConfidence?: number;
  };

  // 예측
  prediction?: {
    errorCode?: string;
    probability?: number;
    timeframe?: string;
  };

  // 권장 조치
  recommendation?: {
    immediate?: string;
    reference?: string;
  };

  // 근거
  evidence?: ChatEvidence;

  // 그래프 시각화용
  graph?: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };

  timestamp?: string;
}

// ============================================================
// Backend snake_case → Frontend camelCase 매핑 참조
// ============================================================
//
// 백엔드 응답 (snake_case)    →  프론트 타입 (camelCase)
// ─────────────────────────────────────────────────────────
// trace_id                   →  traceId
// query_type                 →  queryType
// abstain_reason             →  abstainReason
// partial_evidence           →  partialEvidence
// suggested_questions        →  suggestedQuestions
// evidence.ontology_paths    →  evidence.ontologyPathObjects
// evidence.document_refs     →  evidence.documentRefs
// evidence.similar_events    →  evidence.similarEvents
// analysis.normal_range      →  analysis.normalRange
// reasoning.pattern_confidence → reasoning.patternConfidence
// reasoning.cause_confidence →  reasoning.causeConfidence
// prediction.error_code      →  prediction.errorCode
//
// 변환 로직 구현: frontend/src/lib/api.ts > normalizeChatResponse()
