'use client';

import { useMemo, useState } from 'react';
import { Loader2, Radio, RefreshCw } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { RiskAlertBar } from './RiskAlertBar';
import { ObjectCard } from './ObjectCard';
import { RealtimeChart } from './RealtimeChart';
import { EventList, EventItem } from './EventList';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useUIStore } from '@/stores/uiStore';
import { useSensorReadings, useSensorEvents } from '@/hooks/useApi';
import { useSensorSSE } from '@/hooks/useSSE';
import type { EntityInfo, RiskAlert, SensorReading, NodeState } from '@/types/api';

// Static entities (could be fetched from ontology API in future)
const staticEntities: EntityInfo[] = [
  {
    id: 'ur5e',
    name: 'UR5e',
    type: 'ROBOT',
    state: 'normal',
  },
  {
    id: 'axia80',
    name: 'Axia80',
    type: 'SENSOR',
    state: 'normal',
  },
  {
    id: 'fz',
    name: 'Fz',
    type: 'MEASUREMENT_AXIS',
    state: 'normal',
    currentValue: 0,
    unit: 'N',
    normalRange: [-60, 0],
  },
  {
    id: 'fx',
    name: 'Fx',
    type: 'MEASUREMENT_AXIS',
    state: 'normal',
    currentValue: 0,
    unit: 'N',
    normalRange: [-10, 10],
  },
  {
    id: 'fy',
    name: 'Fy',
    type: 'MEASUREMENT_AXIS',
    state: 'normal',
    currentValue: 0,
    unit: 'N',
    normalRange: [-10, 10],
  },
];

function deriveEntityState(value: number, normalRange: [number, number]): NodeState {
  const [min, max] = normalRange;
  if (value < min * 3 || value > max * 3) return 'critical';
  if (value < min || value > max) return 'warning';
  return 'normal';
}

type StreamMode = 'sse' | 'polling';

export function LiveView() {
  const t = useTranslations('live');
  const { selectedEntity, setSelectedEntity, setGraphCenterNode, setCurrentView } = useUIStore();
  const [streamMode, setStreamMode] = useState<StreamMode>('sse');

  // SSE mode
  const {
    readings: sseReadings,
    isConnected: sseConnected,
    error: sseError,
    reconnect: sseReconnect,
  } = useSensorSSE({
    interval: 1.0,
    bufferSize: 60,
    enabled: streamMode === 'sse',
  });

  // Polling mode (fallback)
  const {
    data: pollingData,
    isLoading: pollingLoading,
    isError: pollingError,
  } = useSensorReadings(60, 0, streamMode === 'polling');

  const { data: eventsData } = useSensorEvents(10);

  // Convert polling API response to SensorReading array
  const pollingReadings: SensorReading[] = useMemo(() => {
    if (!pollingData?.readings) return [];
    return pollingData.readings.map((r) => ({
      timestamp: r.timestamp,
      Fx: r.Fx,
      Fy: r.Fy,
      Fz: r.Fz,
      Tx: r.Tx,
      Ty: r.Ty,
      Tz: r.Tz,
    }));
  }, [pollingData]);

  // Use readings based on stream mode
  const readings = streamMode === 'sse' ? sseReadings : pollingReadings;
  const isLoading = streamMode === 'polling' && pollingLoading;
  const isError = streamMode === 'sse' ? !!sseError : pollingError;
  const isConnected = streamMode === 'sse' ? sseConnected : !pollingError;

  // Derive entity states from latest reading
  const entities: EntityInfo[] = useMemo(() => {
    const latestReading = readings[readings.length - 1];
    if (!latestReading) return staticEntities;

    return staticEntities.map((entity) => {
      if (entity.type !== 'MEASUREMENT_AXIS') return entity;

      const axisKey = entity.id.charAt(0).toUpperCase() + entity.id.slice(1) as keyof SensorReading;
      const value = latestReading[axisKey] as number;

      if (typeof value !== 'number') return entity;

      const state = entity.normalRange
        ? deriveEntityState(value, entity.normalRange as [number, number])
        : 'normal';

      return {
        ...entity,
        currentValue: Math.round(value * 10) / 10,
        state,
      };
    });
  }, [readings]);

  // Derive sensor state for Axia80 card
  const sensorState: NodeState = useMemo(() => {
    const hasWarning = entities.some((e) => e.state === 'warning');
    const hasCritical = entities.some((e) => e.state === 'critical');
    if (hasCritical) return 'critical';
    if (hasWarning) return 'warning';
    return 'normal';
  }, [entities]);

  // Update Axia80 sensor state
  const enrichedEntities = useMemo(() => {
    return entities.map((e) =>
      e.id === 'axia80' ? { ...e, state: sensorState } : e
    );
  }, [entities, sensorState]);

  // Generate alerts from current state
  const alerts: RiskAlert[] = useMemo(() => {
    const result: RiskAlert[] = [];

    const criticalEntities = enrichedEntities.filter((e) => e.state === 'critical');
    const warningEntities = enrichedEntities.filter((e) => e.state === 'warning');

    if (criticalEntities.length > 0) {
      result.push({
        id: 'critical',
        severity: 'critical',
        title: `${criticalEntities.map((e) => e.name).join(', ')} 위험`,
        timestamp: new Date().toISOString(),
        entityId: criticalEntities[0].id,
        count: criticalEntities.length,
      });
    }

    if (warningEntities.length > 0) {
      result.push({
        id: 'warning',
        severity: 'warning',
        title: `${warningEntities.map((e) => e.name).join(', ')} 경고`,
        timestamp: new Date().toISOString(),
        entityId: warningEntities[0].id,
        count: warningEntities.length,
      });
    }

    if (result.length === 0) {
      result.push({
        id: 'normal',
        severity: 'info',
        title: '정상 동작',
        timestamp: new Date().toISOString(),
        count: enrichedEntities.length,
      });
    }

    return result;
  }, [enrichedEntities]);

  // Convert API events to EventItem
  const events: EventItem[] = useMemo(() => {
    if (!eventsData?.events) return [];
    return eventsData.events.map((e) => ({
      id: e.event_id,
      timestamp: e.start_time,
      type: e.error_code ? 'critical' : 'warning',
      message: e.description,
      entityId: e.event_type === 'collision' ? 'fz' : undefined,
    }));
  }, [eventsData]);

  const handleEntityClick = (entity: EntityInfo) => {
    setSelectedEntity(entity);
  };

  const handleAlertClick = (alert: RiskAlert) => {
    if (alert.entityId) {
      const entity = enrichedEntities.find((e) => e.id === alert.entityId);
      if (entity) {
        setSelectedEntity(entity);
      }
    }
  };

  const handleEventClick = (event: EventItem) => {
    if (event.entityId) {
      setGraphCenterNode(event.entityId);
      setCurrentView('graph');
    }
  };

  const toggleStreamMode = () => {
    setStreamMode((prev) => (prev === 'sse' ? 'polling' : 'sse'));
  };

  if (isLoading && readings.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
        <span className="ml-2 text-slate-400">{t('sensorLoading')}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Alert Bar */}
      <RiskAlertBar alerts={alerts} onAlertClick={handleAlertClick} />

      {/* Main Content */}
      <div className="flex-1 p-4 overflow-auto">
        {/* Stream Mode Toggle */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={
                isConnected
                  ? 'text-green-400 border-green-600/50'
                  : 'text-red-400 border-red-600/50'
              }
            >
              {streamMode === 'sse' ? (
                <Radio className="h-3 w-3 mr-1" />
              ) : (
                <RefreshCw className="h-3 w-3 mr-1" />
              )}
              {streamMode === 'sse' ? t('sseMode') : t('pollingMode')}
            </Badge>
            {streamMode === 'sse' && !sseConnected && (
              <Button
                variant="ghost"
                size="sm"
                onClick={sseReconnect}
                className="text-xs text-slate-400 hover:text-white"
              >
                {t('reconnect')}
              </Button>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={toggleStreamMode}
            className="text-xs"
          >
            {streamMode === 'sse' ? t('switchToPolling') : t('switchToSse')}
          </Button>
        </div>

        {/* Connection Status */}
        {isError && (
          <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-sm text-yellow-400">
            {t('sensorLoadError')}
          </div>
        )}

        {/* Entity Cards */}
        <div className="mb-6">
          <h2 className="text-sm font-medium text-slate-400 mb-3">{t('title')}</h2>
          <div className="flex flex-wrap gap-3">
            {enrichedEntities.map((entity) => (
              <ObjectCard
                key={entity.id}
                entity={entity}
                isSelected={selectedEntity?.id === entity.id}
                onClick={() => handleEntityClick(entity)}
              />
            ))}
          </div>
        </div>

        {/* Chart */}
        <div className="mb-6">
          <RealtimeChart
            data={readings}
            axis="Fz"
            title={t('chartTitle')}
            thresholds={{
              warning: -60,
              critical: -200,
            }}
          />
        </div>

        {/* Events */}
        <EventList
          events={events}
          onEventClick={handleEventClick}
          maxHeight="200px"
        />
      </div>
    </div>
  );
}
