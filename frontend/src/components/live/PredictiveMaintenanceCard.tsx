'use client';

import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, AlertTriangle, AlertCircle, CheckCircle, Activity, TrendingUp, Sparkles } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { cardHover, cardTap } from '@/lib/animations';
import type { IntegratedStreamData, NodeState } from '@/types/api';

interface PredictiveMaintenanceCardProps {
  latestData: IntegratedStreamData | null;
  isConnected: boolean;
  onClick?: () => void;
}

// Status configuration
const stateConfig: Record<NodeState, { label: string; color: string; bgColor: string; borderColor: string; icon: typeof CheckCircle }> = {
  critical: { label: '위험', color: 'text-red-400', bgColor: 'bg-red-500/20', borderColor: 'border-red-500/50', icon: AlertTriangle },
  warning: { label: '경고', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', borderColor: 'border-yellow-500/50', icon: AlertCircle },
  normal: { label: '정상', color: 'text-green-400', bgColor: 'bg-green-500/20', borderColor: 'border-green-500/50', icon: CheckCircle },
};

export function PredictiveMaintenanceCard({ latestData, isConnected, onClick }: PredictiveMaintenanceCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  // 예측 데이터 분석
  const analysis = useMemo(() => {
    if (!latestData) {
      return {
        state: 'normal' as NodeState,
        torqueForceRatio: 0,
        contactRisk: 0,
        collisionRisk: 0,
        anomalyDetected: false,
        predictions: [] as string[],
      };
    }

    const { correlation, risk } = latestData;
    const predictions: string[] = [];

    // Load ratio based prediction
    if (correlation.torque_force_ratio > 2) {
      predictions.push('과부하/마모 위험 증가 추세');
    } else {
      predictions.push('부하율 정상 범위');
    }

    // Contact/collision risk based prediction
    if (risk.contact_risk_score > 0.5 || risk.collision_risk_score > 0.5) {
      if (risk.contact_risk_score > 0.5 && risk.collision_risk_score > 0.5) {
        predictions.push('접촉 + 충돌 위험 높음');
      } else if (risk.contact_risk_score > 0.5) {
        predictions.push('작업자 접촉 위험');
      } else {
        predictions.push('장애물 충돌 위험');
      }
    } else if (risk.contact_risk_score > 0.3 || risk.collision_risk_score > 0.3) {
      predictions.push('위험 수준 상승 중');
    } else {
      predictions.push('접촉/충돌 위험 낮음');
    }

    // Force spike
    if (latestData.axia80.force_spike) {
      predictions.push('힘 스파이크 감지!');
    }

    // 상태 결정
    let state: NodeState = 'normal';
    if (
      correlation.anomaly_detected ||
      risk.contact_risk_score > 0.5 ||
      risk.collision_risk_score > 0.5 ||
      latestData.axia80.force_spike
    ) {
      state = 'critical';
    } else if (
      correlation.torque_force_ratio > 2 ||
      risk.contact_risk_score > 0.3 ||
      risk.collision_risk_score > 0.3
    ) {
      state = 'warning';
    }

    return {
      state,
      torqueForceRatio: correlation.torque_force_ratio,
      contactRisk: risk.contact_risk_score,
      collisionRisk: risk.collision_risk_score,
      anomalyDetected: correlation.anomaly_detected,
      predictions,
    };
  }, [latestData]);

  const statusInfo = stateConfig[analysis.state];
  const StatusIcon = statusInfo.icon;

  return (
    <motion.div
      whileHover={cardHover}
      whileTap={cardTap}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="relative"
    >
      <Card
        onClick={onClick}
        className={cn(
          'w-[260px] h-[165px] p-3.5 cursor-pointer transition-all duration-200',
          // 상태별 테두리
          analysis.state === 'critical' && 'ring-1 ring-red-500/30 border-red-500/30',
          analysis.state === 'warning' && 'ring-1 ring-yellow-500/30 border-yellow-500/30',
          'border border-slate-700/50 hover:border-slate-500/70'
        )}
        style={{
          // 상태별 그라데이션 배경
          background: analysis.state === 'critical'
            ? 'linear-gradient(135deg, rgba(153, 27, 27, 0.95) 0%, rgba(127, 29, 29, 0.9) 50%, rgba(69, 10, 10, 0.95) 100%)'
            : analysis.state === 'warning'
            ? 'linear-gradient(135deg, rgba(146, 64, 14, 0.95) 0%, rgba(113, 63, 18, 0.9) 50%, rgba(69, 26, 3, 0.95) 100%)'
            : 'linear-gradient(135deg, rgba(51, 65, 85, 0.95) 0%, rgba(30, 41, 59, 0.9) 50%, rgba(15, 23, 42, 0.95) 100%)',
          boxShadow: analysis.state === 'critical'
            ? '0 4px 12px rgba(239, 68, 68, 0.2), inset 0 1px 0 rgba(255,255,255,0.06)'
            : analysis.state === 'warning'
            ? '0 4px 12px rgba(234, 179, 8, 0.2), inset 0 1px 0 rgba(255,255,255,0.06)'
            : '0 4px 12px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.06)',
        }}
      >
        <div className="flex flex-col h-full relative">
          {/* Header */}
          <div className="flex items-start gap-3">
            <div
              className={cn(
                'p-2 rounded-lg shrink-0 bg-gradient-to-br',
                analysis.state === 'critical' ? 'from-red-600/30 to-red-700/30' :
                analysis.state === 'warning' ? 'from-yellow-600/30 to-yellow-700/30' :
                'from-purple-600/30 to-cyan-600/30'
              )}
              style={{
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.05), 0 1px 2px rgba(0,0,0,0.1)',
              }}
            >
              <Brain className={cn(
                'h-5 w-5 drop-shadow-sm',
                analysis.state === 'critical' ? 'text-red-400' :
                analysis.state === 'warning' ? 'text-yellow-400' :
                'text-cyan-400'
              )} />
            </div>
            <div className="min-w-0 flex-1 pr-2">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium text-white">예지보전</h3>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-gradient-to-r from-purple-600 to-cyan-500 text-white font-bold flex items-center gap-0.5">
                  <Sparkles className="h-2.5 w-2.5" />
                  AI
                </span>
                {/* 상태에 따른 점 색상 */}
                {analysis.state === 'critical' && (
                  <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                )}
                {analysis.state === 'warning' && (
                  <span className="inline-block w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5 leading-tight">UR5e + Axia80 위험 예측</p>
            </div>
          </div>

          {/* Content */}
          <div className="mt-auto pt-2">
            {!latestData || !isConnected ? (
              <div className="flex items-center gap-2 mb-1">
                <Activity className="h-4 w-4 text-slate-400 animate-pulse" />
                <span className="text-sm text-slate-400">데이터 대기 중...</span>
              </div>
            ) : (
              <>
                {/* 부하율 표시 */}
                <div className="flex items-center gap-2 mb-1.5">
                  <TrendingUp className={cn(
                    'h-4 w-4',
                    analysis.torqueForceRatio > 2 ? 'text-yellow-400' : 'text-green-400'
                  )} />
                  <span className="text-xs text-slate-300">부하율</span>
                  <span className={cn(
                    'text-sm font-bold font-mono',
                    analysis.torqueForceRatio > 2 ? 'text-yellow-400' : 'text-green-400'
                  )}>
                    {analysis.torqueForceRatio.toFixed(2)}
                  </span>
                </div>
                {/* 위험도 요약 */}
                <div className="flex items-center gap-3 text-[11px]">
                  <span className="text-slate-400">
                    접촉 <span className={cn(
                      'font-bold',
                      analysis.contactRisk > 0.5 ? 'text-red-400' :
                      analysis.contactRisk > 0.3 ? 'text-yellow-400' : 'text-green-400'
                    )}>
                      {(analysis.contactRisk * 100).toFixed(0)}%
                    </span>
                  </span>
                  <span className="text-slate-400">
                    충돌 <span className={cn(
                      'font-bold',
                      analysis.collisionRisk > 0.5 ? 'text-red-400' :
                      analysis.collisionRisk > 0.3 ? 'text-yellow-400' : 'text-green-400'
                    )}>
                      {(analysis.collisionRisk * 100).toFixed(0)}%
                    </span>
                  </span>
                </div>
              </>
            )}
          </div>

          {/* Status Badge - Bottom Right */}
          <div className="absolute bottom-0 right-0">
            <Badge
              variant="outline"
              className={cn('gap-1', statusInfo.color, statusInfo.bgColor, statusInfo.borderColor)}
            >
              <StatusIcon className="h-3 w-3" />
              {statusInfo.label}
            </Badge>
          </div>
        </div>
      </Card>

      {/* Hover Tooltip - 예측 알림 요약 */}
      <AnimatePresence>
        {isHovered && latestData && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-2 z-50 w-full"
          >
            <div
              className="rounded-lg border border-slate-600/50 p-3"
              style={{
                backgroundColor: '#0f172a',
                boxShadow: '0 4px 16px rgba(0,0,0,0.5), 0 2px 4px rgba(0,0,0,0.3)',
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                <span className="text-xs font-bold text-cyan-300">AI 예측 알림</span>
              </div>
              <div className="space-y-1.5">
                {analysis.predictions.map((prediction, idx) => {
                  const isWarning = prediction.includes('위험') || prediction.includes('감지');
                  const isNormal = prediction.includes('정상') || prediction.includes('낮음');
                  return (
                    <div
                      key={idx}
                      className={cn(
                        'p-1.5 rounded text-[11px] flex items-center gap-2',
                        isWarning ? 'bg-red-500/10 border border-red-500/20' :
                        isNormal ? 'bg-green-500/10 border border-green-500/20' :
                        'bg-yellow-500/10 border border-yellow-500/20'
                      )}
                    >
                      {isWarning ? (
                        <AlertTriangle className="h-3 w-3 text-red-400 shrink-0" />
                      ) : isNormal ? (
                        <CheckCircle className="h-3 w-3 text-green-400 shrink-0" />
                      ) : (
                        <AlertCircle className="h-3 w-3 text-yellow-400 shrink-0" />
                      )}
                      <span className={cn(
                        isWarning ? 'text-red-300' :
                        isNormal ? 'text-green-300' :
                        'text-yellow-300'
                      )}>
                        {prediction}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
