'use client';

import { useState, useMemo } from 'react';
import { SubGraph } from './SubGraph';
import { PathBreadcrumb } from './PathBreadcrumb';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/stores/uiStore';
import { useOntologyEntities, useOntologyGraph, useOntologyEntity } from '@/hooks/useApi';
import type { GraphNode, GraphEdge } from '@/types/api';
import { Loader2, ChevronDown, Search, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

// 타입 색상 매핑
const typeColors: Record<string, string> = {
  Robot: 'bg-blue-500',
  Sensor: 'bg-purple-500',
  MeasurementAxis: 'bg-cyan-500',
  Pattern: 'bg-yellow-500',
  ErrorCode: 'bg-red-500',
  Cause: 'bg-orange-500',
  Resolution: 'bg-green-500',
  State: 'bg-pink-500',
  Joint: 'bg-indigo-500',
  Document: 'bg-gray-500',
};

export function GraphView() {
  const { graphCenterNode, setGraphCenterNode } = useUIStore();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [depth, setDepth] = useState(2);
  const [showEntityPicker, setShowEntityPicker] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // 초기 중심 노드 (없으면 PAT_COLLISION 사용)
  const centerNodeId = graphCenterNode || 'PAT_COLLISION';

  // API 훅들
  const { data: entitiesData, isLoading: entitiesLoading } = useOntologyEntities();
  const { data: graphData, isLoading: graphLoading, error: graphError } = useOntologyGraph(
    centerNodeId,
    depth,
    'both',
    true
  );
  const { data: entityDetail } = useOntologyEntity(selectedNodeId);

  // API 데이터를 GraphNode/GraphEdge 형식으로 변환
  const { nodes, edges } = useMemo(() => {
    if (!graphData) return { nodes: [], edges: [] };

    const convertedNodes: GraphNode[] = graphData.nodes.map((n) => ({
      id: n.id,
      type: n.type,
      label: n.label,
      state: n.id === centerNodeId ? 'warning' : undefined,
    }));

    const convertedEdges: GraphEdge[] = graphData.edges.map((e) => ({
      source: e.source,
      target: e.target,
      relation: e.relation,
    }));

    return { nodes: convertedNodes, edges: convertedEdges };
  }, [graphData, centerNodeId]);

  // 현재 경로 (중심 노드 기준)
  const currentPath = useMemo(() => {
    if (!graphData || nodes.length === 0) return [centerNodeId];
    return [centerNodeId];
  }, [graphData, nodes, centerNodeId]);

  // 필터링된 엔티티 목록
  const filteredEntities = useMemo(() => {
    if (!entitiesData) return [];
    return entitiesData.entities.filter((e) => {
      const matchesType = filterType === 'all' || e.type === filterType;
      const matchesSearch = !searchQuery ||
        e.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesType && matchesSearch;
    });
  }, [entitiesData, filterType, searchQuery]);

  const handleNodeClick = (nodeId: string) => {
    setSelectedNodeId(nodeId);
  };

  const handleNodeDoubleClick = (nodeId: string) => {
    // 더블클릭 시 해당 노드를 중심으로 그래프 확장
    setGraphCenterNode(nodeId);
    setSelectedNodeId(null);
  };

  const handleEntitySelect = (entityId: string) => {
    setGraphCenterNode(entityId);
    setShowEntityPicker(false);
    setSelectedNodeId(null);
  };

  const handleReset = () => {
    setGraphCenterNode('PAT_COLLISION');
    setSelectedNodeId(null);
    setDepth(2);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header Controls */}
      <div className="p-3 border-b border-slate-700/50 bg-slate-800/30">
        <div className="flex items-center justify-between gap-3">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2">
            <PathBreadcrumb
              path={currentPath}
              relations={[]}
              onNodeClick={handleNodeClick}
            />
            {hoveredNodeId && (
              <Badge variant="outline" className="text-xs text-slate-400 border-slate-700">
                {hoveredNodeId}
              </Badge>
            )}
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2">
            {/* Depth Control */}
            <div className="flex items-center gap-1 px-2 py-1 bg-slate-700/50 rounded">
              <span className="text-xs text-slate-400">Depth:</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => setDepth(Math.max(1, depth - 1))}
                disabled={depth <= 1}
              >
                <ZoomOut className="h-3 w-3" />
              </Button>
              <span className="text-sm text-white w-4 text-center">{depth}</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => setDepth(Math.min(4, depth + 1))}
                disabled={depth >= 4}
              >
                <ZoomIn className="h-3 w-3" />
              </Button>
            </div>

            {/* Entity Picker */}
            <div className="relative">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={() => setShowEntityPicker(!showEntityPicker)}
              >
                <Search className="h-3 w-3 mr-1" />
                시작점 선택
                <ChevronDown className="h-3 w-3 ml-1" />
              </Button>

              {showEntityPicker && (
                <div className="absolute top-full right-0 mt-1 w-80 max-h-96 overflow-auto bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50">
                  {/* Search & Filter */}
                  <div className="p-2 border-b border-slate-700 sticky top-0 bg-slate-800">
                    <input
                      type="text"
                      placeholder="검색..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full px-2 py-1 text-sm bg-slate-700 border border-slate-600 rounded text-white placeholder-slate-400"
                    />
                    <div className="flex flex-wrap gap-1 mt-2">
                      <Badge
                        variant={filterType === 'all' ? 'default' : 'outline'}
                        className="cursor-pointer text-xs"
                        onClick={() => setFilterType('all')}
                      >
                        전체
                      </Badge>
                      {entitiesData?.by_type && Object.keys(entitiesData.by_type).map((type) => (
                        <Badge
                          key={type}
                          variant={filterType === type ? 'default' : 'outline'}
                          className="cursor-pointer text-xs"
                          onClick={() => setFilterType(type)}
                        >
                          {type} ({entitiesData.by_type[type]})
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Entity List */}
                  <div className="p-1">
                    {entitiesLoading ? (
                      <div className="flex items-center justify-center p-4">
                        <Loader2 className="h-4 w-4 animate-spin" />
                      </div>
                    ) : (
                      filteredEntities.map((entity) => (
                        <button
                          key={entity.id}
                          className="w-full px-3 py-2 text-left hover:bg-slate-700/50 rounded flex items-center gap-2"
                          onClick={() => handleEntitySelect(entity.id)}
                        >
                          <span className={`w-2 h-2 rounded-full ${typeColors[entity.type] || 'bg-gray-500'}`} />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm text-white truncate">{entity.label}</div>
                            <div className="text-xs text-slate-400">{entity.id}</div>
                          </div>
                          <Badge variant="outline" className="text-xs shrink-0">
                            {entity.type}
                          </Badge>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Reset */}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs"
              onClick={handleReset}
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              초기화
            </Button>
          </div>
        </div>
      </div>

      {/* Graph Area */}
      <div className="flex-1 p-4 relative">
        {graphLoading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
              <span className="text-sm text-slate-400">그래프 로딩 중...</span>
            </div>
          </div>
        ) : graphError ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <p className="text-red-400 mb-2">그래프 로딩 실패</p>
              <Button variant="outline" size="sm" onClick={handleReset}>
                다시 시도
              </Button>
            </div>
          </div>
        ) : (
          <>
            <SubGraph
              nodes={nodes}
              edges={edges}
              centerNodeId={centerNodeId}
              onNodeClick={handleNodeClick}
              onNodeHover={setHoveredNodeId}
            />
            {/* 노드 더블클릭 안내 */}
            <div className="absolute bottom-2 left-2 text-xs text-slate-500">
              💡 노드를 더블클릭하면 해당 노드를 중심으로 그래프가 확장됩니다
            </div>
            {/* 그래프 통계 */}
            <div className="absolute top-2 right-2 text-xs text-slate-500">
              노드: {nodes.length} | 엣지: {edges.length}
            </div>
          </>
        )}
      </div>

      {/* Node Detail Panel */}
      {selectedNodeId && (
        <div className="p-4 border-t border-slate-700/50 bg-slate-800/30">
          <Card className="p-4 bg-slate-800/50 border-slate-700/50">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="text-lg font-medium text-white">
                  {entityDetail?.name || selectedNodeId}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className="text-slate-400 border-slate-600">
                    {entityDetail?.type || '...'}
                  </Badge>
                  {entityDetail?.domain && (
                    <Badge variant="outline" className="text-slate-400 border-slate-600">
                      {entityDetail.domain}
                    </Badge>
                  )}
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleEntitySelect(selectedNodeId)}
              >
                중심으로 설정
              </Button>
            </div>

            {entityDetail?.description && (
              <p className="text-sm text-slate-300 mt-2">{entityDetail.description}</p>
            )}

            {entityDetail?.properties && Object.keys(entityDetail.properties).length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-700">
                <div className="text-xs text-slate-500 mb-1">속성:</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(entityDetail.properties).map(([key, value]) => (
                    <Badge key={key} variant="secondary" className="text-xs">
                      {key}: {JSON.stringify(value)}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
