'use client';

import { useMemo, useState } from 'react';
import { BarChart3, Zap, AlertTriangle, TrendingUp, Activity, Target, Wrench } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSensorPatterns, useSensorReadingsRange } from '@/hooks/useApi';

interface StatisticsSummaryProps {
  predictions?: {
    total_patterns: number;
    high_risk_count: number;
  };
}

type Period = '24h' | '7d';

export function StatisticsSummary({ predictions }: StatisticsSummaryProps) {
  const [period, setPeriod] = useState<Period>('24h');

  // 패턴 데이터 (7일치)
  const { data: patternsData } = useSensorPatterns(100);

  // 기간별 센서 데이터 가져오기
  const hours = period === '24h' ? 24 : 168; // 24시간 또는 7일(168시간)
  const { data: rangeData } = useSensorReadingsRange(hours, 500);

  // Calculate statistics
  const stats = useMemo(() => {
    const now = new Date();
    const cutoff = period === '24h'
      ? new Date(now.getTime() - 24 * 60 * 60 * 1000)
      : new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    // 패턴 필터링
    const patterns = patternsData?.patterns || [];
    const filteredPatterns = patterns.filter(p => new Date(p.timestamp) >= cutoff);

    // Pattern counts by type
    const collisionCount = filteredPatterns.filter(p => p.type === 'collision').length;
    const overloadCount = filteredPatterns.filter(p => p.type === 'overload').length;
    const driftCount = filteredPatterns.filter(p =>
      p.type === 'drift' || p.type?.includes('drift')
    ).length;

    // 센서 데이터 통계 (rangeData 사용)
    const readings = rangeData?.readings || [];

    // 각 축별 평균 계산
    const fxValues = readings.map(r => r.Fx).filter((v): v is number => typeof v === 'number');
    const fyValues = readings.map(r => r.Fy).filter((v): v is number => typeof v === 'number');
    const fzValues = readings.map(r => r.Fz).filter((v): v is number => typeof v === 'number');
    const txValues = readings.map(r => r.Tx).filter((v): v is number => typeof v === 'number');
    const tyValues = readings.map(r => r.Ty).filter((v): v is number => typeof v === 'number');
    const tzValues = readings.map(r => r.Tz).filter((v): v is number => typeof v === 'number');

    const calcAvg = (arr: number[]) => arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
    const calcMin = (arr: number[]) => arr.length > 0 ? Math.min(...arr) : 0;
    const calcMax = (arr: number[]) => arr.length > 0 ? Math.max(...arr) : 0;
    const calcStdDev = (arr: number[]) => {
      if (arr.length === 0) return 0;
      const avg = calcAvg(arr);
      const squareDiffs = arr.map(v => Math.pow(v - avg, 2));
      return Math.sqrt(calcAvg(squareDiffs));
    };

    const fxAvg = calcAvg(fxValues);
    const fyAvg = calcAvg(fyValues);
    const fzAvg = calcAvg(fzValues);
    const txAvg = calcAvg(txValues);
    const tyAvg = calcAvg(tyValues);
    const tzAvg = calcAvg(tzValues);

    const fzMin = calcMin(fzValues);
    const fzStdDev = calcStdDev(fzValues);

    // Normal operation rate
    const normalReadings = fzValues.filter(v => v >= -60 && v <= 0).length;
    const normalRate = fzValues.length > 0
      ? (normalReadings / fzValues.length) * 100
      : 100;

    // 예비보전 예측 점수 계산
    // 기준: Fz 편차가 크거나, 피크가 자주 발생하면 점검 필요
    const maintenanceScore = (() => {
      let score = 100;

      // 충돌 발생 시 감점
      score -= collisionCount * 15;

      // 과부하 발생 시 감점
      score -= overloadCount * 10;

      // 드리프트 발생 시 감점
      score -= driftCount * 5;

      // Fz 표준편차가 크면 감점 (불안정)
      if (fzStdDev > 30) score -= 10;
      if (fzStdDev > 50) score -= 10;

      // Fz 피크가 심하면 감점
      if (Math.abs(fzMin) > 200) score -= 10;
      if (Math.abs(fzMin) > 500) score -= 15;

      return Math.max(0, Math.min(100, score));
    })();

    // 예비보전 상태
    const maintenanceStatus = maintenanceScore >= 80 ? '양호' :
      maintenanceScore >= 60 ? '주의' :
      maintenanceScore >= 40 ? '점검 권장' : '긴급 점검';

    return {
      collisionCount,
      overloadCount,
      driftCount,
      fxAvg: Math.round(fxAvg * 10) / 10,
      fyAvg: Math.round(fyAvg * 10) / 10,
      fzAvg: Math.round(fzAvg * 10) / 10,
      txAvg: Math.round(txAvg * 100) / 100,
      tyAvg: Math.round(tyAvg * 100) / 100,
      tzAvg: Math.round(tzAvg * 100) / 100,
      fzPeak: Math.round(fzMin * 10) / 10,
      normalRate: Math.round(normalRate * 10) / 10,
      maintenanceScore,
      maintenanceStatus,
      dataCount: readings.length,
    };
  }, [patternsData, rangeData, period]);

  return (
    <div
      className="rounded-lg border border-slate-700/50 bg-gradient-to-br from-slate-800/50 via-slate-800/30 to-slate-900/50 backdrop-blur-sm mt-4"
      style={{
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.03)',
      }}
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-slate-700/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-medium text-white">통계 요약</h3>
          <span className="text-xs text-slate-500">
            ({period === '24h' ? '최근 24시간' : '최근 7일'} · {stats.dataCount}건)
          </span>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setPeriod('24h')}
            className={cn(
              'px-2 py-1 text-xs rounded transition-colors',
              period === '24h'
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            )}
          >
            24시간
          </button>
          <button
            onClick={() => setPeriod('7d')}
            className={cn(
              'px-2 py-1 text-xs rounded transition-colors',
              period === '7d'
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            )}
          >
            7일
          </button>
        </div>
      </div>

      <div className="p-3 space-y-3">
        {/* 이벤트 통계 */}
        <div>
          <div className="text-[10px] text-slate-500 mb-1.5 font-medium">이벤트 감지</div>
          <div className="grid grid-cols-4 gap-2">
            <StatCard
              label="충돌"
              value={`${stats.collisionCount}건`}
              icon={AlertTriangle}
              color={stats.collisionCount > 0 ? 'text-red-400' : 'text-slate-400'}
              bgColor={stats.collisionCount > 0 ? 'bg-red-500/10' : 'bg-slate-700/30'}
            />
            <StatCard
              label="과부하"
              value={`${stats.overloadCount}건`}
              icon={Activity}
              color={stats.overloadCount > 0 ? 'text-orange-400' : 'text-slate-400'}
              bgColor={stats.overloadCount > 0 ? 'bg-orange-500/10' : 'bg-slate-700/30'}
            />
            <StatCard
              label="드리프트"
              value={`${stats.driftCount}건`}
              icon={TrendingUp}
              color={stats.driftCount > 0 ? 'text-yellow-400' : 'text-slate-400'}
              bgColor={stats.driftCount > 0 ? 'bg-yellow-500/10' : 'bg-slate-700/30'}
            />
            <StatCard
              label="정상률"
              value={`${stats.normalRate}%`}
              icon={Target}
              color={stats.normalRate >= 90 ? 'text-green-400' : stats.normalRate >= 70 ? 'text-yellow-400' : 'text-red-400'}
              bgColor={stats.normalRate >= 90 ? 'bg-green-500/10' : stats.normalRate >= 70 ? 'bg-yellow-500/10' : 'bg-red-500/10'}
            />
          </div>
        </div>

        {/* Axia80 센서 평균값 */}
        <div>
          <div className="text-[10px] text-slate-500 mb-1.5 font-medium">Axia80 센서 평균 ({period === '24h' ? '24시간' : '7일'})</div>
          <div className="grid grid-cols-6 gap-2">
            <SensorAvgCard label="Fx" value={stats.fxAvg} unit="N" />
            <SensorAvgCard label="Fy" value={stats.fyAvg} unit="N" />
            <SensorAvgCard label="Fz" value={stats.fzAvg} unit="N" highlight />
            <SensorAvgCard label="Tx" value={stats.txAvg} unit="Nm" />
            <SensorAvgCard label="Ty" value={stats.tyAvg} unit="Nm" />
            <SensorAvgCard label="Tz" value={stats.tzAvg} unit="Nm" />
          </div>
        </div>

        {/* 예비보전 예측 */}
        <div className={cn(
          'p-2.5 rounded-lg border',
          stats.maintenanceScore >= 80 ? 'bg-green-500/10 border-green-500/30' :
          stats.maintenanceScore >= 60 ? 'bg-yellow-500/10 border-yellow-500/30' :
          stats.maintenanceScore >= 40 ? 'bg-orange-500/10 border-orange-500/30' :
          'bg-red-500/10 border-red-500/30'
        )}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Wrench className={cn(
                'h-4 w-4',
                stats.maintenanceScore >= 80 ? 'text-green-400' :
                stats.maintenanceScore >= 60 ? 'text-yellow-400' :
                stats.maintenanceScore >= 40 ? 'text-orange-400' : 'text-red-400'
              )} />
              <span className="text-xs font-medium text-white">예비보전 상태</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className={cn(
                  'text-sm font-bold',
                  stats.maintenanceScore >= 80 ? 'text-green-400' :
                  stats.maintenanceScore >= 60 ? 'text-yellow-400' :
                  stats.maintenanceScore >= 40 ? 'text-orange-400' : 'text-red-400'
                )}>
                  {stats.maintenanceStatus}
                </div>
                <div className="text-[10px] text-slate-400">점수: {stats.maintenanceScore}/100</div>
              </div>
              <div className="w-16 h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all',
                    stats.maintenanceScore >= 80 ? 'bg-green-500' :
                    stats.maintenanceScore >= 60 ? 'bg-yellow-500' :
                    stats.maintenanceScore >= 40 ? 'bg-orange-500' : 'bg-red-500'
                  )}
                  style={{ width: `${stats.maintenanceScore}%` }}
                />
              </div>
            </div>
          </div>
          {stats.maintenanceScore < 80 && (
            <div className="mt-2 text-[10px] text-slate-400">
              {stats.collisionCount > 0 && `충돌 ${stats.collisionCount}건 감지. `}
              {stats.overloadCount > 0 && `과부하 ${stats.overloadCount}건 감지. `}
              {Math.abs(stats.fzPeak) > 200 && `Fz 피크(${stats.fzPeak}N) 과다. `}
              {stats.maintenanceScore < 60 && '정기 점검을 권장합니다.'}
            </div>
          )}
        </div>

        {/* 고위험 예측 경고 */}
        {predictions && predictions.high_risk_count > 0 && (
          <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/30">
            <div className="flex items-center gap-2 text-red-400">
              <Zap className="h-4 w-4" />
              <span className="text-xs font-medium">
                고위험 예측 {predictions.high_risk_count}건 감지됨 - 즉시 점검 권장
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// 통계 카드 컴포넌트
function StatCard({
  label,
  value,
  icon: Icon,
  color,
  bgColor,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
}) {
  return (
    <div className={cn('rounded-lg p-2 text-center', bgColor)}>
      <div className="flex items-center justify-center gap-1 mb-0.5">
        <Icon className={cn('h-3 w-3', color)} />
        <span className="text-[10px] text-slate-400 font-medium">{label}</span>
      </div>
      <div className={cn('text-base font-bold', color)}>{value}</div>
    </div>
  );
}

// 센서 평균값 카드
function SensorAvgCard({
  label,
  value,
  unit,
  highlight = false,
}: {
  label: string;
  value: number;
  unit: string;
  highlight?: boolean;
}) {
  return (
    <div className={cn(
      'rounded p-1.5 text-center',
      highlight ? 'bg-blue-500/15 border border-blue-500/30' : 'bg-slate-700/30'
    )}>
      <div className={cn(
        'text-[10px] font-medium mb-0.5',
        highlight ? 'text-blue-300' : 'text-slate-400'
      )}>
        {label}
      </div>
      <div className={cn(
        'text-sm font-bold',
        highlight ? 'text-blue-400' : 'text-slate-200'
      )}>
        {value}
        <span className="text-[9px] font-normal ml-0.5 text-slate-500">{unit}</span>
      </div>
    </div>
  );
}
