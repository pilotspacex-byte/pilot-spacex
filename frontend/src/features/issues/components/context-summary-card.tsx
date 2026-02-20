'use client';

import type { ElementType } from 'react';
import { FileText, Link2, BookOpen, Code, ListChecks } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { ContextSummary } from '@/stores/ai/AIContextStore';

export interface ContextSummaryCardProps {
  summary: ContextSummary;
}

const STAT_STYLES: Record<string, string> = {
  Issues: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  Docs: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  Files: 'bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
  Tasks: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
};

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
            {summary.stats.relatedCount +
              summary.stats.docsCount +
              summary.stats.filesCount +
              summary.stats.tasksCount ===
            0 ? (
              <p className="text-xs text-muted-foreground italic">No related items found yet</p>
            ) : (
              <div className="flex items-center gap-3 pt-1 flex-wrap">
                {summary.stats.relatedCount > 0 && (
                  <StatPill icon={Link2} label="Issues" count={summary.stats.relatedCount} />
                )}
                {summary.stats.docsCount > 0 && (
                  <StatPill icon={BookOpen} label="Docs" count={summary.stats.docsCount} />
                )}
                {summary.stats.filesCount > 0 && (
                  <StatPill icon={Code} label="Files" count={summary.stats.filesCount} />
                )}
                {summary.stats.tasksCount > 0 && (
                  <StatPill icon={ListChecks} label="Tasks" count={summary.stats.tasksCount} />
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatPill({
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
      className={cn(
        'flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        STAT_STYLES[label] ?? 'bg-muted text-muted-foreground'
      )}
      aria-label={`${count} ${label}`}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      <span>{count}</span>
      <span className="opacity-70">{label}</span>
    </div>
  );
}
