'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslations } from 'next-intl';
import type { RiskAlert } from '@/types/api';
import { cn } from '@/lib/utils';
import { staggerContainer, staggerItem } from '@/lib/animations';

interface RiskAlertBarProps {
  alerts: RiskAlert[];
  onAlertClick?: (alert: RiskAlert) => void;
  entityNames?: string[];
}

const severityConfig = {
  critical: {
    dotColor: 'bg-red-500',
    glowColor: 'shadow-red-500/50',
    textColor: 'text-slate-300',
  },
  warning: {
    dotColor: 'bg-yellow-500',
    glowColor: 'shadow-yellow-500/50',
    textColor: 'text-slate-300',
  },
  info: {
    dotColor: 'bg-green-500',
    glowColor: 'shadow-green-500/50',
    textColor: 'text-slate-300',
  },
};

export function RiskAlertBar({ alerts, onAlertClick, entityNames = [] }: RiskAlertBarProps) {
  const t = useTranslations('alert');
  const [hoveredSeverity, setHoveredSeverity] = useState<string | null>(null);

  // Group alerts by severity
  const criticalAlerts = alerts.filter((a) => a.severity === 'critical');
  const warningAlerts = alerts.filter((a) => a.severity === 'warning');
  const infoAlerts = alerts.filter((a) => a.severity === 'info');

  const summaryItems = [
    { severity: 'critical' as const, alerts: criticalAlerts, labelKey: 'critical' },
    { severity: 'warning' as const, alerts: warningAlerts, labelKey: 'warning' },
    { severity: 'info' as const, alerts: infoAlerts, labelKey: 'normal' },
  ];

  return (
    <motion.div
      className="flex items-center gap-4 px-4 py-2 border-b border-white/5 bg-gradient-to-r from-slate-800/40 via-slate-800/30 to-slate-800/40"
      style={{
        boxShadow: 'inset 0 -1px 0 rgba(255,255,255,0.02), 0 1px 3px rgba(0,0,0,0.1)',
      }}
      initial="hidden"
      animate="visible"
      variants={staggerContainer}
    >
      {summaryItems.map(({ severity, alerts: severityAlerts, labelKey }) => {
        const config = severityConfig[severity];
        const count = severityAlerts.reduce((sum, a) => sum + (a.count || 1), 0);
        const latestAlert = severityAlerts[0];
        const isHovered = hoveredSeverity === severity;

        return (
          <motion.div
            key={severity}
            variants={staggerItem}
            className="relative"
            onMouseEnter={() => setHoveredSeverity(severity)}
            onMouseLeave={() => setHoveredSeverity(null)}
          >
            <button
              onClick={() => latestAlert && onAlertClick?.(latestAlert)}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors',
                'hover:bg-slate-700/50',
                !latestAlert && 'opacity-50 cursor-default'
              )}
              disabled={!latestAlert}
            >
              {/* Traffic light dot */}
              <div
                className={cn(
                  'w-3 h-3 rounded-full shadow-md',
                  config.dotColor,
                  count > 0 && config.glowColor
                )}
              />
              <span className={cn('text-sm', config.textColor)}>
                {t(labelKey)}
              </span>
              <span className="text-sm font-medium text-white">
                {count}
              </span>
            </button>

            {/* Hover tooltip - entity list */}
            <AnimatePresence>
              {isHovered && count > 0 && entityNames.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.15 }}
                  className="absolute top-full left-0 mt-1 z-50 min-w-[140px]"
                >
                  <div className="bg-slate-800 border border-slate-600 rounded-lg shadow-xl py-2 px-3">
                    <div className="space-y-1">
                      {entityNames.map((name, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-2 text-sm text-slate-300"
                        >
                          <div className={cn('w-1.5 h-1.5 rounded-full', config.dotColor)} />
                          {name}
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}
    </motion.div>
  );
}
