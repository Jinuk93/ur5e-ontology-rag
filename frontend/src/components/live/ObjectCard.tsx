'use client';

import { motion } from 'framer-motion';
import { Bot, Radio, BarChart3, AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';
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

const stateConfig: Record<NodeState, { color: string; label: string; icon: typeof CheckCircle }> = {
  normal: {
    color: 'text-green-400 bg-green-500/20 border-green-500/50',
    label: '정상',
    icon: CheckCircle,
  },
  warning: {
    color: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/50',
    label: '경고',
    icon: AlertCircle,
  },
  critical: {
    color: 'text-red-400 bg-red-500/20 border-red-500/50',
    label: '위험',
    icon: AlertTriangle,
  },
};

export function ObjectCard({ entity, isSelected, onClick }: ObjectCardProps) {
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
      deviation = `${ratio.toFixed(1)}배 초과`;
    } else if (value > max) {
      const ratio = Math.abs(value / max);
      deviation = `${ratio.toFixed(1)}배 초과`;
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
          'w-[200px] h-[150px] p-4 cursor-pointer transition-colors',
          'bg-slate-800/50 border-slate-700/50 hover:border-slate-600',
          isSelected && 'ring-2 ring-blue-500 border-blue-500/50'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-slate-700/50">
                <Icon className="h-4 w-4 text-slate-300" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-white">{entity.name}</h3>
                <p className="text-xs text-slate-400">{entity.type}</p>
              </div>
            </div>
          </div>

          {/* State Badge */}
          <div className="mt-2">
            <Badge
              variant="outline"
              className={cn('gap-1', stateInfo.color)}
            >
              <StateIcon className="h-3 w-3" />
              {stateInfo.label}
            </Badge>
          </div>

          {/* Value */}
          {hasValue && (
            <div className="mt-auto pt-2">
              <div className="flex items-baseline gap-1">
                <span className={cn(
                  'text-xl font-bold',
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
                <p className="text-xs text-slate-500">
                  정상: {entity.normalRange![0]} ~ {entity.normalRange![1]}
                </p>
              )}
              {deviation && (
                <p className="text-xs text-yellow-400">{deviation}</p>
              )}
            </div>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
