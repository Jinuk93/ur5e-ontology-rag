/**
 * SSE (Server-Sent Events) Hook for real-time sensor data
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import type { SensorReading } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8002';

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

  // Keep ref in sync with effect
  useEffect(() => {
    isEnabledRef.current = enabled;
  }, [enabled]);

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

        setLatestReading(data);
        setReadings((prev) => {
          const newReadings = [...prev, data];
          if (newReadings.length > bufferSize) {
            return newReadings.slice(-bufferSize);
          }
          return newReadings;
        });

        onData?.(data);
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
      onError?.(err);

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
  }, [enabled, interval, bufferSize, onData, onError, reconnectTrigger]);

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
