'use client';

import { AlertTriangle, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

export interface EventItem {
  id: string;
  timestamp: string;
  type: 'critical' | 'warning' | 'info';
  message: string;
  entityId?: string;
}

interface EventListProps {
  events: EventItem[];
  onEventClick?: (event: EventItem) => void;
  maxHeight?: string;
}

const eventConfig = {
  critical: {
    icon: AlertTriangle,
    color: 'text-red-400',
    bgColor: 'hover:bg-red-500/10',
  },
  warning: {
    icon: AlertCircle,
    color: 'text-yellow-400',
    bgColor: 'hover:bg-yellow-500/10',
  },
  info: {
    icon: CheckCircle,
    color: 'text-green-400',
    bgColor: 'hover:bg-green-500/10',
  },
};

export function EventList({ events, onEventClick, maxHeight = '200px' }: EventListProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="bg-slate-800/30 rounded-lg border border-slate-700/50">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700/50">
        <Clock className="h-4 w-4 text-slate-400" />
        <h3 className="text-sm font-medium text-white">최근 이벤트</h3>
      </div>

      <ScrollArea style={{ height: maxHeight }}>
        <div className="p-2 space-y-1">
          {events.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-4">
              이벤트가 없습니다
            </p>
          ) : (
            events.map((event) => {
              const config = eventConfig[event.type];
              const Icon = config.icon;

              return (
                <button
                  key={event.id}
                  onClick={() => onEventClick?.(event)}
                  className={cn(
                    'w-full flex items-start gap-2 px-2 py-1.5 rounded-md text-left transition-colors',
                    config.bgColor
                  )}
                >
                  <Icon className={cn('h-4 w-4 mt-0.5 flex-shrink-0', config.color)} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200 truncate">
                      {event.message}
                    </p>
                    <p className="text-xs text-slate-500">
                      {formatTime(event.timestamp)}
                    </p>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
