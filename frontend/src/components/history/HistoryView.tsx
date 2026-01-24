'use client';

import { useState, useEffect } from 'react';
import { TrendChart } from './TrendChart';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useUIStore } from '@/stores/uiStore';
import type { SensorReading, Pattern } from '@/types/api';

// Time range options
const timeRanges = [
  { id: '1h' as const, label: '1시간' },
  { id: '24h' as const, label: '24시간' },
  { id: '7d' as const, label: '7일' },
];

// Mock sensor trend data
function generateTrendData(days: number): SensorReading[] {
  const data: SensorReading[] = [];
  const now = Date.now();
  const hoursPerDay = 24;
  const pointsPerDay = hoursPerDay;

  for (let d = days - 1; d >= 0; d--) {
    for (let h = 0; h < pointsPerDay; h++) {
      const timestamp = new Date(now - d * 86400000 - h * 3600000).toISOString();
      const baseNoise = Math.random() * 30 - 15;
      const spike = Math.random() > 0.95 ? -100 - Math.random() * 100 : 0;

      data.push({
        timestamp,
        Fx: -5 + baseNoise * 0.3,
        Fy: 3 + baseNoise * 0.2,
        Fz: -50 + baseNoise + spike,
        Tx: 0.1 + baseNoise * 0.01,
        Ty: -0.1 + baseNoise * 0.01,
        Tz: 0.05 + baseNoise * 0.01,
      });
    }
  }

  return data;
}

// Mock patterns
const mockPatterns: Pattern[] = [
  {
    id: 'pat-1',
    type: 'collision',
    timestamp: new Date(Date.now() - 3 * 86400000).toISOString(),
    confidence: 1.0,
    metrics: { peakValue: -829 },
    relatedErrorCodes: ['C153'],
  },
  {
    id: 'pat-2',
    type: 'collision',
    timestamp: new Date(Date.now() - 1 * 86400000).toISOString(),
    confidence: 1.0,
    metrics: { peakValue: -815 },
    relatedErrorCodes: ['C153'],
  },
  {
    id: 'pat-3',
    type: 'overload',
    timestamp: new Date(Date.now() - 4 * 86400000).toISOString(),
    confidence: 1.0,
    metrics: { duration: 9 },
    relatedErrorCodes: [],
  },
  {
    id: 'pat-4',
    type: 'overload',
    timestamp: new Date(Date.now() - 2 * 86400000).toISOString(),
    confidence: 0.95,
    metrics: { duration: 6 },
    relatedErrorCodes: [],
  },
  {
    id: 'pat-5',
    type: 'drift',
    timestamp: new Date(Date.now() - 5 * 86400000).toISOString(),
    confidence: 0.87,
    metrics: { deviation: 12 },
    relatedErrorCodes: [],
  },
];

const patternTypeLabels: Record<Pattern['type'], string> = {
  collision: '충돌',
  overload: '과부하',
  drift: '드리프트',
  vibration: '진동',
};

const patternTypeColors: Record<Pattern['type'], string> = {
  collision: 'bg-red-500/20 text-red-400 border-red-500/50',
  overload: 'bg-orange-500/20 text-orange-400 border-orange-500/50',
  drift: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
  vibration: 'bg-purple-500/20 text-purple-400 border-purple-500/50',
};

export function HistoryView() {
  const { timeRange, setTimeRange, setGraphCenterNode, setCurrentView } = useUIStore();
  const [trendData] = useState(() => generateTrendData(7));

  // Hydration 에러 방지: 클라이언트에서만 날짜 포맷팅
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const patternMarkers = mockPatterns.map((p) => ({
    timestamp: p.timestamp,
    type: p.type as 'collision' | 'overload' | 'drift',
  }));

  const handlePatternClick = (pattern: Pattern) => {
    if (pattern.relatedErrorCodes.length > 0) {
      setGraphCenterNode(pattern.relatedErrorCodes[0]);
      setCurrentView('graph');
    }
  };

  const formatTimestamp = (ts: string) => {
    if (!isMounted) return '-'; // SSR에서는 placeholder
    const date = new Date(ts);
    return date.toLocaleDateString('ko-KR', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="flex flex-col h-full overflow-auto">
      {/* Time Range Selector */}
      <div className="flex items-center gap-2 p-4 border-b border-slate-700/50">
        <span className="text-sm text-slate-400">기간:</span>
        {timeRanges.map((range) => (
          <Button
            key={range.id}
            variant={timeRange === range.id ? 'default' : 'outline'}
            size="sm"
            onClick={() => setTimeRange(range.id)}
            className={
              timeRange === range.id
                ? ''
                : 'border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800'
            }
          >
            {range.label}
          </Button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-6">
        {/* Trend Chart */}
        <TrendChart
          data={trendData}
          axis="Fz"
          title="Fz 추세 (7일)"
          patternMarkers={patternMarkers}
        />

        {/* Pattern Summary */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3">감지된 패턴</h3>
          <Card className="bg-slate-800/50 border-slate-700/50 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50">
                    <th className="text-left text-slate-400 font-medium px-4 py-3">시각</th>
                    <th className="text-left text-slate-400 font-medium px-4 py-3">타입</th>
                    <th className="text-left text-slate-400 font-medium px-4 py-3">신뢰도</th>
                    <th className="text-left text-slate-400 font-medium px-4 py-3">상세</th>
                  </tr>
                </thead>
                <tbody>
                  {mockPatterns.map((pattern) => (
                    <tr
                      key={pattern.id}
                      onClick={() => handlePatternClick(pattern)}
                      className="border-b border-slate-700/30 hover:bg-slate-700/30 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3 text-slate-300">
                        {formatTimestamp(pattern.timestamp)}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          variant="outline"
                          className={patternTypeColors[pattern.type]}
                        >
                          {patternTypeLabels[pattern.type]}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-slate-300">
                        {Math.round(pattern.confidence * 100)}%
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs">
                        {pattern.metrics.peakValue && `피크값: ${pattern.metrics.peakValue}N`}
                        {pattern.metrics.duration && `지속시간: ${pattern.metrics.duration}초`}
                        {pattern.metrics.deviation && `편차: ${pattern.metrics.deviation}%`}
                        {pattern.relatedErrorCodes.length > 0 && (
                          <span className="ml-2 text-orange-400">
                            {pattern.relatedErrorCodes.join(', ')}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* Prediction (placeholder) */}
        <Card className="p-4 bg-slate-800/50 border-slate-700/50">
          <h3 className="text-sm font-medium text-slate-400 mb-3">예측</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-yellow-400">⚠️</span>
              <span className="text-slate-300">24시간 내 C153 발생 확률: 15%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-blue-400">📈</span>
              <span className="text-slate-300">Drift 추세 감지: 주의 필요</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
