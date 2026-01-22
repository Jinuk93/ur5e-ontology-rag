'use client';

import { AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { RiskAlert } from '@/types/api';
import { cn } from '@/lib/utils';

interface RiskAlertBarProps {
  alerts: RiskAlert[];
  onAlertClick?: (alert: RiskAlert) => void;
}

const severityConfig = {
  critical: {
    icon: AlertTriangle,
    bgClass: 'bg-red-500/20 border-red-500/50 hover:bg-red-500/30',
    textClass: 'text-red-400',
    badgeVariant: 'destructive' as const,
  },
  warning: {
    icon: AlertCircle,
    bgClass: 'bg-yellow-500/20 border-yellow-500/50 hover:bg-yellow-500/30',
    textClass: 'text-yellow-400',
    badgeVariant: 'secondary' as const,
  },
  info: {
    icon: CheckCircle,
    bgClass: 'bg-green-500/20 border-green-500/50 hover:bg-green-500/30',
    textClass: 'text-green-400',
    badgeVariant: 'outline' as const,
  },
};

export function RiskAlertBar({ alerts, onAlertClick }: RiskAlertBarProps) {
  // Group alerts by severity
  const criticalAlerts = alerts.filter((a) => a.severity === 'critical');
  const warningAlerts = alerts.filter((a) => a.severity === 'warning');
  const infoAlerts = alerts.filter((a) => a.severity === 'info');

  const summaryItems = [
    { severity: 'critical' as const, alerts: criticalAlerts, label: '긴급' },
    { severity: 'warning' as const, alerts: warningAlerts, label: '경고' },
    { severity: 'info' as const, alerts: infoAlerts, label: '정상' },
  ];

  return (
    <div className="flex items-center gap-2 p-3 bg-slate-800/50 border-b border-white/10">
      {summaryItems.map(({ severity, alerts: severityAlerts, label }) => {
        const config = severityConfig[severity];
        const Icon = config.icon;
        const count = severityAlerts.reduce((sum, a) => sum + (a.count || 1), 0);
        const latestAlert = severityAlerts[0];

        return (
          <button
            key={severity}
            onClick={() => latestAlert && onAlertClick?.(latestAlert)}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors',
              config.bgClass,
              !latestAlert && 'opacity-50 cursor-default'
            )}
            disabled={!latestAlert}
          >
            <Icon className={cn('h-4 w-4', config.textClass)} />
            <span className={cn('text-sm font-medium', config.textClass)}>
              {label}
            </span>
            <Badge variant={config.badgeVariant} className="text-xs">
              {count}
            </Badge>
            {latestAlert && (
              <span className="text-xs text-slate-400 hidden sm:inline">
                {latestAlert.title}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
