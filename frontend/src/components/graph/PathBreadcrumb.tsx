'use client';

import { ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface PathBreadcrumbProps {
  path: string[];
  relations: string[];
  onNodeClick?: (nodeId: string) => void;
  className?: string;
}

export function PathBreadcrumb({ path, relations, onNodeClick, className }: PathBreadcrumbProps) {
  if (path.length === 0) return null;

  return (
    <div className={cn('flex flex-wrap items-center gap-1', className)}>
      {path.map((node, index) => (
        <div key={index} className="flex items-center gap-1">
          {/* Node */}
          <button
            onClick={() => onNodeClick?.(node)}
            className="px-2 py-0.5 rounded bg-slate-700/50 hover:bg-slate-700 text-sm text-slate-200 transition-colors"
          >
            {node}
          </button>

          {/* Relation arrow */}
          {index < path.length - 1 && (
            <>
              <ChevronRight className="h-4 w-4 text-slate-500" />
              {relations[index] && (
                <Badge variant="outline" className="text-xs text-slate-400 border-slate-600">
                  {relations[index]}
                </Badge>
              )}
              <ChevronRight className="h-4 w-4 text-slate-500" />
            </>
          )}
        </div>
      ))}
    </div>
  );
}
