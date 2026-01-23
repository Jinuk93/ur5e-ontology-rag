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
} from '@/lib/api';
import type { ChatRequest, ChatResponse } from '@/types/api';

// Query Keys
export const queryKeys = {
  health: ['health'] as const,
  ontologySummary: ['ontology', 'summary'] as const,
  evidence: (traceId: string) => ['evidence', traceId] as const,
  sensorReadings: (limit: number, offset: number) => ['sensors', 'readings', limit, offset] as const,
  sensorReadingsRange: (hours: number, samples: number) => ['sensors', 'readings', 'range', hours, samples] as const,
  sensorPatterns: (limit: number) => ['sensors', 'patterns', limit] as const,
  sensorEvents: (limit: number) => ['sensors', 'events', limit] as const,
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
