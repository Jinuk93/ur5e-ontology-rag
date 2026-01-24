/**
 * SSE (Server-Sent Events) Hook for real-time sensor data
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import type { SensorReading, IntegratedStreamData } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export interface SSEReading extends SensorReading {
  cursor?: number;
  total?: number;
}

export interface UseSSEOptions {
  /** Data transmission interval in seconds (default: 1.0) */
  interval?: number;
  /** Maximum number of readings to keep in buffer (default: 60) */
  bufferSize?: number;
  /** Enable/disable SSE connection (default: true) */
  enabled?: boolean;
  /** Callback when new data arrives */
  onData?: (reading: SSEReading) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseSSEResult {
  /** Current readings buffer */
  readings: SSEReading[];
  /** Latest single reading */
  latestReading: SSEReading | null;
  /** Connection status */
  isConnected: boolean;
  /** Error state */
  error: Error | null;
  /** Manually reconnect */
  reconnect: () => void;
  /** Manually disconnect */
  disconnect: () => void;
}

export function useSensorSSE(options: UseSSEOptions = {}): UseSSEResult {
  const {
    interval = 1.0,
    bufferSize = 60,
    enabled = true,
    onData,
    onError,
  } = options;

  const [readings, setReadings] = useState<SSEReading[]>([]);
  const [latestReading, setLatestReading] = useState<SSEReading | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [reconnectTrigger, setReconnectTrigger] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isEnabledRef = useRef(enabled);
  // Use refs for callbacks to avoid re-creating connection on every render
  const onDataRef = useRef(onData);
  const onErrorRef = useRef(onError);

  // Keep refs in sync
  useEffect(() => {
    isEnabledRef.current = enabled;
    onDataRef.current = onData;
    onErrorRef.current = onError;
  }, [enabled, onData, onError]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    setReconnectTrigger((prev) => prev + 1);
  }, [disconnect]);

  // Main connection effect
  useEffect(() => {
    if (!enabled) {
      // Cleanup handled in return
      return () => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };
    }

    const url = `${API_BASE_URL}/api/sensors/stream?interval=${interval}`;
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SSEReading;

        if ('error' in data) {
          setError(new Error(String(data.error)));
          return;
        }

        // Clear error on successful data reception
        setError(null);
        setLatestReading(data);
        setReadings((prev) => {
          const newReadings = [...prev, data];
          if (newReadings.length > bufferSize) {
            return newReadings.slice(-bufferSize);
          }
          return newReadings;
        });

        onDataRef.current?.(data);
      } catch (e) {
        console.error('SSE parse error:', e);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();
      eventSourceRef.current = null;

      const err = new Error('SSE connection lost');
      setError(err);
      onErrorRef.current?.(err);

      // Schedule reconnect
      reconnectTimeoutRef.current = setTimeout(() => {
        if (isEnabledRef.current) {
          setReconnectTrigger((prev) => prev + 1);
        }
      }, 3000);
    };

    eventSourceRef.current = eventSource;

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [enabled, interval, bufferSize, reconnectTrigger]);

  // Derive connected state - if disabled, always false
  const effectiveIsConnected = enabled ? isConnected : false;

  return {
    readings,
    latestReading,
    isConnected: effectiveIsConnected,
    error,
    reconnect,
    disconnect,
  };
}


// ============================================================
// Phase 3: 통합 SSE 훅 (UR5e + Axia80 상관분석)
// ============================================================

export interface UseIntegratedSSEOptions {
  /** Data transmission interval in seconds (default: 0.5) */
  interval?: number;
  /** Maximum number of readings to keep in buffer (default: 60) */
  bufferSize?: number;
  /** Enable/disable SSE connection (default: true) */
  enabled?: boolean;
  /** Callback when new data arrives */
  onData?: (data: IntegratedStreamData) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseIntegratedSSEResult {
  /** Current data buffer */
  data: IntegratedStreamData[];
  /** Latest single reading */
  latestData: IntegratedStreamData | null;
  /** Connection status */
  isConnected: boolean;
  /** Error state */
  error: Error | null;
  /** Manually reconnect */
  reconnect: () => void;
  /** Manually disconnect */
  disconnect: () => void;
}

/**
 * 통합 SSE 훅 - UR5e + Axia80 실시간 상관분석 데이터
 *
 * 시나리오 기반 시뮬레이션 데이터를 제공합니다:
 * - Axia80: 힘/토크 센서
 * - UR5e: TCP 속도, 조인트 토크, 전류, 안전 모드
 * - Correlation: 토크/힘 비율, 속도-힘 상관계수
 * - Risk: 접촉/충돌 위험 점수
 */
export function useIntegratedSSE(options: UseIntegratedSSEOptions = {}): UseIntegratedSSEResult {
  const {
    interval = 0.5,
    bufferSize = 60,
    enabled = true,
    onData,
    onError,
  } = options;

  const [data, setData] = useState<IntegratedStreamData[]>([]);
  const [latestData, setLatestData] = useState<IntegratedStreamData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [reconnectTrigger, setReconnectTrigger] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isEnabledRef = useRef(enabled);
  // Use refs for callbacks to avoid re-creating connection on every render
  const onDataRef = useRef(onData);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    isEnabledRef.current = enabled;
    onDataRef.current = onData;
    onErrorRef.current = onError;
  }, [enabled, onData, onError]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    setReconnectTrigger((prev) => prev + 1);
  }, [disconnect]);

  useEffect(() => {
    if (!enabled) {
      return () => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };
    }

    const url = `${API_BASE_URL}/api/sensors/stream/integrated?interval=${interval}`;
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    eventSource.onmessage = (event) => {
      try {
        const streamData = JSON.parse(event.data) as IntegratedStreamData;

        if ('error' in streamData) {
          setError(new Error(String((streamData as unknown as { error: string }).error)));
          return;
        }

        // Clear error on successful data reception
        setError(null);
        setLatestData(streamData);
        setData((prev) => {
          const newData = [...prev, streamData];
          if (newData.length > bufferSize) {
            return newData.slice(-bufferSize);
          }
          return newData;
        });

        onDataRef.current?.(streamData);
      } catch (e) {
        console.error('Integrated SSE parse error:', e);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();
      eventSourceRef.current = null;

      const err = new Error('Integrated SSE connection lost');
      setError(err);
      onErrorRef.current?.(err);

      reconnectTimeoutRef.current = setTimeout(() => {
        if (isEnabledRef.current) {
          setReconnectTrigger((prev) => prev + 1);
        }
      }, 3000);
    };

    eventSourceRef.current = eventSource;

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [enabled, interval, bufferSize, reconnectTrigger]);

  const effectiveIsConnected = enabled ? isConnected : false;

  return {
    data,
    latestData,
    isConnected: effectiveIsConnected,
    error,
    reconnect,
    disconnect,
  };
}
