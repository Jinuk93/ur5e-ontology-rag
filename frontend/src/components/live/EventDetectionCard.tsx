'use client';

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Zap, AlertTriangle, AlertCircle, CheckCircle, Activity } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { cardHover, cardTap } from '@/lib/animations';
import { useEventResolveStore } from '@/stores/eventResolveStore';
import type { EventItem } from './EventList';

interface EventDetectionCardProps {
  events: EventItem[];
  onClick?: () => void;
}

// 이벤트 타입별 설정
const eventTypeConfig: Record<string, { label: string; color: string; icon: typeof AlertTriangle }> = {
  collision: { label: '충돌', color: 'text-red-400', icon: AlertTriangle },
  overload: { label: '과부하', color: 'text-orange-400', icon: AlertCircle },
  drift: { label: '드리프트', color: 'text-yellow-400', icon: Activity },
};

// 시스템 상태 설정 (이벤트 감지 시스템 작동 상태)
const systemStatusConfig = {
  normal: { label: '정상', color: 'text-green-400', bgColor: 'bg-green-500/20', borderColor: 'border-green-500/50' },
};

export function EventDetectionCard({ events, onClick }: EventDetectionCardProps) {
  const { resolvedEventIds } = useEventResolveStore();

  // 이벤트 분석 (해결되지 않은 이벤트만 카운트)
  const analysis = useMemo(() => {
    // 해결되지 않은 이벤트만 필터링
    const unresolvedEvents = events.filter((e) => !resolvedEventIds.has(e.id));

    const criticalEvents = unresolvedEvents.filter((e) => e.type === 'critical');
    const warningEvents = unresolvedEvents.filter((e) => e.type === 'warning');

    // 이벤트 타입별 개수
    const byType: Record<string, number> = {};
    unresolvedEvents.forEach((e) => {
      byType[e.eventType] = (byType[e.eventType] || 0) + 1;
    });

    return {
      total: unresolvedEvents.length,
      critical: criticalEvents.length,
      warning: warningEvents.length,
      byType,
      totalWithResolved: events.length,
      resolvedCount: events.length - unresolvedEvents.length,
    };
  }, [events, resolvedEventIds]);

  const statusInfo = systemStatusConfig.normal; // 항상 "정상" (시스템 작동 상태)
  const hasEvents = analysis.total > 0;

  return (
    <motion.div whileHover={cardHover} whileTap={cardTap}>
      <Card
        onClick={onClick}
        className={cn(
          'w-[260px] h-[165px] p-3.5 cursor-pointer transition-all duration-200',
          hasEvents
            ? 'bg-gradient-to-br from-red-900/30 via-red-800/20 to-slate-900/80'
            : 'bg-gradient-to-br from-slate-800/80 via-slate-800/60 to-slate-900/80',
          'border border-slate-700/50 hover:border-slate-500/70',
          'shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30',
          'backdrop-blur-sm',
          // 이벤트가 있으면 빨간색 테두리
          hasEvents && 'ring-1 ring-red-500/30 border-red-500/30'
        )}
        style={{
          boxShadow: hasEvents
            ? '0 8px 24px rgba(239, 68, 68, 0.15), inset 0 1px 0 rgba(255,255,255,0.05)'
            : '0 4px 16px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255,255,255,0.05)',
        }}
      >
        <div className="flex flex-col h-full relative">
          {/* Header */}
          <div className="flex items-start gap-3">
            <div
              className={cn(
                'p-2 rounded-lg shrink-0 bg-gradient-to-br',
                hasEvents ? 'from-red-600/30 to-red-700/30' : 'from-slate-600/50 to-slate-700/50'
              )}
              style={{
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.1), 0 2px 4px rgba(0,0,0,0.2)',
              }}
            >
              <Zap className={cn('h-5 w-5 drop-shadow-sm', hasEvents ? 'text-red-400' : 'text-slate-300')} />
            </div>
            <div className="min-w-0 flex-1 pr-2">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium text-white">이벤트 감지</h3>
                {/* 이벤트가 있으면 빨간색 점 표시 */}
                {hasEvents && (
                  <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5 leading-tight">충돌/과부하/드리프트 기록</p>
            </div>
          </div>

          {/* Content */}
          <div className="mt-auto pt-2">
            {hasEvents ? (
              <>
                {/* 이벤트 타입별 카운트 */}
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  {Object.entries(analysis.byType).map(([type, count]) => {
                    const config = eventTypeConfig[type] || { label: type, color: 'text-slate-400', icon: AlertCircle };
                    const Icon = config.icon;
                    return (
                      <div key={type} className="flex items-center gap-1">
                        <Icon className={cn('h-3.5 w-3.5', config.color)} />
                        <span className={cn('text-xs font-medium', config.color)}>
                          {config.label} {count}건
                        </span>
                      </div>
                    );
                  })}
                </div>
                {/* 총 이벤트 수 */}
                <p className="text-xs text-slate-500">
                  미해결 {analysis.total}건 (위험 {analysis.critical}, 경고 {analysis.warning})
                  {analysis.resolvedCount > 0 && (
                    <span className="text-green-500 ml-1">/ 해결 {analysis.resolvedCount}건</span>
                  )}
                </p>
              </>
            ) : (
              <>
                <div className="flex items-center gap-2 mb-1">
                  <CheckCircle className="h-5 w-5 text-green-400" />
                  <span className="text-xl font-bold text-green-400">정상</span>
                </div>
                <p className="text-xs text-slate-500">감지된 이벤트 없음</p>
              </>
            )}
          </div>

          {/* Status Badge - Bottom Right (항상 "정상" = 시스템 작동 중) */}
          <div className="absolute bottom-0 right-0">
            <Badge
              variant="outline"
              className={cn('gap-1', statusInfo.color, statusInfo.bgColor, statusInfo.borderColor)}
            >
              <CheckCircle className="h-3 w-3" />
              {statusInfo.label}
            </Badge>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
