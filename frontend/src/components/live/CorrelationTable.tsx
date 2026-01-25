'use client';

import {
  AlertTriangle,
  Activity,
  Cpu,
  TrendingUp,
  Zap,
  Brain,
  Eye,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type {
  IntegratedStreamData,
  RiskLevel,
  SafetyMode,
} from '@/types/api';

interface CorrelationTableProps {
  latestData: IntegratedStreamData | null;
  isConnected: boolean;
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

// 안전 모드 라벨
const safetyModeLabels: Record<SafetyMode, { label: string; color: string }> = {
  normal: { label: '정상', color: 'text-green-400' },
  reduced: { label: '감속', color: 'text-yellow-400' },
  protective_stop: { label: '보호정지', color: 'text-red-400' },
};

export function CorrelationTable({
  latestData,
  isConnected,
}: CorrelationTableProps) {
  if (!latestData) {
    return (
      <div
        className="rounded-lg border border-slate-700/50 bg-gradient-to-br from-slate-800/50 via-slate-800/30 to-slate-900/50 backdrop-blur-sm mt-4"
        style={{ boxShadow: '0 4px 16px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.08), inset 0 -1px 0 rgba(0,0,0,0.2)' }}
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

  const { axia80, ur5e, correlation, risk } = latestData;
  const safetyConfig = safetyModeLabels[ur5e.safety_mode] || safetyModeLabels.normal;
  const riskConfig = riskLevelConfig[risk.risk_level] || riskLevelConfig.low;

  return (
    <div
      className="rounded-lg border border-slate-700/50 bg-gradient-to-br from-slate-800/50 via-slate-800/30 to-slate-900/50 backdrop-blur-sm mt-4"
      style={{ boxShadow: '0 4px 16px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.08), inset 0 -1px 0 rgba(0,0,0,0.2)' }}
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
                'inline-block w-2 h-2 rounded-full',
                isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
              )}
            />
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          UR5e 로봇과 Axia80 센서 데이터를 실시간 분석하여 <span className="text-cyan-400">고장/사고 발생 전</span> 위험을 예측합니다.
        </p>
      </div>

      <div className="p-3">
        {/* 좌/우 2단 레이아웃 */}
        <div className="grid grid-cols-2 gap-3">
          {/* 좌측: 실시간 모니터링 (현재 감지) */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <Eye className="h-4 w-4 text-emerald-400" />
              <span className="text-sm font-bold text-emerald-400">실시간 모니터링</span>
              <span className="text-[10px] text-slate-500">현재 상태 감지</span>
            </div>

            {/* UR5e 카드 */}
            <div className="rounded-lg p-3 border border-slate-600/40" style={{ backgroundColor: '#1e293b' }}>
              <div className="flex items-center gap-2 mb-2">
                <Cpu className="h-4 w-4 text-emerald-400" />
                <span className="text-sm font-medium text-emerald-400">UR5e 로봇</span>
                <span className="ml-auto text-[10px] text-slate-500">협동로봇 동작</span>
              </div>
              <div className="space-y-2 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-400">TCP 속도</span>
                  <span className="text-slate-200 font-mono font-medium">{ur5e.tcp_speed.toFixed(3)} m/s</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">토크 합</span>
                  <span className={cn('font-mono font-medium', ur5e.joint_torque_sum > 80 ? 'text-yellow-400' : 'text-slate-200')}>{ur5e.joint_torque_sum.toFixed(1)} Nm</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">평균 전류</span>
                  <span className="text-slate-200 font-mono font-medium">{ur5e.joint_current_avg.toFixed(2)} A</span>
                </div>
                <div className="flex justify-between pt-2 border-t border-slate-700/40">
                  <span className="text-slate-400">안전 모드</span>
                  <span className={cn('font-bold', safetyConfig.color)}>{safetyConfig.label}</span>
                </div>
              </div>
            </div>

            {/* Axia80 카드 */}
            <div className="rounded-lg p-3 border border-slate-600/40" style={{ backgroundColor: '#1e293b' }}>
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-4 w-4 text-cyan-400" />
                <span className="text-sm font-medium text-cyan-400">Axia80 센서</span>
                <span className="ml-auto text-[10px] text-slate-500">6축 힘/토크</span>
              </div>
              <div className="space-y-2 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-400">총 힘</span>
                  <span className={cn('font-mono font-bold', axia80.force_spike ? 'text-red-400' : axia80.force_magnitude > 80 ? 'text-yellow-400' : 'text-slate-200')}>
                    {axia80.force_magnitude.toFixed(1)} N
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Fz 수직력</span>
                  <span className="text-slate-200 font-mono font-medium">{axia80.Fz.toFixed(1)} N</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">변화속도</span>
                  <span className={cn('font-mono font-medium', Math.abs(axia80.force_rate) > 10 ? 'text-yellow-400' : 'text-slate-200')}>
                    {axia80.force_rate.toFixed(1)} N/s
                  </span>
                </div>
                <div className="flex justify-between pt-2 border-t border-slate-700/40">
                  <span className="text-slate-400">급격한 변화</span>
                  <span className={axia80.force_spike ? 'text-red-400 font-bold' : 'text-green-400 font-medium'}>
                    {axia80.force_spike ? '⚠️ 감지됨!' : '정상'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* 우측: AI 종합 위험 분석 */}
          <div className="flex flex-col space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="h-4 w-4 text-cyan-400" />
              <span className="text-sm font-bold text-cyan-400">AI 종합 위험 분석</span>
              {correlation.anomaly_detected && (
                <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse">
                  <AlertTriangle className="h-3 w-3" />
                  이상 감지!
                </span>
              )}
            </div>

            {/* AI 분석 카드 - 좌측 센서 카드들과 높이 맞춤 */}
            <div
              className={cn('flex-1 rounded-lg p-3 border', riskConfig.borderColor)}
              style={{
                backgroundColor: '#1e293b',
                boxShadow: '0 2px 8px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.05)'
              }}
            >
              <p className="text-xs text-slate-500 mb-2.5">로봇+센서 데이터를 <span className="text-cyan-400">AI가 분석</span>하여 위험을 예측</p>

              <div className="space-y-2 text-[11px]">
                {/* 로봇 부하율 - 글씨 진하게, 크게 */}
                <div className="p-2 rounded bg-purple-900/35 border border-purple-500/30">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <TrendingUp className="h-4 w-4 text-purple-400" />
                      <span className="text-purple-200 font-bold text-xs">로봇 부하율</span>
                    </div>
                    <span className={cn('font-mono font-bold text-lg', correlation.torque_force_ratio > 2 ? 'text-yellow-400' : 'text-green-400')}>
                      {correlation.torque_force_ratio.toFixed(2)}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500">토크÷힘 비율 | 높으면 마모/과부하 징후</p>
                  <div className="mt-1.5 h-1.5 bg-slate-600 rounded-full overflow-hidden">
                    <div className={cn('h-full rounded-full', correlation.torque_force_ratio > 2 ? 'bg-yellow-500' : 'bg-green-500')} style={{ width: `${Math.min(correlation.torque_force_ratio / 3 * 100, 100)}%` }} />
                  </div>
                </div>

                {/* 접촉 위험 */}
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-300 font-medium">접촉 위험</span>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-slate-600 rounded-full overflow-hidden">
                        <div className={cn('h-full rounded-full transition-all', risk.contact_risk_score > 0.5 ? 'bg-red-500' : risk.contact_risk_score > 0.3 ? 'bg-yellow-500' : 'bg-green-500')} style={{ width: `${risk.contact_risk_score * 100}%` }} />
                      </div>
                      <span className={cn('font-mono font-bold w-10 text-right', risk.contact_risk_score > 0.5 ? 'text-red-400' : risk.contact_risk_score > 0.3 ? 'text-yellow-400' : 'text-green-400')}>
                        {(risk.contact_risk_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-500 mt-0.5">작업자와 로봇 간 예상 접촉 확률</p>
                </div>

                {/* 충돌 위험 */}
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-300 font-medium">충돌 위험</span>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-slate-600 rounded-full overflow-hidden">
                        <div className={cn('h-full rounded-full transition-all', risk.collision_risk_score > 0.5 ? 'bg-red-500' : risk.collision_risk_score > 0.3 ? 'bg-yellow-500' : 'bg-green-500')} style={{ width: `${risk.collision_risk_score * 100}%` }} />
                      </div>
                      <span className={cn('font-mono font-bold w-10 text-right', risk.collision_risk_score > 0.5 ? 'text-red-400' : risk.collision_risk_score > 0.3 ? 'text-yellow-400' : 'text-green-400')}>
                        {(risk.collision_risk_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-500 mt-0.5">장애물/공작물과의 충돌 예상 확률</p>
                </div>
              </div>

              {/* AI 예측 알림 - 카드 내부 섹션 */}
              <div
                className="mt-3 rounded-lg border border-slate-600/50 p-2.5 relative"
                style={{
                  backgroundColor: '#0f172a',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.05)'
                }}
              >
                {/* AI 배지 - 우측 상단 */}
                <div className="absolute -top-2 -right-2 px-2 py-1 rounded-md bg-gradient-to-r from-purple-600 to-cyan-500 text-[10px] font-bold text-white shadow-lg flex items-center gap-1">
                  <Sparkles className="h-3 w-3" />
                  AI
                </div>

                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                  <span className="text-xs font-bold text-cyan-300">AI 예측 알림</span>
                </div>

                <div className="space-y-1.5">
                  {/* 부하율 기반 예측 */}
                  {correlation.torque_force_ratio > 2 ? (
                    <div className="p-2 rounded bg-yellow-500/10 border border-yellow-500/20">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-yellow-400 shrink-0" />
                        <span className="text-[11px] text-yellow-300 font-bold">과부하/마모 위험 증가</span>
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1 ml-5">
                        토크 {ur5e.joint_torque_sum.toFixed(1)}Nm ÷ 힘 {axia80.force_magnitude.toFixed(1)}N = <span className="text-yellow-400 font-bold">{correlation.torque_force_ratio.toFixed(2)}</span>
                      </p>
                    </div>
                  ) : (
                    <div className="p-2 rounded bg-green-500/10 border border-green-500/20">
                      <div className="flex items-center gap-2">
                        <Activity className="h-3.5 w-3.5 text-green-400 shrink-0" />
                        <span className="text-[11px] text-green-300">부하율 정상 범위 유지 중</span>
                      </div>
                    </div>
                  )}

                  {/* 접촉/충돌 위험 기반 예측 */}
                  {risk.contact_risk_score > 0.5 || risk.collision_risk_score > 0.5 ? (
                    <div className="p-2 rounded bg-red-500/10 border border-red-500/20">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-red-400 shrink-0" />
                        <span className="text-[11px] text-red-300 font-bold">
                          {risk.contact_risk_score > 0.5 && risk.collision_risk_score > 0.5
                            ? '접촉 + 충돌 위험 높음'
                            : risk.contact_risk_score > 0.5
                            ? '작업자 접촉 위험'
                            : '장애물 충돌 위험'}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1 ml-5">
                        속도 {ur5e.tcp_speed.toFixed(3)}m/s + 힘 {axia80.force_magnitude.toFixed(1)}N
                      </p>
                    </div>
                  ) : risk.contact_risk_score > 0.3 || risk.collision_risk_score > 0.3 ? (
                    <div className="p-2 rounded bg-yellow-500/10 border border-yellow-500/20">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-yellow-400 shrink-0" />
                        <span className="text-[11px] text-yellow-300">위험도 상승 추세 감지</span>
                      </div>
                    </div>
                  ) : (
                    <div className="p-2 rounded bg-green-500/10 border border-green-500/20">
                      <div className="flex items-center gap-2">
                        <Activity className="h-3.5 w-3.5 text-green-400 shrink-0" />
                        <span className="text-[11px] text-green-300">접촉/충돌 위험 낮음 - 안전 운영</span>
                      </div>
                    </div>
                  )}

                  {/* 힘 스파이크 감지 */}
                  {axia80.force_spike && (
                    <div className="p-2 rounded bg-red-500/10 border border-red-500/20">
                      <div className="flex items-center gap-2">
                        <Zap className="h-3.5 w-3.5 text-red-400 shrink-0" />
                        <span className="text-[11px] text-red-300 font-bold">힘 급변 감지!</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
