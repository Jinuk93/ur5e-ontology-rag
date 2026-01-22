// API Types - Backend snake_case to Frontend camelCase

export type EntityType =
  | 'ROBOT'
  | 'SENSOR'
  | 'MEASUREMENT_AXIS'
  | 'STATE'
  | 'PATTERN'
  | 'ERROR_CODE'
  | 'CAUSE'
  | 'RESOLUTION';

export type RelationType =
  | 'HAS_STATE'
  | 'TRIGGERS'
  | 'CAUSED_BY'
  | 'RESOLVED_BY'
  | 'INDICATES'
  | 'MEASURES'
  | 'HAS_SENSOR';

export type QueryType = 'ontology' | 'hybrid' | 'rag';
export type NodeState = 'normal' | 'warning' | 'critical';

// Sensor Reading
export interface SensorReading {
  timestamp: string;
  Fx: number;
  Fy: number;
  Fz: number;
  Tx: number;
  Ty: number;
  Tz: number;
}

// Graph Types
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

// Chat Types
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

export interface AnalysisInfo {
  entity?: string;
  value?: number;
  unit?: string;
  state?: string;
  normalRange?: number[];
  deviation?: string;
}

export interface ReasoningInfo {
  confidence: number;
  pattern?: string;
  patternConfidence?: number;
  cause?: string;
  causeConfidence?: number;
}

export interface PredictionInfo {
  errorCode?: string;
  probability?: number;
  timeframe?: string;
}

export interface RecommendationInfo {
  immediate?: string;
  reference?: string;
}

export interface ChatResponse {
  traceId: string;
  queryType: QueryType;
  answer: string;
  abstain: boolean;
  abstainReason?: string;
  analysis?: AnalysisInfo;
  reasoning?: ReasoningInfo;
  prediction?: PredictionInfo;
  recommendation?: RecommendationInfo;
  evidence?: ChatEvidence;
  graph?: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  timestamp?: string;
}

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

// Risk Alert
export interface RiskAlert {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  timestamp: string;
  entityId?: string;
  count?: number;
}

// Pattern
export interface Pattern {
  id: string;
  type: 'collision' | 'overload' | 'drift' | 'vibration';
  timestamp: string;
  confidence: number;
  metrics: {
    peakValue?: number;
    duration?: number;
    deviation?: number;
  };
  relatedErrorCodes: string[];
}

// Entity Card
export interface EntityInfo {
  id: string;
  name: string;
  type: EntityType;
  state: NodeState;
  currentValue?: number;
  unit?: string;
  normalRange?: [number, number];
}
