/**
 * React Query Hooks for API calls
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getHealth,
  getOntologySummary,
  getEvidence,
  sendChatMessage,
  getSensorReadings,
  getSensorPatterns,
  getSensorEvents,
  getSensorReadingsRange,
  getPredictions,
  getOntologyEntities,
  getOntologyEntity,
  getOntologyNeighbors,
  getOntologyGraph,
} from '@/lib/api';
import type { ChatRequest, ChatResponse } from '@/types/api';

// Query Keys
export const queryKeys = {
  health: ['health'] as const,
  ontologySummary: ['ontology', 'summary'] as const,
  ontologyEntities: ['ontology', 'entities'] as const,
  ontologyEntity: (entityId: string) => ['ontology', 'entity', entityId] as const,
  ontologyNeighbors: (entityId: string, direction: string) => ['ontology', 'neighbors', entityId, direction] as const,
  ontologyGraph: (centerId: string, depth: number, direction: string) => ['ontology', 'graph', centerId, depth, direction] as const,
  evidence: (traceId: string) => ['evidence', traceId] as const,
  sensorReadings: (limit: number, offset: number) => ['sensors', 'readings', limit, offset] as const,
  sensorReadingsRange: (hours: number, samples: number) => ['sensors', 'readings', 'range', hours, samples] as const,
  sensorPatterns: (limit: number) => ['sensors', 'patterns', limit] as const,
  sensorEvents: (limit: number) => ['sensors', 'events', limit] as const,
  predictions: (limit: number) => ['sensors', 'predictions', limit] as const,
};

/**
 * Health check hook - polls every 30 seconds
 */
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: getHealth,
    refetchInterval: 30000, // 30 seconds
    staleTime: 10000, // 10 seconds
  });
}

/**
 * Ontology summary hook - cached for longer duration
 */
export function useOntologySummary() {
  return useQuery({
    queryKey: queryKeys.ontologySummary,
    queryFn: getOntologySummary,
    staleTime: 1000 * 60 * 10, // 10 minutes - ontology changes rarely
  });
}

/**
 * Evidence hook - fetch evidence by traceId
 */
export function useEvidence(traceId: string | null) {
  return useQuery({
    queryKey: queryKeys.evidence(traceId || ''),
    queryFn: () => getEvidence(traceId!),
    enabled: !!traceId, // Only fetch when traceId is provided
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Chat mutation hook
 */
export function useChatMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ChatRequest) => sendChatMessage(request),
    onSuccess: (data: ChatResponse) => {
      // Pre-populate evidence cache if we have a traceId
      if (data.traceId && data.evidence) {
        queryClient.setQueryData(
          queryKeys.evidence(data.traceId),
          { found: true, evidence: data.evidence }
        );
      }
    },
  });
}

/**
 * Prefetch evidence for a given traceId
 */
export function usePrefetchEvidence() {
  const queryClient = useQueryClient();

  return (traceId: string) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.evidence(traceId),
      queryFn: () => getEvidence(traceId),
      staleTime: 1000 * 60 * 5,
    });
  };
}

// ============================================================
// Sensor Hooks
// ============================================================

/**
 * Sensor readings hook - polls every 5 seconds for live data
 */
export function useSensorReadings(limit = 60, offset = 0, enabled = true) {
  return useQuery({
    queryKey: queryKeys.sensorReadings(limit, offset),
    queryFn: () => getSensorReadings(limit, offset),
    enabled,
    refetchInterval: 5000, // 5 seconds for live updates
    staleTime: 2000, // 2 seconds
  });
}

/**
 * Sensor patterns hook - cached for 1 minute
 */
export function useSensorPatterns(limit = 10) {
  return useQuery({
    queryKey: queryKeys.sensorPatterns(limit),
    queryFn: () => getSensorPatterns(limit),
    staleTime: 1000 * 60, // 1 minute
  });
}

/**
 * Sensor events hook - cached for 1 minute
 */
export function useSensorEvents(limit = 20) {
  return useQuery({
    queryKey: queryKeys.sensorEvents(limit),
    queryFn: () => getSensorEvents(limit),
    staleTime: 1000 * 60, // 1 minute
  });
}

/**
 * Sensor readings range hook - for historical data with sampling
 */
export function useSensorReadingsRange(hours = 1, samples = 200, enabled = true) {
  return useQuery({
    queryKey: queryKeys.sensorReadingsRange(hours, samples),
    queryFn: () => getSensorReadingsRange(hours, samples),
    enabled,
    staleTime: 1000 * 60, // 1 minute - historical data doesn't change frequently
  });
}

// ============================================================
// 이기종 결합 예측 Hooks
// ============================================================

/**
 * Realtime predictions hook - 온톨로지 기반 에러 예측
 * Axia80 센서 패턴 + UR5e 온톨로지 결합
 */
export function usePredictions(limit = 10, enabled = true) {
  return useQuery({
    queryKey: queryKeys.predictions(limit),
    queryFn: () => getPredictions(limit),
    enabled,
    refetchInterval: 10000, // 10 seconds - 예측은 자주 갱신
    staleTime: 5000, // 5 seconds
  });
}

// ============================================================
// 온톨로지 그래프 탐색 Hooks (팔란티어 스타일)
// ============================================================

/**
 * 전체 온톨로지 엔티티 목록 조회
 * 그래프 탐색의 시작점을 선택하기 위한 엔티티 목록
 */
export function useOntologyEntities(enabled = true) {
  return useQuery({
    queryKey: queryKeys.ontologyEntities,
    queryFn: getOntologyEntities,
    enabled,
    staleTime: 1000 * 60 * 10, // 10 minutes - 온톨로지는 자주 변경되지 않음
  });
}

/**
 * 특정 엔티티의 상세 정보 조회
 */
export function useOntologyEntity(entityId: string | null, enabled = true) {
  return useQuery({
    queryKey: queryKeys.ontologyEntity(entityId || ''),
    queryFn: () => getOntologyEntity(entityId!),
    enabled: enabled && !!entityId,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}

/**
 * 이웃 노드 조회 (1-hop 탐색)
 * 클릭한 노드의 직접 연결된 이웃들을 반환
 */
export function useOntologyNeighbors(
  entityId: string | null,
  direction: 'outgoing' | 'incoming' | 'both' = 'both',
  enabled = true
) {
  return useQuery({
    queryKey: queryKeys.ontologyNeighbors(entityId || '', direction),
    queryFn: () => getOntologyNeighbors(entityId!, direction),
    enabled: enabled && !!entityId,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}

/**
 * 서브그래프 조회 (팔란티어 스타일 그래프 탐색)
 * 중심 노드에서 depth만큼 확장된 서브그래프를 반환
 */
export function useOntologyGraph(
  centerId: string | null,
  depth: number = 2,
  direction: 'outgoing' | 'incoming' | 'both' = 'both',
  enabled = true
) {
  return useQuery({
    queryKey: queryKeys.ontologyGraph(centerId || '', depth, direction),
    queryFn: () => getOntologyGraph(centerId!, depth, direction),
    enabled: enabled && !!centerId,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}
