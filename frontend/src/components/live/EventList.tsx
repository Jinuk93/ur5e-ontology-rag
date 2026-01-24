'use client';

import { useMemo } from 'react';
import { AlertTriangle, AlertCircle, Clock, Zap } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import type { RealtimePrediction } from '@/lib/api';

export interface EventItem {
  id: string;
  timestamp: string;
  type: 'critical' | 'warning' | 'info';
  eventType: string;
  message: string;
  errorCode?: string;
  entityId?: string;
  context?: {
    fzPeakN?: number;
    fzValueN?: number;
    shift?: string;
    product?: string;
  };
}

interface EventListProps {
  events: EventItem[];
  predictions?: RealtimePrediction[];
  onEventClick?: (event: EventItem) => void;
  maxHeight?: string;
}

const eventConfig = {
  critical: {
    icon: AlertTriangle,
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    label: '위험',
    labelEn: 'Critical',
  },
  warning: {
    icon: AlertCircle,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10',
    label: '경고',
    labelEn: 'Warning',
  },
  info: {
    icon: AlertCircle,
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
    label: '정상',
    labelEn: 'Normal',
  },
};

export function EventList({ events, predictions, onEventClick, maxHeight = '200px' }: EventListProps) {
  const t = useTranslations('card');

  // Sort events by timestamp descending (most recent first)
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [events]);

  // 이벤트와 매칭되는 온톨로지 예측 찾기
  const findMatchingPrediction = (event: EventItem): RealtimePrediction | undefined => {
    if (!predictions || predictions.length === 0) return undefined;

    // 이벤트 타입을 패턴 ID로 변환
    const patternMap: Record<string, string> = {
      'collision': 'PAT_COLLISION',
      'overload': 'PAT_OVERLOAD',
      'drift': 'PAT_DRIFT',
    };
    const expectedPattern = patternMap[event.eventType];

    // 1. 에러코드로 매칭
    if (event.errorCode) {
      const matchByError = predictions.find(p =>
        p.predictions.some(pred => pred.error_code === event.errorCode)
      );
      if (matchByError) return matchByError;
    }

    // 2. 패턴 타입으로 매칭
    if (expectedPattern) {
      const matchByPattern = predictions.find(p =>
        p.pattern_detected === expectedPattern
      );
      if (matchByPattern) return matchByPattern;
    }

    return undefined;
  };

  const formatDateTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return {
      date: date.toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }),
      time: date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
    };
  };

  const getEventTypeLabel = (eventType: string) => {
    switch (eventType) {
      case 'collision': return '충돌';
      case 'overload': return '과부하';
      default: return eventType;
    }
  };

  const getAction = (event: EventItem) => {
    if (event.errorCode) return 'Safety Stop';
    if (event.eventType === 'overload') return '모니터링';
    return '-';
  };

  // 온톨로지 기반 AI 예측 (API 데이터 우선 사용)
  const getEventPrediction = (event: EventItem): { text: string; fromOntology: boolean; probability?: number } => {
    // 온톨로지 예측 데이터가 있으면 우선 사용
    const matchedPrediction = findMatchingPrediction(event);
    if (matchedPrediction && matchedPrediction.predictions.length > 0) {
      const pred = matchedPrediction.predictions[0];
      const prob = pred.probability;

      // 온톨로지 경로 기반 예측 메시지 생성
      let message = pred.recommendation || '';
      if (!message && pred.cause) {
        // cause 기반 메시지
        const causeMessages: Record<string, string> = {
          'CAUSE_COLLISION': '충돌 원인 분석 완료',
          'CAUSE_OVERLOAD': '과부하 원인 감지',
          'CAUSE_DRIFT': '센서 드리프트 감지',
        };
        message = causeMessages[pred.cause] || `${pred.error_code} 예측`;
      }
      if (!message) {
        message = prob > 0.8 ? '즉시 점검 필요' : prob > 0.5 ? '주의 관찰' : '모니터링';
      }

      return { text: message, fromOntology: true, probability: prob };
    }

    // Fallback: 기존 하드코딩 로직
    let fallbackText = '모니터링 중';
    if (event.eventType === 'collision') {
      if (event.errorCode === 'C153') {
        fallbackText = '재발 가능성 높음';
      } else if (event.context?.fzPeakN && event.context.fzPeakN > 500) {
        fallbackText = '그리퍼 점검 필요';
      } else {
        fallbackText = '작업 경로 검토';
      }
    } else if (event.eventType === 'overload') {
      if (event.errorCode) {
        fallbackText = '부품 마모 주의';
      } else if (event.context?.fzValueN && event.context.fzValueN > 200) {
        fallbackText = '축 부하 증가 추세';
      } else {
        fallbackText = '하중 분산 검토';
      }
    } else if (event.eventType === 'drift' || event.eventType?.includes('drift')) {
      fallbackText = '센서 교정 필요';
    } else if (event.errorCode) {
      const errorPredictions: Record<string, string> = {
        C153: '동일 위치 재발 주의',
        C154: '보호 영역 침범 주의',
        C155: '긴급 점검 필요',
        C189: '과전류 재발 가능',
        C200: '충돌 패턴 분석 필요',
        C201: '부하 한계 초과 주의',
      };
      fallbackText = errorPredictions[event.errorCode] || '패턴 분석 중';
    } else if (event.context?.fzPeakN && event.context.fzPeakN > 800) {
      fallbackText = '충돌 위험 증가';
    } else if (event.context?.fzValueN && event.context.fzValueN > 300) {
      fallbackText = '과부하 주의';
    }

    return { text: fallbackText, fromOntology: false };
  };

  const getErrorCodeInfo = (event: EventItem) => {
    if (!event.errorCode) return null;
    // Map error codes to Korean descriptions
    const errorDescriptions: Record<string, string> = {
      C153: '안전 정지',
      C154: '보호 정지',
      C155: '비상 정지',
      C200: '충돌 감지',
      C201: '과부하 감지',
    };
    return {
      code: event.errorCode,
      description: errorDescriptions[event.errorCode] || '알 수 없는 에러',
    };
  };

  return (
    <div
      className="rounded-lg border border-slate-700/50 bg-gradient-to-br from-slate-800/50 via-slate-800/30 to-slate-900/50 backdrop-blur-sm"
      style={{
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.03)',
      }}
    >
      <div className="px-3 py-2 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-medium text-white">최근 이벤트</h3>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          센서에서 감지된 이상 패턴 기록입니다. 클릭하면 상세 분석을 볼 수 있습니다.
        </p>
        <p className="text-xs text-red-400 mt-1">
          AI가 UR5e 에러코드와 Axia80 센서 이벤트의 상관관계를 분석하여 예측 및 조치를 제안합니다.
        </p>
      </div>

      <ScrollArea style={{ height: maxHeight }}>
        {events.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">
            이벤트가 없습니다
          </p>
        ) : (
          <table className="w-full text-xs table-fixed">
          <colgroup>
            <col className="w-[14%]" />
            <col className="w-[12%]" />
            <col className="w-[18%]" />
            <col className="w-[18%]" />
            <col className="w-[18%]" />
            <col className="w-[20%]" />
          </colgroup>
          <thead className="sticky top-0 bg-slate-800/95 z-10">
            <tr className="border-b border-slate-700/50">
              <th className="text-center py-2 px-2 text-slate-400 font-semibold">시간</th>
              <th className="text-center py-2 px-2 text-slate-400 font-semibold">상태</th>
              <th className="text-center py-2 px-2 text-slate-400 font-semibold">감지 이벤트</th>
              <th className="text-center py-2 px-2 text-slate-400 font-semibold">에러코드</th>
              <th className="text-center py-2 px-2 text-slate-400 font-semibold">조치</th>
              <th className="text-center py-2 px-2 text-blue-300 font-semibold bg-blue-950/50">AI 예측</th>
            </tr>
          </thead>
          <tbody>
            {sortedEvents.map((event) => {
              const config = eventConfig[event.type];
              const Icon = config.icon;
              const { date, time } = formatDateTime(event.timestamp);

              return (
                <tr
                  key={event.id}
                  onClick={() => onEventClick?.(event)}
                  className={cn(
                    'border-b border-slate-700/30 cursor-pointer transition-colors',
                    'hover:bg-slate-700/30'
                  )}
                >
                  <td className="py-2 px-2 text-slate-300 whitespace-nowrap text-center font-semibold">
                    <div>{date}</div>
                    <div className="text-slate-400 font-medium">{time}</div>
                  </td>
                  <td className="py-2 px-2 text-center">
                    <span className={cn(
                      'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-semibold',
                      config.bgColor,
                      config.color
                    )}>
                      <Icon className="h-3 w-3" />
                      {t(event.type === 'critical' ? 'critical' : event.type === 'warning' ? 'warning' : 'normal')}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-slate-300 text-center font-semibold">
                    {getEventTypeLabel(event.eventType)}
                  </td>
                  <td className="py-2 px-2 text-center font-semibold">
                    {(() => {
                      const errorInfo = getErrorCodeInfo(event);
                      if (!errorInfo) return <span className="text-slate-400">-</span>;
                      return (
                        <div>
                          <div className="text-red-400 font-bold">{errorInfo.code}</div>
                          <div className="text-[10px] text-slate-400 font-medium">{errorInfo.description}</div>
                        </div>
                      );
                    })()}
                  </td>
                  <td className="py-2 px-2 text-slate-300 text-center font-semibold">
                    {getAction(event)}
                  </td>
                  <td className="py-2 px-2 text-center font-semibold bg-blue-950/40">
                    {(() => {
                      const prediction = getEventPrediction(event);
                      return (
                        <div className="flex flex-col items-center gap-0.5">
                          <span className={cn(
                            'inline-flex items-center gap-1',
                            prediction.fromOntology ? 'text-cyan-300' : 'text-blue-300'
                          )}>
                            <Zap className={cn(
                              'h-3 w-3',
                              prediction.fromOntology ? 'text-cyan-400' : 'text-yellow-400'
                            )} />
                            {prediction.text}
                          </span>
                          {prediction.fromOntology && prediction.probability !== undefined && (
                            <span className="text-[9px] text-cyan-500">
                              온톨로지 ({Math.round(prediction.probability * 100)}%)
                            </span>
                          )}
                        </div>
                      );
                    })()}
                  </td>
                </tr>
              );
            })}
          </tbody>
          </table>
        )}
      </ScrollArea>
    </div>
  );
}
