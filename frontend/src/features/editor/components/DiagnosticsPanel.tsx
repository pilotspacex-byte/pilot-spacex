'use client';

import { useState, useMemo, useCallback } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import type { Diagnostic, DiagnosticCounts } from '../language/diagnostics';
import { DiagnosticRow } from './DiagnosticRow';

type FilterMode = 'all' | 'errors' | 'warnings';

/** Severity sort order: errors first, then warnings, info, hint. */
const SEVERITY_ORDER: Record<Diagnostic['severity'], number> = {
  error: 0,
  warning: 1,
  info: 2,
  hint: 3,
};

interface DiagnosticsPanelProps {
  diagnostics: Diagnostic[];
  counts: DiagnosticCounts;
  onNavigate: (uri: string, line: number, column: number) => void;
  className?: string;
}

export function DiagnosticsPanel({
  diagnostics,
  counts,
  onNavigate,
  className,
}: DiagnosticsPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(true);
  const [filter, setFilter] = useState<FilterMode>('all');

  const toggleCollapsed = useCallback(() => setIsCollapsed((prev) => !prev), []);

  const filteredDiagnostics = useMemo(() => {
    let items = diagnostics;
    if (filter === 'errors') {
      items = diagnostics.filter((d) => d.severity === 'error');
    } else if (filter === 'warnings') {
      items = diagnostics.filter((d) => d.severity === 'warning');
    }
    return items.slice().sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
  }, [diagnostics, filter]);

  // Build badge text from non-zero counts
  const badgeParts: string[] = [];
  if (counts.errors > 0) badgeParts.push(`${counts.errors} error${counts.errors !== 1 ? 's' : ''}`);
  if (counts.warnings > 0)
    badgeParts.push(`${counts.warnings} warning${counts.warnings !== 1 ? 's' : ''}`);

  return (
    <div className={cn('border-t border-border bg-background', className)}>
      {/* Header bar - always visible */}
      <div className="flex items-center h-8 px-2 gap-2">
        <button
          type="button"
          onClick={toggleCollapsed}
          className="flex items-center gap-1.5 hover:bg-accent/50 rounded px-1 py-0.5 transition-colors"
          aria-expanded={!isCollapsed}
          aria-label={isCollapsed ? 'Expand problems panel' : 'Collapse problems panel'}
        >
          {isCollapsed ? (
            <ChevronRight className="size-3.5 text-muted-foreground" />
          ) : (
            <ChevronDown className="size-3.5 text-muted-foreground" />
          )}
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Problems
          </span>
        </button>

        {badgeParts.length > 0 && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
            {badgeParts.join(', ')}
          </Badge>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Filter toggles */}
        <div className="flex items-center gap-0.5">
          {(['all', 'errors', 'warnings'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setFilter(mode)}
              className={cn(
                'text-[10px] px-2 py-0.5 rounded transition-colors capitalize',
                filter === mode
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
              )}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Body - visible when expanded */}
      {!isCollapsed && (
        <div className="max-h-48 overflow-y-auto">
          {filteredDiagnostics.length === 0 ? (
            <div className="flex items-center justify-center h-12 text-muted-foreground text-xs">
              No problems detected
            </div>
          ) : (
            <div className="py-0.5">
              {filteredDiagnostics.map((d, i) => (
                <DiagnosticRow
                  key={`${d.modelUri}-${d.startLineNumber}-${d.startColumn}-${i}`}
                  diagnostic={d}
                  onClick={onNavigate}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
