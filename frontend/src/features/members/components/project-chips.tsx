/**
 * ProjectChips — compact project badge list for workspace members list (US2, FR-02).
 * Shows project identifiers as small colored chips.
 * Shows "+N more" truncation when more than maxVisible chips.
 */

'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface ProjectChip {
  id: string;
  name: string;
  identifier: string;
}

interface ProjectChipsProps {
  projects: ProjectChip[];
  maxVisible?: number;
  className?: string;
}

export function ProjectChips({ projects, maxVisible = 3, className }: ProjectChipsProps) {
  if (!projects || projects.length === 0) {
    return <span className="text-xs text-muted-foreground italic">No projects</span>;
  }

  const visible = projects.slice(0, maxVisible);
  const overflow = projects.length - maxVisible;

  return (
    <div className={cn('flex flex-wrap gap-1 items-center', className)}>
      {visible.map((p) => (
        <Badge
          key={p.id}
          variant="secondary"
          className="text-[10px] font-mono py-0 px-1.5 h-5"
          title={p.name}
        >
          {p.identifier}
        </Badge>
      ))}
      {overflow > 0 && (
        <span className="text-[10px] text-muted-foreground font-medium">+{overflow} more</span>
      )}
    </div>
  );
}
