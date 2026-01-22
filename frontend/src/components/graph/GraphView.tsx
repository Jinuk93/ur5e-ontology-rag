'use client';

import { useState } from 'react';
import { SubGraph } from './SubGraph';
import { PathBreadcrumb } from './PathBreadcrumb';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useUIStore } from '@/stores/uiStore';
import type { GraphNode, GraphEdge } from '@/types/api';

// Mock ontology graph data
const mockNodes: GraphNode[] = [
  { id: 'Fz', type: 'MEASUREMENT_AXIS', label: 'Fz (-180N)', state: 'warning' },
  { id: 'State_Warning', type: 'STATE', label: 'State_Warning', state: 'warning' },
  { id: 'PAT_COLLISION', type: 'PATTERN', label: 'PAT_COLLISION' },
  { id: 'PAT_OVERLOAD', type: 'PATTERN', label: 'PAT_OVERLOAD' },
  { id: 'C153', type: 'ERROR_CODE', label: 'C153' },
  { id: 'CAUSE_COLLISION', type: 'CAUSE', label: 'CAUSE_COLLISION' },
  { id: 'RES_CHECK_OBSTACLE', type: 'RESOLUTION', label: 'RES_CHECK_OBSTACLE' },
];

const mockEdges: GraphEdge[] = [
  { source: 'Fz', target: 'State_Warning', relation: 'HAS_STATE' },
  { source: 'State_Warning', target: 'PAT_COLLISION', relation: 'INDICATES' },
  { source: 'State_Warning', target: 'PAT_OVERLOAD', relation: 'INDICATES' },
  { source: 'PAT_COLLISION', target: 'C153', relation: 'TRIGGERS' },
  { source: 'C153', target: 'CAUSE_COLLISION', relation: 'CAUSED_BY' },
  { source: 'CAUSE_COLLISION', target: 'RES_CHECK_OBSTACLE', relation: 'RESOLVED_BY' },
];

interface NodeDetailInfo {
  id: string;
  type: string;
  label: string;
  description?: string;
  severity?: string;
  documentRef?: string;
}

const nodeDetails: Record<string, NodeDetailInfo> = {
  Fz: {
    id: 'Fz',
    type: 'MEASUREMENT_AXIS',
    label: 'Force Z',
    description: 'Z축 방향 힘 측정값. 현재 -180N으로 경고 범위(-200 ~ -60N) 내에 있음.',
  },
  State_Warning: {
    id: 'State_Warning',
    type: 'STATE',
    label: 'Warning State',
    description: '경고 상태. 정상 범위를 벗어났으나 위험 수준은 아님.',
  },
  PAT_COLLISION: {
    id: 'PAT_COLLISION',
    type: 'PATTERN',
    label: 'Collision Pattern',
    description: '충돌 패턴이 감지됨. 급격한 힘 변화가 특징.',
  },
  C153: {
    id: 'C153',
    type: 'ERROR_CODE',
    label: 'C153 - Collision Detected',
    description: '로봇이 예상치 못한 외부 힘을 감지했습니다.',
    severity: 'High',
    documentRef: 'service_manual p.45',
  },
  CAUSE_COLLISION: {
    id: 'CAUSE_COLLISION',
    type: 'CAUSE',
    label: 'Collision Cause',
    description: '외부 물체와의 충돌 또는 작업 영역 내 장애물.',
  },
  RES_CHECK_OBSTACLE: {
    id: 'RES_CHECK_OBSTACLE',
    type: 'RESOLUTION',
    label: 'Check Obstacle',
    description: '작업 영역의 장애물을 확인하고 제거하세요.',
  },
};

export function GraphView() {
  const { graphCenterNode, setGraphCenterNode } = useUIStore();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Current path (simplified for demo)
  const currentPath = ['Fz', 'State_Warning', 'PAT_COLLISION', 'C153'];
  const pathRelations = ['HAS_STATE', 'INDICATES', 'TRIGGERS'];

  const handleNodeClick = (nodeId: string) => {
    setSelectedNodeId(nodeId);
    setGraphCenterNode(nodeId);
  };

  const selectedNode = selectedNodeId ? nodeDetails[selectedNodeId] : null;

  return (
    <div className="flex flex-col h-full">
      {/* Breadcrumb */}
      <div className="p-3 border-b border-slate-700/50 bg-slate-800/30">
        <PathBreadcrumb
          path={currentPath}
          relations={pathRelations}
          onNodeClick={handleNodeClick}
        />
      </div>

      {/* Graph Area */}
      <div className="flex-1 p-4">
        <SubGraph
          nodes={mockNodes}
          edges={mockEdges}
          centerNodeId={graphCenterNode || 'Fz'}
          onNodeClick={handleNodeClick}
          onNodeHover={setHoveredNodeId}
        />
      </div>

      {/* Node Detail Panel */}
      {selectedNode && (
        <div className="p-4 border-t border-slate-700/50 bg-slate-800/30">
          <Card className="p-4 bg-slate-800/50 border-slate-700/50">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="text-lg font-medium text-white">{selectedNode.label}</h3>
                <Badge variant="outline" className="mt-1 text-slate-400 border-slate-600">
                  {selectedNode.type}
                </Badge>
              </div>
              {selectedNode.severity && (
                <Badge variant="destructive">{selectedNode.severity}</Badge>
              )}
            </div>

            {selectedNode.description && (
              <p className="text-sm text-slate-300 mt-2">{selectedNode.description}</p>
            )}

            {selectedNode.documentRef && (
              <p className="text-xs text-slate-500 mt-2">
                📄 Reference: {selectedNode.documentRef}
              </p>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
