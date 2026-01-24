'use client';

import { useMemo } from 'react';
import {
  AlertTriangle,
  Activity,
  Cpu,
  Shield,
  TrendingUp,
  Zap,
  Clock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import type {
  IntegratedStreamData,
  RiskLevel,
  SafetyMode,
  ScenarioType,
} from '@/types/api';
import type { LiveDetectedEvent } from '@/stores/alertStore';

interface CorrelationTableProps {
  data: IntegratedStreamData[];
  latestData: IntegratedStreamData | null;
  isConnected: boolean;
  maxHeight?: string;
  detectedEvents?: LiveDetectedEvent[];
}

// 위험도 색상 설정
const riskLevelConfig: Record<RiskLevel, { color: string; bgColor: string; borderColor: string }> = {
  critical: {
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500/50',
  },
  high: {
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/20',
    borderColor: 'border-orange-500/50',
  },
  medium: {
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500/50',
  },
  low: {
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/50',
  },
};

// 시나리오 라벨
const scenarioLabels: Record<ScenarioType, { label: string; color: string }> = {
  normal: { label: '정상', color: 'text-green-400' },
  collision: { label: '충돌', color: 'text-red-400' },
  overload: { label: '과부하', color: 'text-orange-400' },
  wear: { label: '마모', color: 'text-yellow-400' },
  risk_approach: { label: '위험접근', color: 'text-purple-400' },
};

// 안전 모드 라벨
const safetyModeLabels: Record<SafetyMode, { label: string; color: string }> = {
  normal: { label: '정상', color: 'text-green-400' },
  reduced: { label: '감속', color: 'text-yellow-400' },
  protective_stop: { label: '보호정지', color: 'text-red-400' },
};

// 권장 조치 라벨
const actionLabels: Record<string, string> = {
  maintain: '현상 유지',
  caution: '주의 관찰',
  slow_down: '감속 필요',
  emergency_stop: '긴급 정지',
  inspect_joints: '조인트 점검',
};

export function CorrelationTable({
  data,
  latestData,
  isConnected,
  maxHeight = '300px',
  detectedEvents = [],
}: CorrelationTableProps) {
  // 최근 이벤트 (최대 20개, 화면에는 5개씩 표시 후 스크롤)
  const recentEvents = useMemo(() => {
    return detectedEvents
      .filter((e) => e.riskLevel !== 'low')
      .slice(0, 20);
  }, [detectedEvents]);

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return '-';
    }
  };
  // 통계 계산
  const stats = useMemo(() => {
    if (data.length < 5) return null;

    const recentData = data.slice(-30);
    const forces = recentData.map((d) => d.axia80.force_magnitude);
    const speeds = recentData.map((d) => d.ur5e.tcp_speed);
    const risks = recentData.map((d) => d.risk.contact_risk_score);

    return {
      avgForce: (forces.reduce((a, b) => a + b, 0) / forces.length).toFixed(1),
      maxForce: Math.max(...forces).toFixed(1),
      avgSpeed: (speeds.reduce((a, b) => a + b, 0) / speeds.length).toFixed(3),
      avgRisk: (risks.reduce((a, b) => a + b, 0) / risks.length).toFixed(2),
    };
  }, [data]);

  if (!latestData) {
    return (
      <div
        className="rounded-lg border border-slate-700/50 bg-gradient-to-br from-slate-800/50 via-slate-800/30 to-slate-900/50 backdrop-blur-sm mt-4"
        style={{ boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)' }}
      >
        <div className="px-3 py-2 border-b border-slate-700/50">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-purple-400" />
            <h3 className="text-sm font-medium text-white">실시간 예지보전</h3>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-medium flex items-center gap-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              AI 예측
            </span>
          </div>
        </div>
        <div className="p-6 text-center text-slate-500">
          <Activity className="h-8 w-8 mx-auto mb-2 opacity-50 animate-pulse" />
          <p className="text-sm">데이터 수신 대기 중...</p>
        </div>
      </div>
    );
  }

  const { scenario, axia80, ur5e, correlation, risk } = latestData;
  const scenarioConfig = scenarioLabels[scenario.current] || scenarioLabels.normal;
  const safetyConfig = safetyModeLabels[ur5e.safety_mode] || safetyModeLabels.normal;
  const riskConfig = riskLevelConfig[risk.risk_level] || riskLevelConfig.low;

  return (
    <div
      className="rounded-lg border border-slate-700/50 bg-gradient-to-br from-slate-800/50 via-slate-800/30 to-slate-900/50 backdrop-blur-sm mt-4"
      style={{ boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.03)' }}
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-slate-700/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-purple-400" />
            <h3 className="text-sm font-medium text-white">실시간 예지보전</h3>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-medium flex items-center gap-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              AI 예측
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'text-[10px] px-1.5 py-0.5 rounded font-medium',
                scenarioConfig.color,
                'bg-slate-700/50'
              )}
            >
              시나리오: {scenarioConfig.label}
            </span>
            <span
              className={cn(
                'inline-block w-2 h-2 rounded-full',
                isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
              )}
            />
          </div>
        </div>
      </div>

      <div className="p-3">
        {/* 상단 데이터 카드 */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          {/* UR5e 카드 */}
          <div className="rounded-lg p-2 bg-slate-700/30 border border-slate-600/30">
            <div className="flex items-center gap-1.5 mb-2">
              <Cpu className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-xs font-medium text-emerald-400">UR5e 로봇</span>
            </div>
            <div className="space-y-1 text-[10px]">
              <div className="flex justify-between">
                <span className="text-slate-400">TCP 속도</span>
                <span className="text-slate-200 font-mono">{ur5e.tcp_speed.toFixed(3)} m/s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">토크 합</span>
                <span className="text-slate-200 font-mono">{ur5e.joint_torque_sum.toFixed(1)} Nm</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">평균 전류</span>
                <span className="text-slate-200 font-mono">{ur5e.joint_current_avg.toFixed(2)} A</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">안전 모드</span>
                <span className={cn('font-medium', safetyConfig.color)}>{safetyConfig.label}</span>
              </div>
            </div>
          </div>

          {/* Axia80 카드 */}
          <div className="rounded-lg p-2 bg-slate-700/30 border border-slate-600/30">
            <div className="flex items-center gap-1.5 mb-2">
              <Activity className="h-3.5 w-3.5 text-cyan-400" />
              <span className="text-xs font-medium text-cyan-400">Axia80 센서</span>
            </div>
            <div className="space-y-1 text-[10px]">
              <div className="flex justify-between">
                <span className="text-slate-400">힘 크기</span>
                <span className={cn(
                  'font-mono font-medium',
                  axia80.force_spike ? 'text-red-400' : 'text-slate-200'
                )}>
                  {axia80.force_magnitude.toFixed(1)} N
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Fz</span>
                <span className="text-slate-200 font-mono">{axia80.Fz.toFixed(1)} N</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">변화율</span>
                <span className={cn(
                  'font-mono',
                  Math.abs(axia80.force_rate) > 10 ? 'text-yellow-400' : 'text-slate-200'
                )}>
                  {axia80.force_rate.toFixed(1)} N/t
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">스파이크</span>
                <span className={axia80.force_spike ? 'text-red-400 font-medium' : 'text-slate-500'}>
                  {axia80.force_spike ? 'YES' : 'no'}
                </span>
              </div>
            </div>
          </div>

          {/* 위험도 카드 - AI 예측 */}
          <div className={cn(
            'rounded-lg p-2 border relative',
            riskConfig.bgColor,
            riskConfig.borderColor
          )}>
            {/* AI 예측 배지 */}
            <div className="absolute -top-1.5 right-2 px-1.5 py-0.5 rounded bg-gradient-to-r from-cyan-500/80 to-purple-500/80 text-[8px] font-bold text-white shadow-lg">
              AI
            </div>
            <div className="flex items-center gap-1.5 mb-2">
              <Shield className="h-3.5 w-3.5" />
              <span className={cn('text-xs font-medium', riskConfig.color)}>위험도 예측</span>
            </div>
            <div className="space-y-1 text-[10px]">
              <div className="flex justify-between">
                <span className="text-slate-400">접촉 위험</span>
                <span className={cn('font-mono font-medium', riskConfig.color)}>
                  {(risk.contact_risk_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">충돌 위험</span>
                <span className={cn('font-mono font-medium', riskConfig.color)}>
                  {(risk.collision_risk_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">수준</span>
                <span className={cn('font-semibold uppercase', riskConfig.color)}>
                  {risk.risk_level}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">권장</span>
                <span className="text-slate-200 text-[9px]">
                  {actionLabels[risk.recommended_action] || risk.recommended_action}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* 상관관계 메트릭 */}
        <div className="rounded-lg p-2 bg-slate-700/20 border border-slate-600/30 mb-3">
          <div className="flex items-center gap-1.5 mb-2">
            <TrendingUp className="h-3.5 w-3.5 text-blue-400" />
            <span className="text-xs font-medium text-blue-400">상관분석 메트릭</span>
            {correlation.anomaly_detected && (
              <span className="ml-auto flex items-center gap-1 text-[10px] text-red-400">
                <AlertTriangle className="h-3 w-3" />
                이상 감지
              </span>
            )}
          </div>
          <div className="grid grid-cols-3 gap-4 text-[10px]">
            <div>
              <div className="text-slate-400 mb-0.5">토크/힘 비율</div>
              <div className={cn(
                'font-mono text-lg font-bold',
                correlation.torque_force_ratio > 2 ? 'text-yellow-400' : 'text-slate-200'
              )}>
                {correlation.torque_force_ratio.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-slate-400 mb-0.5">속도-힘 상관</div>
              <div className="font-mono text-lg font-bold text-slate-200">
                {correlation.speed_force_correlation.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-slate-400 mb-0.5">시나리오 진행</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-slate-600 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500 rounded-full transition-all"
                    style={{
                      width: `${(scenario.elapsed_sec / (scenario.elapsed_sec + scenario.remaining_sec)) * 100}%`
                    }}
                  />
                </div>
                <span className="text-slate-300 font-mono">
                  {scenario.remaining_sec.toFixed(0)}s
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* 최근 히스토리 테이블 */}
        {stats && (
          <div className="text-[10px] text-slate-500 flex justify-between px-1 mb-3">
            <span>최근 30개 평균 - 힘: {stats.avgForce}N, 속도: {stats.avgSpeed}m/s, 위험: {(parseFloat(stats.avgRisk) * 100).toFixed(0)}%</span>
            <span>최대 힘: {stats.maxForce}N</span>
          </div>
        )}

        {/* 위험 감지 이벤트 기록 */}
        {recentEvents.length > 0 && (
          <div className="border-t border-slate-700/50 pt-3">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
              <span className="text-xs font-medium text-red-400">위험 감지 기록</span>
              <span className="text-[10px] text-slate-500">
                {recentEvents.length}건{recentEvents.length > 5 && ' (스크롤)'}
              </span>
            </div>
            <ScrollArea className="max-h-[145px]">
              <div className="space-y-1">
                {recentEvents.map((event) => {
                  const eventRiskConfig = riskLevelConfig[event.riskLevel] || riskLevelConfig.low;
                  const eventScenarioConfig = scenarioLabels[event.scenario] || scenarioLabels.normal;
                  return (
                    <div
                      key={event.id}
                      className={cn(
                        'flex items-center gap-3 px-2 py-1.5 rounded text-[10px] border',
                        event.resolved
                          ? 'bg-slate-800/30 border-slate-700/30 opacity-60'
                          : cn(eventRiskConfig.bgColor, eventRiskConfig.borderColor)
                      )}
                    >
                      {/* 시간 */}
                      <div className="flex items-center gap-1 text-slate-400 min-w-[60px]">
                        <Clock className="h-3 w-3" />
                        {formatTime(event.timestamp)}
                      </div>

                      {/* 시나리오 */}
                      <span className={cn('font-medium min-w-[50px]', eventScenarioConfig.color)}>
                        {eventScenarioConfig.label}
                      </span>

                      {/* 위험도 */}
                      <span className={cn(
                        'px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase',
                        eventRiskConfig.bgColor,
                        eventRiskConfig.color
                      )}>
                        {event.riskLevel}
                      </span>

                      {/* 최대 힘 */}
                      <div className="flex items-center gap-1">
                        <span className="text-slate-500">힘:</span>
                        <span className="font-mono text-slate-300">{event.maxForce.toFixed(1)}N</span>
                      </div>

                      {/* 위험도 */}
                      <div className="flex items-center gap-1">
                        <span className="text-slate-500">위험:</span>
                        <span className={cn('font-mono', eventRiskConfig.color)}>
                          {(event.maxRiskScore * 100).toFixed(0)}%
                        </span>
                      </div>

                      {/* 지속시간 */}
                      <div className="flex items-center gap-1">
                        <span className="text-slate-500">지속:</span>
                        <span className="font-mono text-slate-300">{event.duration.toFixed(1)}s</span>
                      </div>

                      {/* 보호정지 */}
                      {event.details.protectiveStop && (
                        <span className="flex items-center gap-1 text-red-400">
                          <Shield className="h-3 w-3" />
                          보호정지
                        </span>
                      )}

                      {/* 해제 상태 */}
                      {event.resolved && (
                        <span className="ml-auto text-green-400">✓ 해제</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </div>
        )}
      </div>
    </div>
  );
}
