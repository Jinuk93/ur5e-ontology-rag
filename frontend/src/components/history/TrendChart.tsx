'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { SensorReading } from '@/types/api';

interface TrendChartProps {
  data: SensorReading[];
  axis: 'Fx' | 'Fy' | 'Fz' | 'Tx' | 'Ty' | 'Tz';
  title?: string;
  patternMarkers?: Array<{
    timestamp: string;
    type: 'collision' | 'overload' | 'drift';
  }>;
}

const patternColors = {
  collision: '#ef4444',
  overload: '#f97316',
  drift: '#eab308',
};

export function TrendChart({ data, axis, title, patternMarkers }: TrendChartProps) {
  // Aggregate data by hour for trend view
  const chartData = data.map((reading) => {
    const date = new Date(reading.timestamp);
    return {
      time: date.toLocaleDateString('ko-KR', {
        month: 'numeric',
        day: 'numeric',
      }),
      value: reading[axis],
      timestamp: reading.timestamp,
    };
  });

  // Count patterns by type
  const patternCounts = (patternMarkers || []).reduce(
    (acc, p) => {
      acc[p.type] = (acc[p.type] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <Card className="p-4 bg-slate-800/50 border-slate-700/50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-white">
          {title || `${axis} 추세`}
        </h3>
        <div className="flex gap-2">
          {patternCounts.collision > 0 && (
            <Badge variant="destructive" className="text-xs">
              충돌 {patternCounts.collision}건
            </Badge>
          )}
          {patternCounts.overload > 0 && (
            <Badge className="text-xs bg-orange-500/20 text-orange-400 border-orange-500/50">
              과부하 {patternCounts.overload}건
            </Badge>
          )}
          {patternCounts.drift > 0 && (
            <Badge className="text-xs bg-yellow-500/20 text-yellow-400 border-yellow-500/50">
              드리프트 {patternCounts.drift}건
            </Badge>
          )}
        </div>
      </div>

      <div className="h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
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
            />

            {/* Warning threshold */}
            <ReferenceLine
              y={-60}
              stroke="#eab308"
              strokeDasharray="5 5"
            />
            <ReferenceLine
              y={-200}
              stroke="#ef4444"
              strokeDasharray="5 5"
            />

            <Area
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorValue)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
