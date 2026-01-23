'use client';

import { useState, useMemo, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Loader2, Info } from 'lucide-react';
import { useSensorReadingsRange } from '@/hooks/useApi';
import type { SensorReading } from '@/types/api';

type AxisType = 'Fx' | 'Fy' | 'Fz' | 'Tx' | 'Ty' | 'Tz';
type TimeRange = 'realtime' | '1h' | '24h' | '7d';

const timeRangeConfig: Record<TimeRange, { label: string; hours: number; samples: number }> = {
  realtime: { label: '실시간', hours: 0, samples: 60 },
  '1h': { label: '1시간', hours: 1, samples: 200 },
  '24h': { label: '24시간', hours: 24, samples: 300 },
  '7d': { label: '7일', hours: 168, samples: 500 },
};

interface RealtimeChartProps {
  data: SensorReading[];
  axis?: AxisType;
  axes?: AxisType[];
  thresholds?: {
    warning: number;
    critical: number;
  };
  title?: string;
}

const axisConfig: Record<AxisType, { label: string; labelKo: string; unit: string; color: string }> = {
  Fx: { label: 'Force X', labelKo: 'Fx (전후력)', unit: 'N', color: '#3b82f6' },
  Fy: { label: 'Force Y', labelKo: 'Fy (좌우력)', unit: 'N', color: '#22c55e' },
  Fz: { label: 'Force Z', labelKo: 'Fz (수직력)', unit: 'N', color: '#ef4444' },
  Tx: { label: 'Torque X', labelKo: 'Tx', unit: 'Nm', color: '#f97316' },
  Ty: { label: 'Torque Y', labelKo: 'Ty', unit: 'Nm', color: '#8b5cf6' },
  Tz: { label: 'Torque Z', labelKo: 'Tz', unit: 'Nm', color: '#06b6d4' },
};

export function RealtimeChart({ data, axis, axes, thresholds, title }: RealtimeChartProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('realtime');

  // Support both single axis and multiple axes
  const allAxes: AxisType[] = axes || (axis ? [axis] : ['Fz']);
  const [visibleAxes, setVisibleAxes] = useState<Set<AxisType>>(new Set(allAxes));
  const displayAxes = allAxes.filter((ax) => visibleAxes.has(ax));

  // Fix hydration mismatch - only render chart after mount
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const toggleAxis = (ax: AxisType) => {
    setVisibleAxes((prev) => {
      const next = new Set(prev);
      if (next.has(ax)) {
        // Don't allow hiding all axes
        if (next.size > 1) next.delete(ax);
      } else {
        next.add(ax);
      }
      return next;
    });
  };

  // Fetch historical data when not in realtime mode
  const rangeConfig = timeRangeConfig[timeRange];
  const { data: rangeData, isLoading: rangeLoading } = useSensorReadingsRange(
    rangeConfig.hours,
    rangeConfig.samples,
    timeRange !== 'realtime'
  );

  // Use realtime data or historical data based on mode
  const activeData = useMemo(() => {
    if (timeRange === 'realtime') return data;
    if (!rangeData?.readings) return [];
    return rangeData.readings.map((r) => ({
      timestamp: r.timestamp,
      Fx: r.Fx,
      Fy: r.Fy,
      Fz: r.Fz,
      Tx: r.Tx,
      Ty: r.Ty,
      Tz: r.Tz,
    }));
  }, [timeRange, data, rangeData]);

  // Format time based on range
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    if (timeRange === 'realtime' || timeRange === '1h') {
      return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    } else if (timeRange === '24h') {
      return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    } else {
      // 7d: show date
      return date.toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' });
    }
  };

  // Format data for chart
  const chartData = activeData.map((reading) => {
    const point: Record<string, unknown> = {
      time: formatTime(reading.timestamp),
      timestamp: reading.timestamp,
      fullTime: new Date(reading.timestamp).toLocaleString('ko-KR'),
    };
    displayAxes.forEach((ax) => {
      point[ax] = reading[ax];
    });
    return point;
  });

  return (
    <Card
      className="p-4 border-slate-700/50 bg-gradient-to-br from-slate-800/60 via-slate-800/40 to-slate-900/60 backdrop-blur-sm"
      style={{
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.03)',
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-medium text-white">
            {title || `힘 센서 실시간 모니터링`}
          </h3>
          {/* Time range selector */}
          <div className="flex items-center gap-1 bg-slate-700/50 rounded-lg p-1">
            {(Object.keys(timeRangeConfig) as TimeRange[]).map((range) => (
              <Button
                key={range}
                variant={timeRange === range ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setTimeRange(range)}
                className={`h-6 px-2 text-xs ${
                  timeRange === range
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-slate-600'
                }`}
              >
                {timeRangeConfig[range].label}
              </Button>
            ))}
          </div>
          {rangeLoading && timeRange !== 'realtime' && (
            <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
          )}
        </div>
        <div className="flex items-center gap-4">
          {allAxes.map((ax) => (
            <label
              key={ax}
              className="flex items-center gap-2 cursor-pointer select-none"
            >
              <Checkbox
                checked={visibleAxes.has(ax)}
                onCheckedChange={() => toggleAxis(ax)}
                className="h-4 w-4 border-slate-500 data-[state=checked]:bg-transparent data-[state=checked]:border-slate-500"
                style={{
                  backgroundColor: visibleAxes.has(ax) ? axisConfig[ax].color : 'transparent',
                  borderColor: axisConfig[ax].color,
                }}
              />
              <span className={`text-xs ${visibleAxes.has(ax) ? 'text-slate-300' : 'text-slate-500'}`}>
                {axisConfig[ax].labelKo}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Demo notice */}
      <div className="flex items-center gap-1.5 -mt-0.5 mb-0.5">
        <Info className="h-3.5 w-3.5 text-red-400 shrink-0" />
        <span className="text-xs text-red-400">
          데모 버전: 2024-01-15 ~ 2024-01-21 (7일) 샘플 데이터가 제공됩니다.
        </span>
      </div>

      <div className="h-[200px]">
        {isMounted ? (
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="time"
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
            />
            <YAxis
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              domain={['auto', 'auto']}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              labelStyle={{ color: '#94a3b8' }}
              labelFormatter={(_, payload) => {
                if (payload && payload.length > 0) {
                  const fullTime = payload[0]?.payload?.fullTime;
                  return fullTime || '';
                }
                return '';
              }}
              formatter={(value: unknown, name?: string) => {
                if (typeof value !== 'number' || !name) return ['-', name || ''];
                const cfg = axisConfig[name as AxisType];
                return [`${value.toFixed(2)} ${cfg?.unit || 'N'}`, cfg?.labelKo || name];
              }}
            />

            {/* Threshold lines */}
            {thresholds?.warning && (
              <ReferenceLine
                y={thresholds.warning}
                stroke="#eab308"
                strokeDasharray="5 5"
                label={{
                  value: '경고',
                  fill: '#eab308',
                  fontSize: 10,
                  position: 'right',
                }}
              />
            )}
            {thresholds?.critical && (
              <ReferenceLine
                y={thresholds.critical}
                stroke="#ef4444"
                strokeDasharray="5 5"
                label={{
                  value: '위험',
                  fill: '#ef4444',
                  fontSize: 10,
                  position: 'right',
                }}
              />
            )}

            {displayAxes.map((ax) => (
              <Line
                key={ax}
                type="monotone"
                dataKey={ax}
                stroke={axisConfig[ax].color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: axisConfig[ax].color }}
              />
            ))}
          </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-full h-full" />
        )}
      </div>
    </Card>
  );
}
