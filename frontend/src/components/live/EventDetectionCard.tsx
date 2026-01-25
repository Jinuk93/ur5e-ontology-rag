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

// 이벤트 상태 설정 (미해결 이벤트 기반)
const eventStatusConfig = {
  critical: { label: '위험', color: 'text-red-400', bgColor: 'bg-red-500/20', borderColor: 'border-red-500/50', icon: AlertTriangle },
  warning: { label: '경고', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', borderColor: 'border-yellow-500/50', icon: AlertCircle },
  normal: { label: '정상', color: 'text-green-400', bgColor: 'bg-green-500/20', borderColor: 'border-green-500/50', icon: CheckCircle },
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

  // 미해결 이벤트 기반으로 상태 결정
  const cardStatus = analysis.critical > 0 ? 'critical' : analysis.warning > 0 ? 'warning' : 'normal';
  const statusInfo = eventStatusConfig[cardStatus];
  const StatusIcon = statusInfo.icon;
  const hasEvents = analysis.total > 0;

  return (
    <motion.div whileHover={cardHover} whileTap={cardTap}>
      <Card
        onClick={onClick}
        className={cn(
          'w-[260px] h-[165px] p-3.5 cursor-pointer transition-all duration-200',
          // 상태별 테두리
          cardStatus === 'critical' && 'ring-1 ring-red-500/30 border-red-500/30',
          cardStatus === 'warning' && 'ring-1 ring-yellow-500/30 border-yellow-500/30',
          'border border-slate-700/50 hover:border-slate-500/70'
        )}
        style={{
          // 그라데이션 없는 단색 배경 (경고/위험은 투명도 높임)
          backgroundColor: cardStatus === 'critical'
            ? 'rgba(127, 29, 29, 0.35)'  // 진한 빨간색 (투명도 증가)
            : cardStatus === 'warning'
            ? 'rgba(113, 63, 18, 0.35)'  // 진한 노란색/주황색 (투명도 증가)
            : 'rgba(30, 41, 59, 0.9)',  // 슬레이트
          boxShadow: cardStatus === 'critical'
            ? '0 2px 6px rgba(239, 68, 68, 0.15), inset 0 1px 0 rgba(255,255,255,0.04)'
            : cardStatus === 'warning'
            ? '0 2px 6px rgba(234, 179, 8, 0.15), inset 0 1px 0 rgba(255,255,255,0.04)'
            : '0 2px 6px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.04)',
        }}
      >
        <div className="flex flex-col h-full relative">
          {/* Header */}
          <div className="flex items-start gap-3">
            <div
              className={cn(
                'p-2 rounded-lg shrink-0 bg-gradient-to-br',
                cardStatus === 'critical' ? 'from-red-600/30 to-red-700/30' :
                cardStatus === 'warning' ? 'from-yellow-600/30 to-yellow-700/30' :
                'from-slate-600/50 to-slate-700/50'
              )}
              style={{
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.05), 0 1px 2px rgba(0,0,0,0.1)',
              }}
            >
              <Zap className={cn(
                'h-5 w-5 drop-shadow-sm',
                cardStatus === 'critical' ? 'text-red-400' :
                cardStatus === 'warning' ? 'text-yellow-400' :
                'text-slate-300'
              )} />
            </div>
            <div className="min-w-0 flex-1 pr-2">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium text-white">이벤트 감지</h3>
                {/* 상태에 따른 점 색상: 위험=빨간색, 경고=노란색 */}
                {cardStatus === 'critical' && (
                  <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                )}
                {cardStatus === 'warning' && (
                  <span className="inline-block w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
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
                {/* 총 이벤트 수 - 배지와 겹치지 않도록 pr-16 추가 */}
                <div className="pr-16">
                  <p className="text-xs text-slate-500">
                    미해결 {analysis.total}건 (위험 {analysis.critical}, 경고 {analysis.warning})
                  </p>
                  {analysis.resolvedCount > 0 && (
                    <p className="text-xs text-green-500 mt-0.5">해결 {analysis.resolvedCount}건</p>
                  )}
                </div>
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

          {/* Status Badge - Bottom Right (이벤트 상태에 따라 동적으로 변경) */}
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
    </motion.div>
  );
}
