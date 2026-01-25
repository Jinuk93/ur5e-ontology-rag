'use client';

import { useMemo, useState } from 'react';
import { Loader2, Radio, RefreshCw, Bell, BellOff, Volume2, VolumeX, Info } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { RiskAlertBar } from './RiskAlertBar';
import { ObjectCard } from './ObjectCard';
import { EventDetectionCard } from './EventDetectionCard';
import { RealtimeChart } from './RealtimeChart';
import { EventList, EventItem } from './EventList';
import { StatisticsSummary } from './StatisticsSummary';
import { CorrelationTable } from './CorrelationTable';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useUIStore } from '@/stores/uiStore';
import { useAlertStore } from '@/stores/alertStore';
import { useEventResolveStore } from '@/stores/eventResolveStore';
import { useSensorReadings, useSensorEvents, usePredictions } from '@/hooks/useApi';
import { useSensorSSE, useIntegratedSSE } from '@/hooks/useSSE';
import { useAnomalyAlert } from '@/hooks/useAnomalyAlert';
import type { EntityInfo, RiskAlert, SensorReading, NodeState } from '@/types/api';

// Entity configuration (names/descriptions come from i18n)
const entityConfigs = [
  { id: 'ur5e', type: 'ROBOT' as const },
  { id: 'axia80', type: 'SENSOR' as const },
  { id: 'fz', type: 'MEASUREMENT_AXIS' as const, unit: 'N', normalRange: [-60, 0] as [number, number] },
  { id: 'fx', type: 'MEASUREMENT_AXIS' as const, unit: 'N', normalRange: [-10, 10] as [number, number] },
  { id: 'fy', type: 'MEASUREMENT_AXIS' as const, unit: 'N', normalRange: [-10, 10] as [number, number] },
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
  const { settings, updateSettings, detectedEvents } = useAlertStore();
  const { resolvedEventIds } = useEventResolveStore();
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

  // 이기종 결합 예측 데이터
  const { data: predictionsData } = usePredictions(10);

  // 통합 SSE (UR5e + Axia80 상관분석)
  const {
    data: integratedData,
    latestData: latestIntegratedData,
    isConnected: integratedConnected,
  } = useIntegratedSSE({
    interval: 0.5,
    bufferSize: 60,
    enabled: streamMode === 'sse',
  });

  // 이상 감지 알림 시스템
  useAnomalyAlert(latestIntegratedData);

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

  // Build entities with i18n names/descriptions
  const baseEntities: EntityInfo[] = useMemo(() => {
    return entityConfigs.map((config) => {
      // detail은 MEASUREMENT_AXIS 타입에만 있음
      const hasDetail = config.type === 'MEASUREMENT_AXIS';
      return {
        id: config.id,
        name: t(`entities.${config.id}.name`),
        description: t(`entities.${config.id}.description`),
        detail: hasDetail ? t(`entities.${config.id}.detail`) : undefined,
        type: config.type,
        state: 'normal' as NodeState,
        unit: config.unit,
        normalRange: config.normalRange,
        currentValue: config.type === 'MEASUREMENT_AXIS' ? 0 : undefined,
      };
    });
  }, [t]);

  // Derive entity states from latest reading
  const entities: EntityInfo[] = useMemo(() => {
    const latestReading = readings[readings.length - 1];
    if (!latestReading) return baseEntities;

    return baseEntities.map((entity) => {
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
  }, [readings, baseEntities]);

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

  // Convert API events to EventItem (alerts보다 먼저 정의)
  const events: EventItem[] = useMemo(() => {
    if (!eventsData?.events) return [];
    return eventsData.events.map((e) => ({
      id: e.event_id,
      timestamp: e.start_time,
      type: e.error_code ? 'critical' : 'warning',
      eventType: e.event_type,
      message: e.description,
      errorCode: e.error_code || undefined,
      entityId: e.event_type === 'collision' ? 'fz' : undefined,
      context: {
        fzPeakN: (e as unknown as { context?: { fz_peak_N?: number } }).context?.fz_peak_N,
        fzValueN: (e as unknown as { context?: { fz_value_N?: number } }).context?.fz_value_N,
        shift: (e as unknown as { context?: { shift?: string } }).context?.shift,
        product: (e as unknown as { context?: { product?: string } }).context?.product,
      },
    }));
  }, [eventsData]);

  // Generate alerts from current state + events (이벤트 감지 연동)
  const alerts: RiskAlert[] = useMemo(() => {
    const result: RiskAlert[] = [];

    // 센서 상태 기반
    const criticalEntities = enrichedEntities.filter((e) => e.state === 'critical');
    const warningEntities = enrichedEntities.filter((e) => e.state === 'warning');

    // 이벤트 기반 (미해결 이벤트만 카운트)
    const unresolvedEvents = events.filter((e) => !resolvedEventIds.has(e.id));
    const criticalEvents = unresolvedEvents.filter((e) => e.type === 'critical');
    const warningEvents = unresolvedEvents.filter((e) => e.type === 'warning');

    // EventDetectionCard 상태 결정 (이벤트 기반)
    const eventCardStatus = criticalEvents.length > 0 ? 'critical' : warningEvents.length > 0 ? 'warning' : 'normal';

    // 긴급 (센서 + EventDetectionCard가 critical이면 +1)
    const criticalCount = criticalEntities.length + (eventCardStatus === 'critical' ? 1 : 0);
    if (criticalCount > 0) {
      result.push({
        id: 'critical',
        severity: 'critical',
        title: criticalEntities.length > 0
          ? `${criticalEntities.map((e) => e.name).join(', ')} 위험`
          : `이벤트 ${criticalEvents.length}건`,
        timestamp: new Date().toISOString(),
        entityId: criticalEntities[0]?.id,
        count: criticalCount,
      });
    }

    // 경고 (센서 + EventDetectionCard가 warning이면 +1)
    const warningCount = warningEntities.length + (eventCardStatus === 'warning' ? 1 : 0);
    if (warningCount > 0) {
      result.push({
        id: 'warning',
        severity: 'warning',
        title: warningEntities.length > 0
          ? `${warningEntities.map((e) => e.name).join(', ')} 경고`
          : `이벤트 ${warningEvents.length}건`,
        timestamp: new Date().toISOString(),
        entityId: warningEntities[0]?.id,
        count: warningCount,
      });
    }

    // 정상 (센서 + EventDetectionCard가 normal이면 +1)
    const normalCount = enrichedEntities.filter((e) => e.state === 'normal').length + (eventCardStatus === 'normal' ? 1 : 0);
    result.push({
      id: 'normal',
      severity: 'info',
      title: '정상 동작',
      timestamp: new Date().toISOString(),
      count: normalCount,
    });

    return result;
  }, [enrichedEntities, events, resolvedEventIds]);

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
      <RiskAlertBar
        alerts={alerts}
        onAlertClick={handleAlertClick}
        entityNamesBySeverity={(() => {
          // 이벤트 기반 (미해결 이벤트만 카운트)
          const unresolvedEvents = events.filter((e) => !resolvedEventIds.has(e.id));
          const criticalEvents = unresolvedEvents.filter((e) => e.type === 'critical');
          const warningEvents = unresolvedEvents.filter((e) => e.type === 'warning');
          const eventCardStatus = criticalEvents.length > 0 ? 'critical' : warningEvents.length > 0 ? 'warning' : 'normal';

          // 센서 카드별 상태
          const criticalNames = enrichedEntities.filter((e) => e.state === 'critical').map((e) => e.name);
          const warningNames = enrichedEntities.filter((e) => e.state === 'warning').map((e) => e.name);
          const normalNames = enrichedEntities.filter((e) => e.state === 'normal').map((e) => e.name);

          // 이벤트 감지 카드 상태에 따라 추가
          if (eventCardStatus === 'critical') {
            criticalNames.push('이벤트 감지');
          } else if (eventCardStatus === 'warning') {
            warningNames.push('이벤트 감지');
          } else {
            normalNames.push('이벤트 감지');
          }

          return {
            critical: criticalNames,
            warning: warningNames,
            normal: normalNames,
          };
        })()}
      />

      {/* Main Content */}
      <div className="flex-1 p-4 overflow-auto">
        {/* Stream Mode Toggle + Title */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
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
            <span className="text-sm font-medium text-slate-300">{t('title')}</span>
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
          <div className="flex items-center gap-2">
            {/* Alert Settings Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => updateSettings({ toastEnabled: !settings.toastEnabled })}
              className={settings.toastEnabled ? 'text-green-400' : 'text-slate-500'}
              title={settings.toastEnabled ? '알림 끄기' : '알림 켜기'}
            >
              {settings.toastEnabled ? (
                <Bell className="h-4 w-4" />
              ) : (
                <BellOff className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => updateSettings({ soundEnabled: !settings.soundEnabled })}
              className={settings.soundEnabled ? 'text-green-400' : 'text-slate-500'}
              title={settings.soundEnabled ? '소리 끄기' : '소리 켜기'}
            >
              {settings.soundEnabled ? (
                <Volume2 className="h-4 w-4" />
              ) : (
                <VolumeX className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={toggleStreamMode}
              className="text-xs"
            >
              {streamMode === 'sse' ? t('switchToPolling') : t('switchToSse')}
            </Button>
          </div>
        </div>

        {/* Connection Status */}
        {isError && (
          <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-sm text-yellow-400">
            {t('sensorLoadError')}
          </div>
        )}

        {/* Entity Cards */}
        <div className="mb-4">
          <div className="flex flex-wrap gap-3">
            {enrichedEntities.map((entity) => (
              <ObjectCard
                key={entity.id}
                entity={entity}
                isSelected={selectedEntity?.id === entity.id}
                onClick={() => handleEntityClick(entity)}
              />
            ))}
            {/* 이벤트 감지 카드 - 실제 발생한 이벤트 (충돌/과부하/드리프트) */}
            <EventDetectionCard events={events} />
          </div>
        </div>

        {/* 시스템 구분선 - 모니터링 객체와 통합 운영 현황 사이 */}
        <div className="my-6 border-t border-slate-700/50" />

        {/* Statistics Summary - 통합 운영 현황 (차트 위에 배치) */}
        <StatisticsSummary
          sseReadings={readings}
          integratedData={integratedData}
          latestIntegratedData={latestIntegratedData}
          events={events}
          predictions={
            predictionsData?.predictions
              ? {
                  total_patterns: predictionsData.predictions.length,
                  high_risk_count: predictionsData.predictions.filter(
                    (p) => p.risk_level === 'high' || p.risk_level === 'critical'
                  ).length,
                }
              : undefined
          }
        />

        {/* 구분선 - 통합 운영 현황과 차트 사이 */}
        <div className="my-6 border-t border-slate-700/50" />

        {/* Chart - UR5e + Axia80 통합 모니터링 */}
        {/* Demo notice - 차트 바깥에 표시 */}
        <div className="flex items-center gap-1.5 mb-2">
          <Info className="h-3.5 w-3.5 text-red-400 shrink-0" />
          <span className="text-xs text-red-400">
            데모 버전: 2024-01-15 ~ 2024-01-21 (7일) 샘플 데이터가 제공됩니다.
          </span>
        </div>

        <div className="mb-6">
          <RealtimeChart
            data={readings}
            integratedData={integratedData}
            axes={['Fz', 'Fx', 'Fy', 'tcp_speed', 'joint_torque_sum', 'joint_current_avg']}
            thresholds={{
              warning: -60,
              critical: -200,
            }}
          />
        </div>

        {/* 구분선 - 차트와 이벤트 리스트 사이 */}
        <div className="my-6 border-t border-slate-700/50" />

        {/* Events */}
        <EventList
          events={events}
          predictions={predictionsData?.predictions}
          onEventClick={handleEventClick}
          maxHeight="350px"
        />

        {/* 구분선 - 이벤트 리스트와 상관분석 사이 */}
        <div className="my-6 border-t border-slate-700/50" />

        {/* UR5e + Axia80 실시간 상관분석 (Simulated) */}
        <CorrelationTable
          data={integratedData}
          latestData={latestIntegratedData}
          isConnected={integratedConnected}
          maxHeight="300px"
        />
      </div>
    </div>
  );
}
