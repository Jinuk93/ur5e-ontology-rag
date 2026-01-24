'use client';

import { useMemo } from 'react';
import { AlertTriangle, AlertCircle, Clock, Zap, Shield, Activity } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { LiveDetectedEvent } from '@/stores/alertStore';
import { getScenarioName, getRiskLevelName } from '@/stores/alertStore';

interface LiveDetectedEventListProps {
  events: LiveDetectedEvent[];
  maxHeight?: string;
}

export function LiveDetectedEventList({ events, maxHeight = '200px' }: LiveDetectedEventListProps) {
  // 최근 10개만 표시
  const recentEvents = useMemo(() => events.slice(0, 10), [events]);

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'high':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    }
  };

  const getScenarioIcon = (scenario: string) => {
    switch (scenario) {
      case 'collision':
        return <Zap className="h-4 w-4 text-red-400" />;
      case 'overload':
        return <AlertTriangle className="h-4 w-4 text-orange-400" />;
      case 'wear':
        return <Activity className="h-4 w-4 text-yellow-400" />;
      case 'risk_approach':
        return <Shield className="h-4 w-4 text-purple-400" />;
      default:
        return <AlertCircle className="h-4 w-4 text-blue-400" />;
    }
  };

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

  if (recentEvents.length === 0) return null;

  return (
    <Card className="mb-4 p-4 bg-slate-900/50 border-slate-700">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-yellow-400" />
          <span className="text-sm font-medium text-slate-200">
            실시간 감지 이벤트
          </span>
          <Badge variant="outline" className="text-xs text-yellow-400 border-yellow-500/50">
            {events.length}개
          </Badge>
        </div>
        <span className="text-xs text-slate-500">최근 10개 표시</span>
      </div>

      <ScrollArea style={{ maxHeight }} className="pr-4">
        <div className="space-y-2">
          {recentEvents.map((event) => (
            <div
              key={event.id}
              className={`p-3 rounded-lg border ${
                event.resolved
                  ? 'bg-slate-800/50 border-slate-700/50 opacity-70'
                  : 'bg-slate-800 border-slate-600 animate-pulse-subtle'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  {getScenarioIcon(event.scenario)}
                  <span className="font-medium text-sm text-slate-200">
                    {getScenarioName(event.scenario)}
                  </span>
                  <Badge
                    variant="outline"
                    className={`text-xs ${getRiskColor(event.riskLevel)}`}
                  >
                    {getRiskLevelName(event.riskLevel)}
                  </Badge>
                  {!event.resolved && (
                    <Badge
                      variant="outline"
                      className="text-xs bg-red-500/20 text-red-400 border-red-500/50 animate-pulse"
                    >
                      진행 중
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-1 text-xs text-slate-500">
                  <Clock className="h-3 w-3" />
                  {formatTime(event.timestamp)}
                </div>
              </div>

              <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                <div className="flex items-center gap-1">
                  <span className="text-slate-500">최대 힘:</span>
                  <span className="text-slate-300 font-mono">
                    {event.maxForce.toFixed(1)}N
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-slate-500">최대 위험:</span>
                  <span className="text-slate-300 font-mono">
                    {(event.maxRiskScore * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-slate-500">지속시간:</span>
                  <span className="text-slate-300 font-mono">
                    {event.duration.toFixed(1)}초
                  </span>
                </div>
                {event.details.protectiveStop && (
                  <div className="flex items-center gap-1">
                    <Shield className="h-3 w-3 text-red-400" />
                    <span className="text-red-400">보호정지</span>
                  </div>
                )}
              </div>

              {event.resolved && event.resolvedAt && (
                <div className="mt-2 text-xs text-green-400 flex items-center gap-1">
                  <span>✓ 해제: {formatTime(event.resolvedAt)}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
}
