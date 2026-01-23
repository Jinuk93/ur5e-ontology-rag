'use client';

import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  ConnectionMode,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { OntologyNode, OntologyNodeData } from './OntologyNode';
import type { GraphNode, GraphEdge } from '@/types/api';

interface SubGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  centerNodeId?: string;
  onNodeClick?: (nodeId: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
}

const nodeTypes = {
  ontology: OntologyNode,
};

// Layout algorithm - simple hierarchical
function layoutNodes(nodes: GraphNode[], edges: GraphEdge[], centerId?: string): Node<OntologyNodeData>[] {
  // Build adjacency lists
  const children: Map<string, string[]> = new Map();
  const parents: Map<string, string[]> = new Map();

  edges.forEach((edge) => {
    if (!children.has(edge.source)) children.set(edge.source, []);
    children.get(edge.source)!.push(edge.target);

    if (!parents.has(edge.target)) parents.set(edge.target, []);
    parents.get(edge.target)!.push(edge.source);
  });

  // Find root nodes (no parents) or use center node
  const roots = centerId
    ? [centerId]
    : nodes.filter((n) => !parents.has(n.id) || parents.get(n.id)!.length === 0).map((n) => n.id);

  // BFS to assign levels
  const levels: Map<string, number> = new Map();
  const queue: string[] = [...roots];
  roots.forEach((r) => levels.set(r, 0));

  while (queue.length > 0) {
    const current = queue.shift()!;
    const currentLevel = levels.get(current)!;
    const nodeChildren = children.get(current) || [];

    nodeChildren.forEach((child) => {
      if (!levels.has(child)) {
        levels.set(child, currentLevel + 1);
        queue.push(child);
      }
    });
  }

  // Assign unconnected nodes to level 0
  nodes.forEach((n) => {
    if (!levels.has(n.id)) {
      levels.set(n.id, 0);
    }
  });

  // Group by level
  const nodesByLevel: Map<number, GraphNode[]> = new Map();
  nodes.forEach((n) => {
    const level = levels.get(n.id)!;
    if (!nodesByLevel.has(level)) nodesByLevel.set(level, []);
    nodesByLevel.get(level)!.push(n);
  });

  // Position nodes
  const HORIZONTAL_SPACING = 180;
  const VERTICAL_SPACING = 120;

  const positionedNodes: Node<OntologyNodeData>[] = [];

  nodesByLevel.forEach((levelNodes, level) => {
    const totalWidth = (levelNodes.length - 1) * HORIZONTAL_SPACING;
    const startX = -totalWidth / 2;

    levelNodes.forEach((node, index) => {
      positionedNodes.push({
        id: node.id,
        type: 'ontology',
        position: {
          x: startX + index * HORIZONTAL_SPACING,
          y: level * VERTICAL_SPACING,
        },
        data: {
          label: node.label,
          type: node.type,
          state: node.state,
        },
      });
    });
  });

  return positionedNodes;
}

function convertEdges(edges: GraphEdge[]): Edge[] {
  return edges.map((edge, index) => ({
    id: `edge-${index}`,
    source: edge.source,
    target: edge.target,
    label: edge.relation,
    type: 'smoothstep',
    animated: true,
    style: { stroke: '#64748b', strokeWidth: 2 },
    labelStyle: { fill: '#94a3b8', fontSize: 10 },
    labelBgStyle: { fill: '#1e293b', fillOpacity: 0.8 },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: '#64748b',
    },
  }));
}

export function SubGraph({ nodes, edges, centerNodeId, onNodeClick, onNodeHover }: SubGraphProps) {
  const initialNodes = useMemo(
    () => layoutNodes(nodes, edges, centerNodeId),
    [nodes, edges, centerNodeId]
  );
  const initialEdges = useMemo(() => convertEdges(edges), [edges]);

  const [flowNodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [flowEdges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick]
  );

  const handleNodeMouseEnter = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeHover?.(node.id);
    },
    [onNodeHover]
  );

  const handleNodeMouseLeave = useCallback(() => {
    onNodeHover?.(null);
  }, [onNodeHover]);

  return (
    <div className="h-full w-full bg-slate-900/50 rounded-lg border border-slate-700/50">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onNodeMouseEnter={handleNodeMouseEnter}
        onNodeMouseLeave={handleNodeMouseLeave}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#334155" gap={20} />
        <Controls
          className="!bg-slate-800 !border-slate-700 [&>button]:!bg-slate-800 [&>button]:!border-slate-700 [&>button]:!text-slate-300"
        />
      </ReactFlow>
    </div>
  );
}
