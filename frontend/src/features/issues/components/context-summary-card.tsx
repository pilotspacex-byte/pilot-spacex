'use client';

import type { ElementType } from 'react';
import { FileText, Link2, BookOpen, Code, ListChecks } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import type { ContextSummary } from '@/stores/ai/AIContextStore';

export interface ContextSummaryCardProps {
  summary: ContextSummary;
}

export function ContextSummaryCard({ summary }: ContextSummaryCardProps) {
  return (
    <Card className="bg-gradient-to-br from-ai/5 to-ai/10 border-ai/20">
      <CardContent className="p-5">
        <div className="flex items-start gap-3">
          <FileText className="size-5 text-ai mt-0.5 shrink-0" aria-hidden="true" />
          <div className="space-y-3 min-w-0">
            <div>
              <p className="text-xs font-medium text-ai">{summary.issueIdentifier}</p>
              <h3 className="text-base font-semibold leading-snug">{summary.title}</h3>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">{summary.summaryText}</p>
            <div className="flex items-center gap-4 pt-1">
              <StatItem icon={Link2} label="Issues" count={summary.stats.relatedCount} />
              <StatItem icon={BookOpen} label="Docs" count={summary.stats.docsCount} />
              <StatItem icon={Code} label="Files" count={summary.stats.filesCount} />
              <StatItem icon={ListChecks} label="Tasks" count={summary.stats.tasksCount} />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatItem({
  icon: Icon,
  label,
  count,
}: {
  icon: ElementType;
  label: string;
  count: number;
}) {
  return (
    <div
      className="flex items-center gap-1.5 text-xs text-muted-foreground"
      aria-label={`${count} ${label}`}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      <span className="font-medium text-foreground">{count}</span>
      <span>{label}</span>
    </div>
  );
}
