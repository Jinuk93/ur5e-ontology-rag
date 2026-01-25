'use client';

import { motion } from 'framer-motion';
import { Bot, Radio, BarChart3, AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { EntityInfo, EntityType, NodeState } from '@/types/api';
import { cn } from '@/lib/utils';
import { cardHover, cardTap } from '@/lib/animations';

interface ObjectCardProps {
  entity: EntityInfo;
  isSelected?: boolean;
  onClick?: () => void;
}

const entityIcons: Record<EntityType, typeof Bot> = {
  ROBOT: Bot,
  SENSOR: Radio,
  MEASUREMENT_AXIS: BarChart3,
  STATE: AlertCircle,
  PATTERN: AlertTriangle,
  ERROR_CODE: AlertTriangle,
  CAUSE: AlertCircle,
  RESOLUTION: CheckCircle,
};

const stateConfig: Record<NodeState, { color: string; labelKey: string; icon: typeof CheckCircle }> = {
  normal: {
    color: 'text-green-400 bg-green-500/20 border-green-500/50',
    labelKey: 'normal',
    icon: CheckCircle,
  },
  warning: {
    color: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/50',
    labelKey: 'warning',
    icon: AlertCircle,
  },
  critical: {
    color: 'text-red-400 bg-red-500/20 border-red-500/50',
    labelKey: 'critical',
    icon: AlertTriangle,
  },
};

export function ObjectCard({ entity, isSelected, onClick }: ObjectCardProps) {
  const t = useTranslations('card');
  const Icon = entityIcons[entity.type] || BarChart3;
  const stateInfo = stateConfig[entity.state];
  const StateIcon = stateInfo.icon;

  const hasValue = entity.currentValue !== undefined;
  const hasRange = entity.normalRange !== undefined;

  // Calculate deviation if we have value and range
  let deviation: string | null = null;
  if (hasValue && hasRange) {
    const [min, max] = entity.normalRange!;
    const value = entity.currentValue!;
    if (value < min) {
      const ratio = Math.abs(value / min);
      deviation = `${ratio.toFixed(1)}x ${t('exceeded')}`;
    } else if (value > max) {
      const ratio = Math.abs(value / max);
      deviation = `${ratio.toFixed(1)}x ${t('exceeded')}`;
    }
  }

  return (
    <motion.div
      whileHover={cardHover}
      whileTap={cardTap}
    >
      <Card
        onClick={onClick}
        className={cn(
          'w-[260px] h-[165px] p-3.5 cursor-pointer transition-all duration-300',
          // 상태별 테두리
          entity.state === 'critical' && 'ring-1 ring-red-500/30 border-red-500/30',
          entity.state === 'warning' && 'ring-1 ring-yellow-500/30 border-yellow-500/30',
          'border border-slate-700/50 hover:border-slate-500/70',
          isSelected && 'ring-2 ring-blue-500 border-blue-500/50'
        )}
        style={{
          // 상태별 그라데이션 배경 (실시간 변경)
          background: entity.state === 'critical'
            ? 'linear-gradient(135deg, rgba(153, 27, 27, 0.95) 0%, rgba(127, 29, 29, 0.9) 50%, rgba(69, 10, 10, 0.95) 100%)'
            : entity.state === 'warning'
            ? 'linear-gradient(135deg, rgba(146, 64, 14, 0.95) 0%, rgba(113, 63, 18, 0.9) 50%, rgba(69, 26, 3, 0.95) 100%)'
            : 'linear-gradient(135deg, rgba(51, 65, 85, 0.95) 0%, rgba(30, 41, 59, 0.9) 50%, rgba(15, 23, 42, 0.95) 100%)',
          boxShadow: isSelected
            ? '0 4px 12px rgba(59, 130, 246, 0.15), 0 2px 4px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.08)'
            : entity.state === 'critical'
            ? '0 4px 12px rgba(239, 68, 68, 0.2), inset 0 1px 0 rgba(255,255,255,0.06)'
            : entity.state === 'warning'
            ? '0 4px 12px rgba(234, 179, 8, 0.2), inset 0 1px 0 rgba(255,255,255,0.06)'
            : '0 4px 12px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.06)',
        }}
      >
        <div className="flex flex-col h-full relative">
          {/* Header */}
          <div className="flex items-start gap-3">
            <div
              className={cn(
                'p-2 rounded-lg shrink-0 bg-gradient-to-br',
                entity.state === 'critical' ? 'from-red-600/30 to-red-700/30' :
                entity.state === 'warning' ? 'from-yellow-600/30 to-yellow-700/30' :
                'from-slate-600/50 to-slate-700/50'
              )}
              style={{
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.05), 0 1px 2px rgba(0,0,0,0.1)',
              }}
            >
              <Icon className={cn(
                'h-5 w-5 drop-shadow-sm',
                entity.state === 'critical' ? 'text-red-400' :
                entity.state === 'warning' ? 'text-yellow-400' :
                'text-slate-300'
              )} />
            </div>
            <div className="min-w-0 flex-1 pr-2">
              <h3 className="text-sm font-medium text-white">{entity.name}</h3>
              <p className="text-xs text-slate-400 mt-0.5 leading-tight">{entity.description || entity.type}</p>
              {entity.detail && (
                <p className="text-xs text-slate-500 leading-tight">({entity.detail})</p>
              )}
            </div>
          </div>

          {/* Value */}
          {hasValue && (
            <div className="mt-auto pt-2">
              <div className="flex items-baseline gap-1">
                <span className={cn(
                  'text-2xl font-bold',
                  entity.state === 'critical' && 'text-red-400',
                  entity.state === 'warning' && 'text-yellow-400',
                  entity.state === 'normal' && 'text-green-400'
                )}>
                  {entity.currentValue}
                </span>
                {entity.unit && (
                  <span className="text-sm text-slate-400">{entity.unit}</span>
                )}
              </div>
              {hasRange && (
                <p className="text-xs text-slate-500 mt-0.5">
                  {t('normalRange')}: {entity.normalRange![0]} ~ {entity.normalRange![1]}
                </p>
              )}
              {deviation && (
                <p className="text-xs text-yellow-400">{deviation}</p>
              )}
            </div>
          )}

          {/* State Badge - Bottom Right */}
          <div className="absolute bottom-0 right-0">
            <Badge
              variant="outline"
              className={cn('gap-1', stateInfo.color)}
            >
              <StateIcon className="h-3 w-3" />
              {t(stateInfo.labelKey)}
            </Badge>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
