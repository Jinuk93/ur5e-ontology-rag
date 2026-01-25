'use client';

import { useMemo } from 'react';
import {
  Activity, AlertTriangle, CheckCircle, XCircle, Minus,
  Wrench, Sparkles, Zap, Gauge, RotateCcw, Info, ArrowRight, Brain
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSensorReadingsRange, useSensorEvents } from '@/hooks/useApi';
import { useEventResolveStore } from '@/stores/eventResolveStore';
import type { SensorReading, IntegratedStreamData } from '@/types/api';
import type { EventItem } from './EventList';

interface StatisticsSummaryProps {
  sseReadings?: SensorReading[];
  integratedData?: IntegratedStreamData[];
  latestIntegratedData?: IntegratedStreamData | null;
  events?: EventItem[];
  predictions?: {
    total_patterns: number;
    high_risk_count: number;
  };
}

export function StatisticsSummary({
  sseReadings = [],
  integratedData = [],
  latestIntegratedData,
  events = [],
  predictions
}: StatisticsSummaryProps) {
  const { resolvedEventIds } = useEventResolveStore();

  const { data: dayRangeData } = useSensorReadingsRange(24, 500);
  const { data: eventsData } = useSensorEvents(500);

  const stats = useMemo(() => {
    // === 실시간 값 (SSE) ===
    const latestSSE = sseReadings[sseReadings.length - 1];
    const fzLive = latestSSE?.Fz ?? null;
    const fxLive = latestSSE?.Fx ?? null;
    const fyLive = latestSSE?.Fy ?? null;
    const forceMagLive = (fxLive != null && fyLive != null && fzLive != null)
      ? Math.sqrt(fxLive * fxLive + fyLive * fyLive + fzLive * fzLive)
      : null;

    // === UR5e 실시간 값 ===
    const tcpSpeedLive = latestIntegratedData?.ur5e?.tcp_speed ?? null;
    const jointTorqueLive = latestIntegratedData?.ur5e?.joint_torque_sum ?? null;
    const jointCurrentLive = latestIntegratedData?.ur5e?.joint_current_avg ?? null;

    // UR5e 힘 크기 (통합 스트림에서)
    const ur5eForceMagLive = latestIntegratedData?.axia80
      ? Math.sqrt(
          (latestIntegratedData.axia80.Fx || 0) ** 2 +
          (latestIntegratedData.axia80.Fy || 0) ** 2 +
          (latestIntegratedData.axia80.Fz || 0) ** 2
        )
      : null;

    // === 24시간 평균 (7일 평균은 제거) ===
    const dayReadings = dayRangeData?.readings || [];

    const calcAvg = (arr: number[]) => arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
    const calcP95 = (arr: number[]) => {
      if (arr.length === 0) return 0;
      const sorted = [...arr].sort((a, b) => a - b);
      return sorted[Math.floor(sorted.length * 0.95)] || 0;
    };

    const fzValues24h = dayReadings.map(r => r.Fz).filter((v): v is number => typeof v === 'number');
    const fxValues24h = dayReadings.map(r => r.Fx).filter((v): v is number => typeof v === 'number');
    const fyValues24h = dayReadings.map(r => r.Fy).filter((v): v is number => typeof v === 'number');

    const fzAvg24h = calcAvg(fzValues24h);
    const fxAvg24h = calcAvg(fxValues24h);
    const fyAvg24h = calcAvg(fyValues24h);

    const calcForceMag = (fx: number, fy: number, fz: number) => Math.sqrt(fx * fx + fy * fy + fz * fz);
    const forceMag24h = dayReadings.map(r => calcForceMag(r.Fx, r.Fy, r.Fz)).filter(v => Number.isFinite(v));

    const forceMagAvg24h = calcAvg(forceMag24h);
    const forceMagP95_24h = calcP95(forceMag24h);

    // UR5e 평균 (버퍼 기반)
    const tcpSpeedValues = integratedData.map(d => d.ur5e?.tcp_speed).filter((v): v is number => typeof v === 'number');
    const jointTorqueValues = integratedData.map(d => d.ur5e?.joint_torque_sum).filter((v): v is number => typeof v === 'number');
    const jointCurrentValues = integratedData.map(d => d.ur5e?.joint_current_avg).filter((v): v is number => typeof v === 'number');
    const ur5eForceMagValues = integratedData.map(d => {
      if (!d.axia80) return null;
      return Math.sqrt((d.axia80.Fx || 0) ** 2 + (d.axia80.Fy || 0) ** 2 + (d.axia80.Fz || 0) ** 2);
    }).filter((v): v is number => v !== null && Number.isFinite(v));

    const tcpSpeedAvg = calcAvg(tcpSpeedValues);
    const jointTorqueAvg = calcAvg(jointTorqueValues);
    const jointCurrentAvg = calcAvg(jointCurrentValues);
    const ur5eForceMagP95 = calcP95(ur5eForceMagValues);

    // === 정상률 계산: Fz + Fx + Fy + 이벤트 미발생 비율 ===
    // Fz: -60~0N, Fx: -10~10N, Fy: -10~10N 기준
    const fzNormalCount = fzValues24h.filter(v => v >= -60 && v <= 0).length;
    const fxNormalCount = fxValues24h.filter(v => v >= -10 && v <= 10).length;
    const fyNormalCount = fyValues24h.filter(v => v >= -10 && v <= 10).length;

    // 전체 센서 정상률 (3개 축 평균)
    const fzRate = fzValues24h.length > 0 ? (fzNormalCount / fzValues24h.length) * 100 : 100;
    const fxRate = fxValues24h.length > 0 ? (fxNormalCount / fxValues24h.length) * 100 : 100;
    const fyRate = fyValues24h.length > 0 ? (fyNormalCount / fyValues24h.length) * 100 : 100;

    // 이벤트 미발생 비율 (이벤트가 없을수록 높음)
    const eventPenalty = events.length > 0 ? Math.max(0, 100 - events.length * 5) : 100;

    // 종합 정상률: 센서 3개 평균(70%) + 이벤트 미발생률(30%)
    const sensorNormalRate = (fzRate + fxRate + fyRate) / 3;
    const normalRate24h = sensorNormalRate * 0.7 + eventPenalty * 0.3;

    // 현재 상태 판단 (전체 센서 기반)
    const fzOk = fzLive == null || (fzLive >= -60 && fzLive <= 0);
    const fxOk = fxLive == null || (fxLive >= -10 && fxLive <= 10);
    const fyOk = fyLive == null || (fyLive >= -10 && fyLive <= 10);
    const sensorStatus: 'good' | 'warning' | 'danger' | 'unknown' =
      fzLive == null && fxLive == null && fyLive == null ? 'unknown' :
      (fzOk && fxOk && fyOk) ? 'good' :
      (!fzOk && (fzLive! < -120 || fzLive! > 20)) ? 'danger' : 'warning';

    // 위험 평가
    const contactRisk = latestIntegratedData?.risk?.contact_risk_score ?? 0;
    const collisionRisk = latestIntegratedData?.risk?.collision_risk_score ?? 0;
    const riskScore = Math.max(contactRisk, collisionRisk);

    // === 이벤트 집계 ===
    const allEvents = events.length > 0 ? events : (eventsData?.events?.map(e => ({
      id: e.event_id,
      timestamp: e.start_time,
      type: e.error_code ? 'critical' : 'warning',
      eventType: e.event_type,
      message: e.description,
      errorCode: e.error_code || undefined,
    })) || []);

    const collisionEvents = allEvents.filter(e => e.eventType?.toLowerCase() === 'collision');
    const overloadEvents = allEvents.filter(e => e.eventType?.toLowerCase() === 'overload');
    const driftEvents = allEvents.filter(e => e.eventType?.toLowerCase().includes('drift'));

    const resolvedCount = allEvents.filter(e => resolvedEventIds.has(e.id)).length;
    const unresolvedCount = allEvents.length - resolvedCount;
    const unresolvedEvents = allEvents.filter(e => !resolvedEventIds.has(e.id));

    // === AI 분석 생성 (근거 포함) ===
    const aiAnalysis: {
      text: string;
      type: 'insight' | 'warning' | 'action';
      basis?: string;
    }[] = [];

    if (fzLive != null && fzAvg24h !== 0) {
      const trendDiff = Math.abs(fzLive) - Math.abs(fzAvg24h);
      if (trendDiff > 10) {
        aiAnalysis.push({
          text: `Fz 접촉력 ${Math.abs(trendDiff).toFixed(1)}N 증가 중`,
          type: 'warning',
          basis: `현재 ${Math.abs(fzLive).toFixed(1)}N vs 24시간 평균 ${Math.abs(fzAvg24h).toFixed(1)}N`
        });
      }
    }

    if (collisionEvents.length > 0) {
      aiAnalysis.push({
        text: `충돌 ${collisionEvents.length}건 → 작업 경로 점검 필요`,
        type: 'action',
        basis: collisionEvents.slice(0, 2).map(e => e.message || e.errorCode).join(', ')
      });
    }

    if (overloadEvents.length > 0) {
      aiAnalysis.push({
        text: `과부하 ${overloadEvents.length}건 → 페이로드 설정 확인`,
        type: 'action',
        basis: overloadEvents.slice(0, 2).map(e => e.message || e.errorCode).join(', ')
      });
    }

    if (jointTorqueLive != null && jointTorqueLive > 100) {
      aiAnalysis.push({
        text: `조인트 토크 과다 → 부하 점검 필요`,
        type: 'warning',
        basis: `현재 ${jointTorqueLive.toFixed(0)}Nm (정상: ≤80Nm)`
      });
    }

    if (normalRate24h < 90) {
      aiAnalysis.push({
        text: `${(100 - normalRate24h).toFixed(0)}% 정상 범위 초과 → 공정 점검`,
        type: normalRate24h < 70 ? 'action' : 'warning',
        basis: `Fz -60~0N 범위, 24시간 내 ${(100 - normalRate24h).toFixed(0)}% 초과`
      });
    }

    if (aiAnalysis.length === 0) {
      aiAnalysis.push({
        text: '모든 지표 정상 범위',
        type: 'insight',
        basis: '센서값, 이벤트, UR5e 상태 모두 정상'
      });
    }

    // Actions required
    const actions: { text: string; type: 'danger' | 'warning' | 'info' }[] = [];
    if (unresolvedCount > 0) {
      actions.push({
        text: `미해결 이벤트 ${unresolvedCount}건`,
        type: unresolvedCount > 3 ? 'danger' : 'warning'
      });
    }
    if (normalRate24h < 90) {
      actions.push({
        text: `${(100 - normalRate24h).toFixed(0)}% 정상 범위 초과`,
        type: normalRate24h < 70 ? 'danger' : 'warning'
      });
    }

    return {
      fzLive: fzLive != null ? Math.round(fzLive * 10) / 10 : null,
      fxLive: fxLive != null ? Math.round(fxLive * 10) / 10 : null,
      fyLive: fyLive != null ? Math.round(fyLive * 10) / 10 : null,
      forceMagLive: forceMagLive != null ? Math.round(forceMagLive * 10) / 10 : null,
      sensorStatus,
      fzAvg24h: Math.round(fzAvg24h * 10) / 10,
      fxAvg24h: Math.round(fxAvg24h * 10) / 10,
      fyAvg24h: Math.round(fyAvg24h * 10) / 10,
      forceMagAvg24h: Math.round(forceMagAvg24h * 10) / 10,
      forceMagP95_24h: Math.round(forceMagP95_24h * 10) / 10,
      normalRate24h: Math.round(normalRate24h * 10) / 10,
      // UR5e 힘 크기 (힘 피크용)
      ur5eForceMagLive: ur5eForceMagLive != null ? Math.round(ur5eForceMagLive * 10) / 10 : null,
      ur5eForceMagP95: Math.round(ur5eForceMagP95 * 10) / 10,
      tcpSpeedLive: tcpSpeedLive != null ? Math.round(tcpSpeedLive * 1000) : null,
      jointTorqueLive: jointTorqueLive != null ? Math.round(jointTorqueLive) : null,
      jointCurrentLive: jointCurrentLive != null ? Math.round(jointCurrentLive * 100) / 100 : null,
      tcpSpeedAvg: Math.round(tcpSpeedAvg * 1000),
      jointTorqueAvg: Math.round(jointTorqueAvg),
      jointCurrentAvg: Math.round(jointCurrentAvg * 100) / 100,
      riskScore: Math.round(riskScore * 100),
      totalEvents: allEvents.length,
      collisionTotal: collisionEvents.length,
      overloadTotal: overloadEvents.length,
      driftTotal: driftEvents.length,
      collisionEvents,
      overloadEvents,
      driftEvents,
      resolvedCount,
      unresolvedCount,
      unresolvedEvents,
      aiAnalysis,
      actions,
      sseBufferSize: sseReadings.length,
      integratedBufferSize: integratedData.length,
      sampleCount24h: dayReadings.length,
    };
  }, [sseReadings, integratedData, latestIntegratedData, events, dayRangeData, eventsData, resolvedEventIds]);

  const StatusIcon = ({ status }: { status: 'good' | 'warning' | 'danger' | 'unknown' }) => {
    if (status === 'good') return <CheckCircle className="h-4 w-4 text-green-400" />;
    if (status === 'warning') return <AlertTriangle className="h-4 w-4 text-yellow-400" />;
    if (status === 'danger') return <XCircle className="h-4 w-4 text-red-400" />;
    return <Minus className="h-4 w-4 text-slate-400" />;
  };

  return (
    <div className="rounded-lg border border-slate-700/60 mb-4" style={{ backgroundColor: '#0f172a' }}>
      {/* 헤더 */}
      <div className="px-3 py-2 border-b border-slate-700/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-blue-400" />
          <span className="text-sm font-medium text-white">통합 운영 현황</span>
          <span className="text-[10px] text-green-400 px-1.5 py-0.5 bg-green-500/10 rounded border border-green-500/30">
            실시간
          </span>
        </div>
        <div className="flex items-center gap-2">
          <StatusIcon status={stats.sensorStatus} />
          <span className={cn(
            'text-xs font-medium',
            stats.sensorStatus === 'good' ? 'text-green-400' :
            stats.sensorStatus === 'warning' ? 'text-yellow-400' :
            stats.sensorStatus === 'danger' ? 'text-red-400' : 'text-slate-400'
          )}>
            {stats.sensorStatus === 'good' ? '정상' :
             stats.sensorStatus === 'warning' ? '주의' :
             stats.sensorStatus === 'danger' ? '위험' : '대기'}
          </span>
        </div>
      </div>

      <div className="p-3 space-y-3">
        {/* 1. AI 운영 분석 + 운영 품질 (1:1 비율) */}
        <div className="grid grid-cols-2 gap-3">
          {/* AI 운영 분석 - 더 진한 네이비 배경 */}
          <div
            className="rounded-lg border border-blue-900/70 p-3"
            style={{
              backgroundColor: '#050810',
              boxShadow: '0 6px 20px rgba(0,0,0,0.6), 0 3px 6px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04), inset 0 -1px 0 rgba(0,0,0,0.4)'
            }}
          >
            <div className="flex items-center gap-2 mb-3">
              {/* AI 분석 배지 - 파란색 배경으로 강조 + 3D 입체감 */}
              <div
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-blue-600 border border-blue-400/60"
                style={{
                  boxShadow: '0 3px 8px rgba(37, 99, 235, 0.4), 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 0 rgba(0,0,0,0.2)'
                }}
              >
                <Sparkles className="h-3.5 w-3.5 text-white drop-shadow-sm" />
                <span className="text-xs font-extrabold text-white drop-shadow-sm">AI 분석</span>
              </div>
              {predictions && predictions.high_risk_count > 0 && (
                <span className="ml-auto text-[10px] px-2 py-1 rounded bg-red-500/20 text-red-400 font-medium border border-red-500/30">
                  고위험 {predictions.high_risk_count}
                </span>
              )}
            </div>

            {/* 분석 결과 - 배경 연하게, 글씨 진하게 */}
            <div className="space-y-2">
              {stats.aiAnalysis.slice(0, 3).map((analysis, idx) => (
                <div key={idx} className={cn(
                  'p-2.5 rounded-md border-l-2',
                  analysis.type === 'action' ? 'border-l-red-400' :
                  analysis.type === 'warning' ? 'border-l-amber-400' :
                  'border-l-emerald-400'
                )}
                style={{
                  backgroundColor: analysis.type === 'action' ? 'rgba(127, 29, 29, 0.4)' :
                    analysis.type === 'warning' ? 'rgba(120, 53, 15, 0.4)' : 'rgba(6, 78, 59, 0.4)',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.05)'
                }}>
                  <div className={cn(
                    'text-[13px] font-medium leading-snug',
                    analysis.type === 'action' ? 'text-red-300' :
                    analysis.type === 'warning' ? 'text-amber-300' : 'text-emerald-300'
                  )}>
                    {analysis.text}
                  </div>
                  {analysis.basis && (
                    <div className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
                      <span className="text-slate-500">근거:</span> {analysis.basis}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 운영 품질 - 세로 레이아웃 */}
          <div
            className="rounded-lg border border-slate-700/60 p-3"
            style={{
              backgroundColor: '#0f172a',
              boxShadow: '0 4px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)'
            }}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <Zap className="h-4 w-4 text-blue-400" />
              <span className="text-sm font-medium text-slate-200">운영 품질</span>
            </div>
            <p className="text-[10px] text-slate-500 mb-3 leading-relaxed">
              센서 정상 범위 유지율과 힘 부하의 종합 평가입니다.
            </p>

            {/* 종합 정상률 + 힘 피크 세로 배치 */}
            <div className="space-y-3">
              {/* 정상률 */}
              <div
                className="p-3 rounded-lg border border-slate-600/50"
                style={{
                  backgroundColor: '#1e293b',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)'
                }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="text-xs font-medium text-slate-300">종합 정상률</span>
                    <p className="text-[9px] text-slate-500">24시간 센서 정상 범위 비율</p>
                  </div>
                  <div className="text-right">
                    <span className={cn(
                      'text-xl font-bold',
                      stats.normalRate24h >= 90 ? 'text-green-400' :
                      stats.normalRate24h >= 70 ? 'text-yellow-400' : 'text-red-400'
                    )}>
                      {stats.normalRate24h}%
                    </span>
                    <p className={cn(
                      'text-[10px] font-medium',
                      stats.normalRate24h >= 90 ? 'text-green-500' :
                      stats.normalRate24h >= 70 ? 'text-yellow-500' : 'text-red-500'
                    )}>
                      {stats.normalRate24h >= 90 ? '양호' : stats.normalRate24h >= 70 ? '주의' : '위험'}
                    </p>
                  </div>
                </div>
                {/* 프로그레스 바 with 목표선 */}
                <div className="relative h-3 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      stats.normalRate24h >= 90 ? 'bg-green-500' :
                      stats.normalRate24h >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                    )}
                    style={{ width: `${Math.min(stats.normalRate24h, 100)}%` }}
                  />
                  {/* 목표선 90% */}
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-white/60"
                    style={{ left: '90%' }}
                    title="Target: 90%"
                  />
                </div>
                {/* 기준 범례 */}
                <div className="mt-2 flex items-center justify-between text-[9px]">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-red-500" />
                      <span className="text-slate-500">&lt;70%</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-yellow-500" />
                      <span className="text-slate-500">70-89%</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-green-500" />
                      <span className="text-slate-500">≥90%</span>
                    </span>
                  </div>
                  <span className="text-slate-400 font-medium">목표 90%↑</span>
                </div>
              </div>

              {/* 힘 피크 */}
              <div
                className="p-3 rounded-lg border border-slate-600/50"
                style={{
                  backgroundColor: '#1e293b',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)'
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <div>
                    <span className="text-xs font-medium text-slate-300">UR5e 힘 피크(P95)</span>
                    <p className="text-[9px] text-slate-500">상위 5% 최대 힘 크기</p>
                  </div>
                  <span className={cn(
                    'text-xl font-bold',
                    stats.ur5eForceMagP95 <= 80 ? 'text-green-400' :
                    stats.ur5eForceMagP95 <= 120 ? 'text-yellow-400' : 'text-red-400'
                  )}>
                    {stats.ur5eForceMagP95}N
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>현재값: {stats.ur5eForceMagLive ?? '-'}N</span>
                  <span className={stats.ur5eForceMagP95 <= 80 ? 'text-green-400' : 'text-amber-400'}>
                    목표값: ≤80N
                  </span>
                </div>
              </div>
            </div>

            {stats.riskScore > 30 && (
              <div className="mt-3 p-2 rounded bg-red-500/10 border border-red-500/30 flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
                <span className="text-[11px] text-red-400 font-medium">위험 점수: {stats.riskScore}%</span>
              </div>
            )}
          </div>
        </div>

        {/* 2. Axia80 센서 현황 (7일 평균 제거) */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Gauge className="h-4 w-4 text-cyan-400" />
            <span className="text-sm font-medium text-slate-300">Axia80 힘 센서</span>
          </div>
          <p className="text-[10px] text-slate-500 mb-2 leading-relaxed">
            6축 힘/토크 센서 실시간 측정값. Fz(수직), Fx(전후), Fy(좌우) 힘과 합력을 모니터링합니다.
          </p>
          <div className="grid grid-cols-4 gap-2">
            <ComparisonCard
              label="Fz (수직)"
              live={stats.fzLive}
              avg24h={stats.fzAvg24h}
              unit="N"
              highlight
            />
            <ComparisonCard
              label="Fx (전후)"
              live={stats.fxLive}
              avg24h={stats.fxAvg24h}
              unit="N"
            />
            <ComparisonCard
              label="Fy (좌우)"
              live={stats.fyLive}
              avg24h={stats.fyAvg24h}
              unit="N"
            />
            <ComparisonCard
              label="|F| 합력"
              live={stats.forceMagLive}
              avg24h={stats.forceMagAvg24h}
              unit="N"
            />
          </div>
        </div>

        {/* 3. UR5e 로봇 현황 */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <RotateCcw className="h-4 w-4 text-orange-400" />
            <span className="text-sm font-medium text-slate-300">UR5e 로봇 상태</span>
            {stats.tcpSpeedLive === 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400 ml-1">
                대기/정지
              </span>
            )}
          </div>
          <p className="text-[10px] text-slate-500 mb-2 leading-relaxed">
            협동로봇 운전 상태. TCP 속도(엔드이펙터 속도), 조인트 토크(부하), 전류(모터 소비전력)를 추적합니다.
          </p>
          <div className="grid grid-cols-3 gap-2">
            <ComparisonCard
              label="TCP 속도"
              live={stats.tcpSpeedLive}
              avg24h={stats.tcpSpeedAvg}
              unit="mm/s"
              showAvgLabel="버퍼 평균"
            />
            <ComparisonCard
              label="조인트 토크"
              live={stats.jointTorqueLive}
              avg24h={stats.jointTorqueAvg}
              unit="Nm"
              showAvgLabel="버퍼 평균"
            />
            <ComparisonCard
              label="조인트 전류"
              live={stats.jointCurrentLive}
              avg24h={stats.jointCurrentAvg}
              unit="A"
              showAvgLabel="버퍼 평균"
            />
          </div>
        </div>

        {/* 4. 예지보전 (AI 예측 요약) */}
        <div
          className="rounded-lg border border-slate-700/60 p-3"
          style={{
            backgroundColor: '#0f172a',
            boxShadow: '0 4px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)'
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Brain className="h-4.5 w-4.5 text-cyan-400" />
            <span className="text-base font-medium text-slate-200">예지보전</span>
            <span className="text-[8px] px-1 py-0.5 rounded bg-gradient-to-r from-purple-600 to-cyan-500 text-white font-bold flex items-center gap-0.5">
              <Sparkles className="h-2 w-2" />
              AI
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mb-2 leading-relaxed">
            UR5e + Axia80 실시간 상관분석 기반 위험 예측.
          </p>
          {latestIntegratedData ? (
            <div className="grid grid-cols-4 gap-2">
              {/* 부하율 */}
              <div
                className="p-2.5 rounded-lg border border-slate-600/50 text-center"
                style={{ backgroundColor: '#1e293b' }}
              >
                <div className="text-xs text-slate-400 mb-1">부하율</div>
                <div className={cn(
                  'text-xl font-bold',
                  latestIntegratedData.correlation.torque_force_ratio > 2.5 ? 'text-red-400' :
                  latestIntegratedData.correlation.torque_force_ratio > 2 ? 'text-yellow-400' : 'text-green-400'
                )}>
                  {latestIntegratedData.correlation.torque_force_ratio.toFixed(2)}
                </div>
              </div>
              {/* 접촉 위험 */}
              <div
                className="p-2.5 rounded-lg border border-slate-600/50 text-center"
                style={{ backgroundColor: '#1e293b' }}
              >
                <div className="text-xs text-slate-400 mb-1">접촉 위험</div>
                <div className={cn(
                  'text-xl font-bold',
                  latestIntegratedData.risk.contact_risk_score > 0.5 ? 'text-red-400' :
                  latestIntegratedData.risk.contact_risk_score > 0.3 ? 'text-yellow-400' : 'text-green-400'
                )}>
                  {(latestIntegratedData.risk.contact_risk_score * 100).toFixed(0)}%
                </div>
              </div>
              {/* 충돌 위험 */}
              <div
                className="p-2.5 rounded-lg border border-slate-600/50 text-center"
                style={{ backgroundColor: '#1e293b' }}
              >
                <div className="text-xs text-slate-400 mb-1">충돌 위험</div>
                <div className={cn(
                  'text-xl font-bold',
                  latestIntegratedData.risk.collision_risk_score > 0.5 ? 'text-red-400' :
                  latestIntegratedData.risk.collision_risk_score > 0.3 ? 'text-yellow-400' : 'text-green-400'
                )}>
                  {(latestIntegratedData.risk.collision_risk_score * 100).toFixed(0)}%
                </div>
              </div>
              {/* 상태 */}
              <div
                className={cn(
                  'p-2.5 rounded-lg border text-center',
                  latestIntegratedData.correlation.anomaly_detected ||
                  latestIntegratedData.risk.contact_risk_score > 0.5 ||
                  latestIntegratedData.risk.collision_risk_score > 0.5 ||
                  latestIntegratedData.axia80.force_spike
                    ? 'border-red-500/50 bg-red-500/20'
                    : latestIntegratedData.correlation.torque_force_ratio > 2 ||
                      latestIntegratedData.risk.contact_risk_score > 0.3 ||
                      latestIntegratedData.risk.collision_risk_score > 0.3
                    ? 'border-yellow-500/50 bg-yellow-500/20'
                    : 'border-green-500/50 bg-green-500/20'
                )}
              >
                <div className="text-xs text-slate-400 mb-1">상태</div>
                <div className={cn(
                  'text-base font-bold',
                  latestIntegratedData.correlation.anomaly_detected ||
                  latestIntegratedData.risk.contact_risk_score > 0.5 ||
                  latestIntegratedData.risk.collision_risk_score > 0.5 ||
                  latestIntegratedData.axia80.force_spike
                    ? 'text-red-400'
                    : latestIntegratedData.correlation.torque_force_ratio > 2 ||
                      latestIntegratedData.risk.contact_risk_score > 0.3 ||
                      latestIntegratedData.risk.collision_risk_score > 0.3
                    ? 'text-yellow-400'
                    : 'text-green-400'
                )}>
                  {latestIntegratedData.correlation.anomaly_detected ||
                   latestIntegratedData.risk.contact_risk_score > 0.5 ||
                   latestIntegratedData.risk.collision_risk_score > 0.5 ||
                   latestIntegratedData.axia80.force_spike
                    ? '위험'
                    : latestIntegratedData.correlation.torque_force_ratio > 2 ||
                      latestIntegratedData.risk.contact_risk_score > 0.3 ||
                      latestIntegratedData.risk.collision_risk_score > 0.3
                    ? '경고'
                    : '정상'}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-2 text-slate-500 text-sm">
              데이터 대기 중...
            </div>
          )}
        </div>

        {/* 5. 이벤트 현황 + 조치 필요 (통합 카드) - AI 분석과 동일한 테두리 및 배경 */}
        <div
          className={cn(
            'rounded-lg border p-3',
            stats.unresolvedCount > 0
              ? 'border-amber-500/50'
              : 'border-blue-900/70'
          )}
          style={{
            backgroundColor: '#050810',
            boxShadow: '0 6px 20px rgba(0,0,0,0.6), 0 3px 6px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04), inset 0 -1px 0 rgba(0,0,0,0.4)'
          }}
        >
          {/* 헤더: 이벤트 현황 + 조치 필요 배지 */}
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <AlertTriangle className={cn(
                'h-4.5 w-4.5',
                stats.unresolvedCount > 0 ? 'text-amber-400' : 'text-slate-400'
              )} />
              <span className="text-base font-medium text-slate-200">이벤트 현황</span>
              <span className="text-xs text-slate-500">
                총 {stats.totalEvents}건
              </span>
            </div>
            <div className="flex items-center gap-2">
              {stats.unresolvedCount > 0 ? (
                <span className="flex items-center gap-1.5 text-[11px] px-2 py-1 rounded bg-red-500/20 text-red-400 font-medium border border-red-500/30">
                  <Wrench className="h-3 w-3" />
                  조치 필요 {stats.unresolvedCount}건
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-[11px] px-2 py-1 rounded bg-green-500/20 text-green-400 font-medium border border-green-500/30">
                  <CheckCircle className="h-3 w-3" />
                  전체 해결
                </span>
              )}
            </div>
          </div>
          <p className="text-[10px] text-slate-500 mb-3 leading-relaxed">
            센서에서 감지한 이상 패턴 기록. 충돌(물체 접촉), 과부하(힘 한계 초과), 드리프트(센서 편차)로 분류합니다.
          </p>

          {/* 이벤트 카운터 */}
          <div className="grid grid-cols-3 gap-2 mb-3">
            <EventCounter label="충돌" count={stats.collisionTotal} color="red" />
            <EventCounter label="과부하" count={stats.overloadTotal} color="orange" />
            <EventCounter label="드리프트" count={stats.driftTotal} color="yellow" />
          </div>

          {/* 이벤트 상세 리스트 (유형별) */}
          {stats.totalEvents > 0 && (
            <div className="border-t border-slate-700/30 pt-3 space-y-2">
              {/* 충돌 이벤트 */}
              {stats.collisionEvents.length > 0 && (
                <div
                  className="p-2 rounded bg-red-500/15 border border-red-500/30"
                  style={{
                    boxShadow: '0 2px 4px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.03)'
                  }}
                >
                  <div className="text-[11px] text-red-400 font-medium mb-1.5 flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-red-400" />
                    충돌 이벤트 ({stats.collisionEvents.length}건)
                  </div>
                  <div className="space-y-1 max-h-[50px] overflow-y-auto">
                    {stats.collisionEvents.slice(0, 2).map((ev, idx) => (
                      <div key={idx} className="text-[11px] pl-3 flex items-center gap-1.5">
                        <span className="text-slate-300">
                          {ev.message || ev.errorCode || '충돌 감지됨'}
                        </span>
                        {resolvedEventIds.has(ev.id) && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 font-medium">
                            해결됨
                          </span>
                        )}
                      </div>
                    ))}
                    {stats.collisionEvents.length > 2 && (
                      <div className="text-[10px] text-slate-500 pl-3">
                        +{stats.collisionEvents.length - 2}건 더보기
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 과부하 이벤트 */}
              {stats.overloadEvents.length > 0 && (
                <div
                  className="p-2 rounded bg-orange-500/15 border border-orange-500/30"
                  style={{
                    boxShadow: '0 2px 4px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.03)'
                  }}
                >
                  <div className="text-[11px] text-orange-400 font-medium mb-1.5 flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-orange-400" />
                    과부하 이벤트 ({stats.overloadEvents.length}건)
                  </div>
                  <div className="space-y-1 max-h-[50px] overflow-y-auto">
                    {stats.overloadEvents.slice(0, 2).map((ev, idx) => (
                      <div key={idx} className="text-[11px] pl-3 flex items-center gap-1.5">
                        <span className="text-slate-300">
                          {ev.message || ev.errorCode || '과부하 감지됨'}
                        </span>
                        {resolvedEventIds.has(ev.id) && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 font-medium">
                            해결됨
                          </span>
                        )}
                      </div>
                    ))}
                    {stats.overloadEvents.length > 2 && (
                      <div className="text-[10px] text-slate-500 pl-3">
                        +{stats.overloadEvents.length - 2}건 더보기
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 드리프트 이벤트 */}
              {stats.driftEvents.length > 0 && (
                <div
                  className="p-2 rounded bg-yellow-500/15 border border-yellow-500/30"
                  style={{
                    boxShadow: '0 2px 4px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.03)'
                  }}
                >
                  <div className="text-[11px] text-yellow-400 font-medium mb-1.5 flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-yellow-400" />
                    드리프트 이벤트 ({stats.driftEvents.length}건)
                  </div>
                  <div className="space-y-1 max-h-[50px] overflow-y-auto">
                    {stats.driftEvents.slice(0, 2).map((ev, idx) => (
                      <div key={idx} className="text-[11px] pl-3 flex items-center gap-1.5">
                        <span className="text-slate-300">
                          {ev.message || ev.errorCode || '드리프트 감지됨'}
                        </span>
                        {resolvedEventIds.has(ev.id) && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 font-medium">
                            해결됨
                          </span>
                        )}
                      </div>
                    ))}
                    {stats.driftEvents.length > 2 && (
                      <div className="text-[10px] text-slate-500 pl-3">
                        +{stats.driftEvents.length - 2}건 더보기
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 조치 필요 항목 */}
          {stats.actions.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-700/30">
              <div className="text-[11px] text-amber-400 font-medium mb-2 flex items-center gap-1.5">
                <Wrench className="h-3.5 w-3.5" />
                권장 조치
              </div>
              <div className="space-y-1.5">
                {stats.actions.map((action, idx) => (
                  <div key={idx} className="flex items-center gap-2 pl-1">
                    <ArrowRight className={cn(
                      'h-3 w-3 shrink-0',
                      action.type === 'danger' ? 'text-red-400' : 'text-amber-400'
                    )} />
                    <span className={cn(
                      'text-[11px]',
                      action.type === 'danger' ? 'text-red-300' : 'text-amber-300'
                    )}>
                      {action.text}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 해결된 경우 */}
          {stats.totalEvents > 0 && stats.unresolvedCount === 0 && (
            <div className="mt-3 pt-3 border-t border-slate-700/30 flex items-center justify-center gap-2 py-2">
              <CheckCircle className="h-4 w-4 text-green-400" />
              <span className="text-[12px] text-green-400 font-medium">
                전체 {stats.resolvedCount}건 이벤트 해결됨
              </span>
            </div>
          )}
        </div>

        {/* 5. 데이터 정보 */}
        <div className="text-[10px] text-slate-500 flex items-center justify-between">
          <span>SSE Buffer: {stats.sseBufferSize} | Integrated Stream: {stats.integratedBufferSize}</span>
          <span>24h Samples: {stats.sampleCount24h}</span>
        </div>
      </div>
    </div>
  );
}

// === 비교 카드 (7일 평균 제거) ===
function ComparisonCard({
  label,
  live,
  avg24h,
  unit,
  highlight = false,
  showAvgLabel,
}: {
  label: string;
  live: number | null;
  avg24h: number;
  unit: string;
  highlight?: boolean;
  showAvgLabel?: string;
}) {
  return (
    <div
      className={cn(
        'rounded-lg border p-2',
        highlight
          ? 'border-blue-500/60'
          : 'border-slate-600/50'
      )}
      style={{
        backgroundColor: highlight ? '#172554' : '#1e293b',
        boxShadow: '0 2px 6px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)'
      }}
    >
      <div className={cn(
        'text-[11px] font-medium mb-1.5',
        highlight ? 'text-blue-300' : 'text-slate-300'
      )}>
        {label}
      </div>

      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-emerald-400">● 현재값</span>
          <span className="text-sm font-bold tabular-nums text-white">
            {live != null ? live : '-'}
            <span className="text-[10px] font-normal text-slate-500 ml-0.5">{unit}</span>
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-[10px] text-blue-400">● {showAvgLabel || '24시간 평균'}</span>
          <span className="text-sm font-bold text-slate-300 tabular-nums">
            {avg24h}
            <span className="text-[10px] font-normal text-slate-500 ml-0.5">{unit}</span>
          </span>
        </div>
      </div>
    </div>
  );
}

// === 이벤트 카운터 ===
function EventCounter({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: 'red' | 'orange' | 'yellow';
}) {
  // 색상 카드들은 투명도 유지 (이벤트 현황 특성)
  const colorClass = {
    red: count > 0 ? 'text-red-400 bg-red-500/25 border-red-500/40' : 'text-slate-500 border-slate-600/50',
    orange: count > 0 ? 'text-orange-400 bg-orange-500/25 border-orange-500/40' : 'text-slate-500 border-slate-600/50',
    yellow: count > 0 ? 'text-yellow-400 bg-yellow-500/25 border-yellow-500/40' : 'text-slate-500 border-slate-600/50',
  }[color];

  return (
    <div
      className={cn('rounded p-1.5 text-center border', colorClass)}
      style={{
        backgroundColor: count > 0 ? undefined : '#1e293b',
        boxShadow: '0 2px 4px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.04)'
      }}
    >
      <div className="text-base font-bold">{count}</div>
      <div className="text-[9px]">{label}</div>
    </div>
  );
}
