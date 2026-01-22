'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { cn } from '@/lib/utils';
import type { NodeState } from '@/types/api';

export interface OntologyNodeData {
  label: string;
  type: string;
  state?: NodeState;
}

const typeStyles: Record<string, { bg: string; border: string; text: string }> = {
  MEASUREMENT_AXIS: { bg: 'bg-blue-500/20', border: 'border-blue-500', text: 'text-blue-400' },
  STATE: { bg: 'bg-emerald-500/20', border: 'border-emerald-500', text: 'text-emerald-400' },
  PATTERN: { bg: 'bg-purple-500/20', border: 'border-purple-500', text: 'text-purple-400' },
  ERROR_CODE: { bg: 'bg-orange-500/20', border: 'border-orange-500', text: 'text-orange-400' },
  CAUSE: { bg: 'bg-pink-500/20', border: 'border-pink-500', text: 'text-pink-400' },
  RESOLUTION: { bg: 'bg-cyan-500/20', border: 'border-cyan-500', text: 'text-cyan-400' },
  ROBOT: { bg: 'bg-slate-500/20', border: 'border-slate-500', text: 'text-slate-400' },
  SENSOR: { bg: 'bg-teal-500/20', border: 'border-teal-500', text: 'text-teal-400' },
};

const stateColors: Record<NodeState, string> = {
  normal: 'ring-green-500',
  warning: 'ring-yellow-500',
  critical: 'ring-red-500',
};

function OntologyNodeComponent({ data, selected }: NodeProps<{ data: OntologyNodeData }>) {
  const nodeData = data as unknown as OntologyNodeData;
  const style = typeStyles[nodeData.type] || typeStyles.MEASUREMENT_AXIS;
  const stateRing = nodeData.state ? stateColors[nodeData.state] : '';

  return (
    <div
      className={cn(
        'px-4 py-2 rounded-lg border-2 min-w-[120px] text-center',
        style.bg,
        style.border,
        selected && 'ring-2 ring-offset-2 ring-offset-slate-900 ring-blue-500',
        nodeData.state && `ring-2 ${stateRing}`
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-slate-500 !w-2 !h-2"
      />

      <div className={cn('text-sm font-medium', style.text)}>
        {nodeData.label}
      </div>
      <div className="text-xs text-slate-500">{nodeData.type}</div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-500 !w-2 !h-2"
      />
    </div>
  );
}

export const OntologyNode = memo(OntologyNodeComponent);
