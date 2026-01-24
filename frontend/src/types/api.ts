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

export interface PartialEvidence {
  found: string[];
  missing: string[];
}

export interface ChatResponse {
  traceId: string;
  queryType: QueryType;
  answer: string;
  abstain: boolean;
  abstainReason?: string;
  partialEvidence?: PartialEvidence;
  suggestedQuestions?: string[];
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
  description?: string;
  detail?: string;
  type: EntityType;
  state: NodeState;
  currentValue?: number;
  unit?: string;
  normalRange?: [number, number];
}

// ============================================================
// Phase 3: UR5e + Axia80 통합 실시간 스트림 타입
// ============================================================

export type SafetyMode = 'normal' | 'reduced' | 'protective_stop';
export type ProgramState = 'running' | 'paused' | 'stopped';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type RecommendedAction = 'maintain' | 'caution' | 'slow_down' | 'emergency_stop' | 'inspect_joints';
export type ScenarioType = 'normal' | 'collision' | 'overload' | 'wear' | 'risk_approach';

/** UR5e 텔레메트리 데이터 (시뮬레이션) */
export interface UR5eTelemetry {
  tcp_speed: number;          // m/s (0~1.0)
  tcp_acceleration: number;   // m/s² (-5~5)
  joint_torque_sum: number;   // Nm (0~150)
  joint_current_avg: number;  // A (0.5~5.0)
  safety_mode: SafetyMode;
  program_state: ProgramState;
  protective_stop: boolean;
}

/** Axia80 힘 센서 확장 데이터 */
export interface Axia80Data {
  Fx: number;
  Fy: number;
  Fz: number;
  Tx: number;
  Ty: number;
  Tz: number;
  force_magnitude: number;    // 힘 크기 (N)
  force_rate: number;         // 힘 변화율 (N/tick)
  force_spike: boolean;       // 스파이크 감지
  peak_axis: string;          // 최대 힘 축
}

/** UR5e-Axia80 상관 메트릭 */
export interface CorrelationMetrics {
  torque_force_ratio: number;        // 토크/힘 비율
  speed_force_correlation: number;   // 속도-힘 상관계수 (-1~1)
  anomaly_detected: boolean;         // 이상 감지
}

/** 위험도 평가 */
export interface RiskAssessment {
  contact_risk_score: number;    // 0~1
  collision_risk_score: number;  // 0~1
  risk_level: RiskLevel;
  recommended_action: RecommendedAction;
  prediction_horizon_sec: number;
}

/** 시나리오 정보 */
export interface ScenarioInfo {
  current: ScenarioType;
  elapsed_sec: number;
  remaining_sec: number;
}

/** 통합 실시간 스트림 데이터 */
export interface IntegratedStreamData {
  timestamp: string;
  scenario: ScenarioInfo;
  axia80: Axia80Data;
  ur5e: UR5eTelemetry;
  correlation: CorrelationMetrics;
  risk: RiskAssessment;
  data_source: 'simulated' | 'live';
}
