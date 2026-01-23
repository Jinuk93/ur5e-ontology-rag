'use client';

import { useMemo } from 'react';
import { Zap, Activity, Cpu, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SensorReading } from '@/types/api';
import type { RealtimePrediction } from '@/lib/api';

interface HeterogeneousPredictionProps {
  readings: SensorReading[];
  predictions?: RealtimePrediction[];
  maxHeight?: string;
}

// 위험도 레벨 색상
const riskLevelConfig = {
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

export function HeterogeneousPrediction({
  readings,
  predictions,
  maxHeight = '250px'
}: HeterogeneousPredictionProps) {
  // 최근 센서 데이터 통계
  const sensorStats = useMemo(() => {
    if (readings.length === 0) return null;

    const latest = readings[readings.length - 1];
    const recentReadings = readings.slice(-30); // 최근 30개

    // 평균 계산
    const avgFz = recentReadings.reduce((sum, r) => sum + (r.Fz || 0), 0) / recentReadings.length;
    const avgFx = recentReadings.reduce((sum, r) => sum + (r.Fx || 0), 0) / recentReadings.length;
    const avgFy = recentReadings.reduce((sum, r) => sum + (r.Fy || 0), 0) / recentReadings.length;

    // 최대값 (절대값)
    const maxFz = Math.min(...recentReadings.map(r => r.Fz || 0));

    return {
      current: {
        Fx: latest.Fx?.toFixed(1) || '0',
        Fy: latest.Fy?.toFixed(1) || '0',
        Fz: latest.Fz?.toFixed(1) || '0',
        Tx: latest.Tx?.toFixed(2) || '0',
        Ty: latest.Ty?.toFixed(2) || '0',
        Tz: latest.Tz?.toFixed(2) || '0',
      },
      avg: {
        Fx: avgFx.toFixed(1),
        Fy: avgFy.toFixed(1),
        Fz: avgFz.toFixed(1),
      },
      peak: {
        Fz: maxFz.toFixed(1),
      },
      timestamp: latest.timestamp,
    };
  }, [readings]);

  // 예측 데이터 가공
  const predictionItems = useMemo(() => {
    if (!predictions || predictions.length === 0) return [];

    return predictions.map(pred => {
      const riskLevel = pred.risk_level as keyof typeof riskLevelConfig || 'low';
      const config = riskLevelConfig[riskLevel] || riskLevelConfig.low;

      return {
        id: pred.pattern_detected || 'unknown',
        pattern: pred.pattern_detected?.replace('PAT_', '') || '알 수 없음',
        riskLevel,
        config,
        predictions: pred.predictions.slice(0, 3), // 상위 3개만
        timestamp: pred.timestamp,
      };
    });
  }, [predictions]);

  const getRiskLevelLabel = (level: string) => {
    switch (level) {
      case 'critical': return '심각';
      case 'high': return '높음';
      case 'medium': return '중간';
      case 'low': return '낮음';
      default: return level;
    }
  };

  const getPatternLabel = (pattern: string) => {
    switch (pattern.toLowerCase()) {
      case 'collision': return '충돌 패턴';
      case 'overload': return '과부하 패턴';
      case 'drift': return '드리프트 패턴';
      default: return pattern;
    }
  };

  return (
    <div
      className="rounded-lg border border-slate-700/50 bg-gradient-to-br from-slate-800/50 via-slate-800/30 to-slate-900/50 backdrop-blur-sm mt-4"
      style={{
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.03)',
      }}
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-blue-400" />
          <h3 className="text-sm font-medium text-white">이기종 결합 예측</h3>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-medium">
            Ontology AI
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          UR5e 로봇과 Axia80 센서 데이터를 온톨로지 기반으로 결합 분석합니다.
        </p>
      </div>

      <div className="p-3">
        {/* 데이터 소스 표시 */}
        <div className="grid grid-cols-2 gap-3 mb-3">
          {/* UR5e 로봇 상태 */}
          <div className="rounded-lg p-2 bg-slate-700/30 border border-slate-600/30">
            <div className="flex items-center gap-1.5 mb-2">
              <Cpu className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-xs font-medium text-emerald-400">UR5e 로봇</span>
            </div>
            <div className="grid grid-cols-2 gap-1 text-[10px]">
              <div className="text-slate-400">상태</div>
              <div className="text-slate-200 font-medium">운전 중</div>
              <div className="text-slate-400">모드</div>
              <div className="text-slate-200 font-medium">자동</div>
            </div>
          </div>

          {/* Axia80 센서 값 */}
          <div className="rounded-lg p-2 bg-slate-700/30 border border-slate-600/30">
            <div className="flex items-center gap-1.5 mb-2">
              <Activity className="h-3.5 w-3.5 text-cyan-400" />
              <span className="text-xs font-medium text-cyan-400">Axia80 센서</span>
            </div>
            {sensorStats ? (
              <div className="grid grid-cols-3 gap-1 text-[10px]">
                <div>
                  <div className="text-slate-400">Fz</div>
                  <div className="text-slate-200 font-medium">{sensorStats.current.Fz}N</div>
                </div>
                <div>
                  <div className="text-slate-400">Fx</div>
                  <div className="text-slate-200 font-medium">{sensorStats.current.Fx}N</div>
                </div>
                <div>
                  <div className="text-slate-400">Fy</div>
                  <div className="text-slate-200 font-medium">{sensorStats.current.Fy}N</div>
                </div>
              </div>
            ) : (
              <div className="text-[10px] text-slate-500">데이터 없음</div>
            )}
          </div>
        </div>

        {/* 예측 결과 테이블 */}
        <div className="overflow-auto" style={{ maxHeight }}>
          {predictionItems.length === 0 ? (
            <div className="text-center py-6 text-slate-500 text-sm">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>감지된 패턴이 없습니다</p>
              <p className="text-xs mt-1">정상 운전 중입니다</p>
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-slate-800/95 z-10">
                <tr className="border-b border-slate-700/50">
                  <th className="text-left py-2 px-2 text-slate-400 font-semibold">감지 패턴</th>
                  <th className="text-center py-2 px-2 text-slate-400 font-semibold">위험도</th>
                  <th className="text-center py-2 px-2 text-blue-300 font-semibold bg-blue-950/50">예측 에러</th>
                  <th className="text-center py-2 px-2 text-blue-300 font-semibold bg-blue-950/50">확률</th>
                  <th className="text-left py-2 px-2 text-slate-400 font-semibold">권장 조치</th>
                </tr>
              </thead>
              <tbody>
                {predictionItems.map((item) => (
                  item.predictions.map((pred, idx) => (
                    <tr
                      key={`${item.id}-${idx}`}
                      className="border-b border-slate-700/30 hover:bg-slate-700/20"
                    >
                      {idx === 0 && (
                        <>
                          <td
                            className="py-2 px-2 text-slate-200 font-medium"
                            rowSpan={item.predictions.length}
                          >
                            {getPatternLabel(item.pattern)}
                          </td>
                          <td
                            className="py-2 px-2 text-center"
                            rowSpan={item.predictions.length}
                          >
                            <span className={cn(
                              'inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold',
                              item.config.bgColor,
                              item.config.color
                            )}>
                              {getRiskLevelLabel(item.riskLevel)}
                            </span>
                          </td>
                        </>
                      )}
                      <td className="py-2 px-2 text-center bg-blue-950/30">
                        <span className="text-blue-300 font-bold">{pred.error_code}</span>
                      </td>
                      <td className="py-2 px-2 text-center bg-blue-950/30">
                        <span className={cn(
                          'font-medium',
                          pred.probability >= 0.7 ? 'text-red-400' :
                          pred.probability >= 0.4 ? 'text-yellow-400' : 'text-green-400'
                        )}>
                          {Math.round(pred.probability * 100)}%
                        </span>
                      </td>
                      <td className="py-2 px-2 text-slate-300 text-[10px]">
                        {pred.recommendation || '-'}
                      </td>
                    </tr>
                  ))
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
