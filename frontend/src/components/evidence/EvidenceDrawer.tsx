'use client';

import { FileText, Network, Clock, ExternalLink, Loader2 } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useEvidence } from '@/hooks/useApi';
import type { ChatResponse, OntologyPath, DocumentRef } from '@/types/api';

interface EvidenceDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  traceId: string | null;
  response?: ChatResponse;
}

export function EvidenceDrawer({
  open,
  onOpenChange,
  traceId,
  response,
}: EvidenceDrawerProps) {
  const { data: evidenceData, isLoading, error } = useEvidence(traceId);

  // Use cached response data if available, otherwise use fetched data
  const evidence = response?.evidence ?? evidenceData?.evidence;
  const graph = response?.graph;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-[400px] sm:max-w-[540px] bg-slate-900 border-slate-700 overflow-y-auto"
      >
        <SheetHeader className="border-b border-slate-700/50 pb-4">
          <SheetTitle className="text-white flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-400" />
            근거 상세
          </SheetTitle>
          {traceId && (
            <SheetDescription className="text-slate-400 font-mono text-xs">
              Trace ID: {traceId}
            </SheetDescription>
          )}
        </SheetHeader>

        <div className="py-4 space-y-6">
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
              <span className="ml-2 text-slate-400">로딩 중...</span>
            </div>
          )}

          {error && (
            <Card className="p-4 bg-red-500/10 border-red-500/50">
              <p className="text-red-400 text-sm">
                근거를 불러오는 중 오류가 발생했습니다.
              </p>
            </Card>
          )}

          {!isLoading && !error && evidence && (
            <>
              {/* Ontology Paths */}
              <OntologyPathsSection paths={evidence.ontologyPathObjects} />

              {/* Document References */}
              <DocumentRefsSection refs={evidence.documentRefs} />

              {/* Similar Events */}
              <SimilarEventsSection events={evidence.similarEvents} />

              {/* Graph Summary */}
              {graph && graph.nodes.length > 0 && (
                <GraphSummarySection graph={graph} />
              )}
            </>
          )}

          {!isLoading && !error && !evidence && (
            <div className="text-center py-8 text-slate-500">
              <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>근거 데이터가 없습니다.</p>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function OntologyPathsSection({ paths }: { paths?: OntologyPath[] }) {
  if (!paths || paths.length === 0) return null;

  return (
    <div>
      <h3 className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-3">
        <Network className="h-4 w-4 text-purple-400" />
        온톨로지 경로
        <Badge variant="outline" className="ml-auto text-xs border-slate-700 text-slate-500">
          {paths.length}개
        </Badge>
      </h3>
      <div className="space-y-2">
        {paths.map((p, i) => (
          <Card key={i} className="p-3 bg-slate-800/50 border-slate-700/50">
            <div className="flex flex-wrap items-center gap-1 text-xs">
              {p.path.map((node, j) => (
                <span key={j} className="flex items-center gap-1">
                  <span className="text-slate-200 bg-slate-700 px-2 py-0.5 rounded">
                    {node}
                  </span>
                  {j < p.path.length - 1 && (
                    <span className="text-purple-400">
                      {p.relations?.[j] ? `—${p.relations[j]}→` : '→'}
                    </span>
                  )}
                </span>
              ))}
            </div>
            {p.confidence !== undefined && (
              <div className="mt-2 text-xs text-slate-500">
                신뢰도: {Math.round(p.confidence * 100)}%
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

function DocumentRefsSection({ refs }: { refs?: DocumentRef[] }) {
  if (!refs || refs.length === 0) return null;

  return (
    <div>
      <h3 className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-3">
        <FileText className="h-4 w-4 text-green-400" />
        문서 참조
        <Badge variant="outline" className="ml-auto text-xs border-slate-700 text-slate-500">
          {refs.length}개
        </Badge>
      </h3>
      <div className="space-y-2">
        {refs.map((d, i) => (
          <Card
            key={i}
            className="p-3 bg-slate-800/50 border-slate-700/50 hover:border-green-500/30 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="text-sm text-slate-200">{d.docId || '문서'}</span>
                {d.page !== undefined && (
                  <span className="text-slate-500 text-xs ml-2">p.{d.page}</span>
                )}
                {d.chunkId && (
                  <span className="text-slate-600 text-xs ml-2 font-mono">
                    #{d.chunkId.slice(0, 8)}
                  </span>
                )}
              </div>
              <ExternalLink className="h-3 w-3 text-slate-600" />
            </div>
            {d.relevance !== undefined && (
              <div className="mt-2">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500 rounded-full"
                      style={{ width: `${d.relevance * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-500">
                    {Math.round(d.relevance * 100)}%
                  </span>
                </div>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

function SimilarEventsSection({ events }: { events?: string[] }) {
  if (!events || events.length === 0) return null;

  return (
    <div>
      <h3 className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-3">
        <Clock className="h-4 w-4 text-yellow-400" />
        유사 이벤트
        <Badge variant="outline" className="ml-auto text-xs border-slate-700 text-slate-500">
          {events.length}개
        </Badge>
      </h3>
      <div className="space-y-1">
        {events.map((evt, i) => (
          <div
            key={i}
            className="text-xs text-slate-400 py-1 px-2 bg-slate-800/30 rounded"
          >
            {evt}
          </div>
        ))}
      </div>
    </div>
  );
}

function GraphSummarySection({
  graph,
}: {
  graph: { nodes: { id: string; type: string; label: string; state?: string }[]; edges: { source: string; target: string; relation: string }[] };
}) {
  const nodesByType = graph.nodes.reduce((acc, node) => {
    acc[node.type] = (acc[node.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const relationTypes = [...new Set(graph.edges.map((e) => e.relation))];

  return (
    <div>
      <h3 className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-3">
        <Network className="h-4 w-4 text-blue-400" />
        그래프 요약
      </h3>
      <Card className="p-3 bg-slate-800/50 border-slate-700/50 space-y-3">
        <div>
          <span className="text-xs text-slate-500">노드</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {Object.entries(nodesByType).map(([type, count]) => (
              <Badge
                key={type}
                variant="outline"
                className="text-xs border-slate-600 text-slate-400"
              >
                {type}: {count}
              </Badge>
            ))}
          </div>
        </div>
        <div>
          <span className="text-xs text-slate-500">관계 타입</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {relationTypes.map((rel) => (
              <Badge
                key={rel}
                variant="outline"
                className="text-xs border-blue-700/50 text-blue-400"
              >
                {rel}
              </Badge>
            ))}
          </div>
        </div>
        <div className="text-xs text-slate-500 pt-2 border-t border-slate-700/50">
          총 {graph.nodes.length}개 노드, {graph.edges.length}개 엣지
        </div>
      </Card>
    </div>
  );
}
