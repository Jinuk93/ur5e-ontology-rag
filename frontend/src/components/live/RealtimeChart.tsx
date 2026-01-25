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
import { Loader2 } from 'lucide-react';
import { useSensorReadingsRange } from '@/hooks/useApi';
import type { SensorReading, IntegratedStreamData } from '@/types/api';

// Axia80 센서 축
type Axia80AxisType = 'Fx' | 'Fy' | 'Fz' | 'Tx' | 'Ty' | 'Tz';
// UR5e 텔레메트리 축
type UR5eAxisType = 'tcp_speed' | 'joint_torque_sum' | 'joint_current_avg';
// 통합 축 타입
type AxisType = Axia80AxisType | UR5eAxisType;
type TimeRange = 'realtime' | '1h' | '24h' | '7d';

const timeRangeConfig: Record<TimeRange, { label: string; hours: number; samples: number }> = {
  realtime: { label: '실시간', hours: 0, samples: 60 },
  '1h': { label: '1시간', hours: 1, samples: 200 },
  '24h': { label: '24시간', hours: 24, samples: 300 },
  '7d': { label: '7일', hours: 168, samples: 500 },
};

interface RealtimeChartProps {
  data: SensorReading[];
  integratedData?: IntegratedStreamData[];
  axis?: AxisType;
  axes?: AxisType[];
  thresholds?: {
    warning: number;
    critical: number;
  };
  title?: string;
}

const axisConfig: Record<AxisType, { label: string; labelKo: string; unit: string; color: string; category: 'axia80' | 'ur5e' }> = {
  // Axia80 힘 센서
  Fx: { label: 'Force X', labelKo: 'Fx (전후력)', unit: 'N', color: '#3b82f6', category: 'axia80' },
  Fy: { label: 'Force Y', labelKo: 'Fy (좌우력)', unit: 'N', color: '#22c55e', category: 'axia80' },
  Fz: { label: 'Force Z', labelKo: 'Fz (수직력)', unit: 'N', color: '#ef4444', category: 'axia80' },
  Tx: { label: 'Torque X', labelKo: 'Tx', unit: 'Nm', color: '#f97316', category: 'axia80' },
  Ty: { label: 'Torque Y', labelKo: 'Ty', unit: 'Nm', color: '#8b5cf6', category: 'axia80' },
  Tz: { label: 'Torque Z', labelKo: 'Tz', unit: 'Nm', color: '#06b6d4', category: 'axia80' },
  // UR5e 텔레메트리
  tcp_speed: { label: 'TCP Speed', labelKo: 'TCP 속도', unit: 'm/s', color: '#f43f5e', category: 'ur5e' },
  joint_torque_sum: { label: 'Joint Torque', labelKo: '관절 토크 합', unit: 'Nm', color: '#a855f7', category: 'ur5e' },
  joint_current_avg: { label: 'Joint Current', labelKo: '평균 전류', unit: 'A', color: '#14b8a6', category: 'ur5e' },
};

export function RealtimeChart({ data, integratedData, axis, axes, thresholds, title }: RealtimeChartProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('realtime');

  // Support both single axis and multiple axes - include UR5e axes if integratedData is provided
  const defaultAxes: AxisType[] = integratedData && integratedData.length > 0
    ? ['Fz', 'tcp_speed', 'joint_current_avg'] // 통합 데이터 사용 시 기본값
    : ['Fz'];
  const allAxes: AxisType[] = axes || (axis ? [axis] : defaultAxes);
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

  // Check if we have integrated data with UR5e
  const hasIntegratedData = integratedData && integratedData.length > 0;

  // Use realtime data or historical data based on mode
  const activeData = useMemo(() => {
    if (timeRange === 'realtime') {
      // 통합 데이터가 있으면 UR5e 데이터 포함
      if (hasIntegratedData) {
        return integratedData.map((d) => ({
          timestamp: d.timestamp,
          // Axia80 데이터
          Fx: d.axia80.Fx,
          Fy: d.axia80.Fy,
          Fz: d.axia80.Fz,
          Tx: d.axia80.Tx,
          Ty: d.axia80.Ty,
          Tz: d.axia80.Tz,
          // UR5e 데이터
          tcp_speed: d.ur5e.tcp_speed,
          joint_torque_sum: d.ur5e.joint_torque_sum,
          joint_current_avg: d.ur5e.joint_current_avg,
        }));
      }
      return data;
    }
    if (!rangeData?.readings) return [];
    return rangeData.readings.map((r) => ({
      timestamp: r.timestamp,
      Fx: r.Fx,
      Fy: r.Fy,
      Fz: r.Fz,
      Tx: r.Tx,
      Ty: r.Ty,
      Tz: r.Tz,
      // Historical 데이터는 UR5e 없음
      tcp_speed: undefined,
      joint_torque_sum: undefined,
      joint_current_avg: undefined,
    }));
  }, [timeRange, data, integratedData, hasIntegratedData, rangeData]);

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
      point[ax] = (reading as unknown as Record<string, unknown>)[ax];
    });
    return point;
  });

  return (
    <Card
      className="p-4 border-slate-700/50 bg-gradient-to-br from-slate-800/60 via-slate-800/40 to-slate-900/60 backdrop-blur-sm"
      style={{
        boxShadow: '0 4px 16px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.08), inset 0 -1px 0 rgba(0,0,0,0.2)',
      }}
    >
      <div className="flex items-center justify-between mb-0">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-medium text-white">
            {title || (hasIntegratedData ? `UR5e + Axia80 센서 통합 모니터링` : `힘 센서 실시간 모니터링`)}
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
        <div className="flex items-center gap-1">
          {/* Axia80 축 (힘 센서) */}
          <span className="text-[10px] text-slate-500 mr-1">Axia80:</span>
          {allAxes.filter((ax) => axisConfig[ax].category === 'axia80').map((ax) => (
            <label
              key={ax}
              className="flex items-center gap-1.5 cursor-pointer select-none mr-2"
            >
              <Checkbox
                checked={visibleAxes.has(ax)}
                onCheckedChange={() => toggleAxis(ax)}
                className="h-3.5 w-3.5 border-slate-500 data-[state=checked]:bg-transparent data-[state=checked]:border-slate-500"
                style={{
                  backgroundColor: visibleAxes.has(ax) ? axisConfig[ax].color : 'transparent',
                  borderColor: axisConfig[ax].color,
                }}
              />
              <span className={`text-[10px] ${visibleAxes.has(ax) ? 'text-slate-300' : 'text-slate-500'}`}>
                {axisConfig[ax].labelKo}
              </span>
            </label>
          ))}
          {/* UR5e 축 (로봇 텔레메트리) - 통합 데이터가 있을 때만 표시 */}
          {hasIntegratedData && (
            <>
              <div className="w-px h-4 bg-slate-600 mx-2" />
              <span className="text-[10px] text-slate-500 mr-1">UR5e:</span>
              {allAxes.filter((ax) => axisConfig[ax].category === 'ur5e').map((ax) => (
                <label
                  key={ax}
                  className="flex items-center gap-1.5 cursor-pointer select-none mr-2"
                >
                  <Checkbox
                    checked={visibleAxes.has(ax)}
                    onCheckedChange={() => toggleAxis(ax)}
                    className="h-3.5 w-3.5 border-slate-500 data-[state=checked]:bg-transparent data-[state=checked]:border-slate-500"
                    style={{
                      backgroundColor: visibleAxes.has(ax) ? axisConfig[ax].color : 'transparent',
                      borderColor: axisConfig[ax].color,
                    }}
                  />
                  <span className={`text-[10px] ${visibleAxes.has(ax) ? 'text-slate-300' : 'text-slate-500'}`}>
                    {axisConfig[ax].labelKo}
                  </span>
                </label>
              ))}
            </>
          )}
        </div>
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
