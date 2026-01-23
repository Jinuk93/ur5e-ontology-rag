'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { Card } from '@/components/ui/card';
import type { SensorReading } from '@/types/api';

type AxisType = 'Fx' | 'Fy' | 'Fz' | 'Tx' | 'Ty' | 'Tz';

interface RealtimeChartProps {
  data: SensorReading[];
  axis: AxisType;
  thresholds?: {
    warning: number;
    critical: number;
  };
  title?: string;
}

const axisConfig: Record<AxisType, { label: string; unit: string; color: string }> = {
  Fx: { label: 'Force X', unit: 'N', color: '#3b82f6' },
  Fy: { label: 'Force Y', unit: 'N', color: '#22c55e' },
  Fz: { label: 'Force Z', unit: 'N', color: '#ef4444' },
  Tx: { label: 'Torque X', unit: 'Nm', color: '#f97316' },
  Ty: { label: 'Torque Y', unit: 'Nm', color: '#8b5cf6' },
  Tz: { label: 'Torque Z', unit: 'Nm', color: '#06b6d4' },
};

export function RealtimeChart({ data, axis, thresholds, title }: RealtimeChartProps) {
  const config = axisConfig[axis];
  const isBrowser = typeof window !== 'undefined';

  // Format data for chart
  const chartData = data.map((reading) => ({
    time: new Date(reading.timestamp).toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    value: reading[axis],
    timestamp: reading.timestamp,
  }));

  return (
    <Card className="p-4 bg-slate-800/50 border-slate-700/50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-white">
          {title || `${config.label} (${config.unit})`}
        </h3>
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: config.color }}
          />
          <span className="text-xs text-slate-400">{axis}</span>
        </div>
      </div>

      <div className="h-[200px]">
        {isBrowser ? (
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
              formatter={(value) => {
                if (typeof value !== 'number') return ['-', config.label];
                return [`${value.toFixed(2)} ${config.unit}`, config.label];
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

            <Line
              type="monotone"
              dataKey="value"
              stroke={config.color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: config.color }}
            />
          </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-full h-full" />
        )}
      </div>
    </Card>
  );
}
