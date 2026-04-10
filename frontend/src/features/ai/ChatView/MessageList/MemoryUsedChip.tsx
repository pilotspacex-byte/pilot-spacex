/**
 * MemoryUsedChip — inline chip rendered in an assistant message when long-term
 * memory recall provided grounding sources for the response.
 *
 * Phase 69. Click opens a Popover listing each source with type/score/id.
 */

import { memo } from 'react';
import { Brain } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

export interface MemorySource {
  id: string;
  type: string;
  score: number;
}

interface MemoryUsedChipProps {
  sources: MemorySource[] | undefined;
}

export const MemoryUsedChip = memo<MemoryUsedChipProps>(({ sources }) => {
  if (!sources || sources.length === 0) return null;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={`Memory used: ${sources.length} sources. Click for details.`}
          data-testid="memory-used-chip"
        >
          <Brain className="h-3 w-3" aria-hidden="true" />
          <span>
            {sources.length} memor{sources.length === 1 ? 'y' : 'ies'} used
          </span>
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80 p-2">
        <div className="mb-2 px-2 text-xs font-semibold text-muted-foreground">
          Sources used by the agent
        </div>
        <ul className="space-y-1" aria-label="Memory sources">
          {sources.map((s) => (
            <li
              key={s.id}
              className="flex items-center justify-between gap-2 rounded px-2 py-1.5 text-xs hover:bg-muted/50"
            >
              <div className="flex min-w-0 items-center gap-2">
                <Badge variant="secondary" className="text-[9px] uppercase">
                  {s.type}
                </Badge>
                <code className="truncate text-[10px] text-muted-foreground">
                  {s.id.slice(0, 12)}
                </code>
              </div>
              <span className="shrink-0 text-[10px] tabular-nums text-muted-foreground">
                {s.score.toFixed(2)}
              </span>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
});

MemoryUsedChip.displayName = 'MemoryUsedChip';
