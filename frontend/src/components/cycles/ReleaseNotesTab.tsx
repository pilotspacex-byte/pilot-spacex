'use client';

/**
 * ReleaseNotesTab - Displays AI-classified release notes for a cycle.
 *
 * T-026: Release notes tab in cycle detail.
 * T-027: Markdown export with clipboard copy.
 */

import * as React from 'react';
import { Copy, Check, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { ReleaseNotesData, ReleaseEntry } from '@/services/api';

// ── Types ────────────────────────────────────────────────────────────────────

export interface ReleaseNotesTabProps {
  workspaceId: string;
  cycleId: string;
  cycleName: string;
  data: ReleaseNotesData | undefined;
  isLoading: boolean;
}

// ── Category Config ──────────────────────────────────────────────────────────

const CATEGORY_ORDER = [
  'features',
  'bug_fixes',
  'improvements',
  'internal',
  'uncategorized',
] as const;

type Category = (typeof CATEGORY_ORDER)[number];

const CATEGORY_LABELS: Record<Category, string> = {
  features: 'Features',
  bug_fixes: 'Bug Fixes',
  improvements: 'Improvements',
  internal: 'Internal',
  uncategorized: 'Uncategorized',
};

const CATEGORY_BADGE_VARIANTS: Record<
  Category,
  'default' | 'secondary' | 'outline' | 'destructive'
> = {
  features: 'default',
  bug_fixes: 'destructive',
  improvements: 'secondary',
  internal: 'outline',
  uncategorized: 'outline',
};

// ── Helper Functions ─────────────────────────────────────────────────────────

function groupEntriesByCategory(entries: ReleaseEntry[]): Map<Category, ReleaseEntry[]> {
  const grouped = new Map<Category, ReleaseEntry[]>();
  for (const cat of CATEGORY_ORDER) {
    grouped.set(cat, []);
  }

  for (const entry of entries) {
    const cat = (entry.category as Category) ?? 'uncategorized';
    const bucket = grouped.get(cat) ?? grouped.get('uncategorized')!;
    bucket.push(entry);
  }

  return grouped;
}

function buildMarkdown(cycleName: string, grouped: Map<Category, ReleaseEntry[]>): string {
  const lines: string[] = [`## Release Notes — ${cycleName}`, ''];

  for (const cat of CATEGORY_ORDER) {
    const entries = grouped.get(cat);
    if (!entries || entries.length === 0) continue;

    lines.push(`### ${CATEGORY_LABELS[cat]}`);
    for (const entry of entries) {
      lines.push(`- ${entry.identifier}: ${entry.name}`);
    }
    lines.push('');
  }

  return lines.join('\n').trimEnd();
}

// ── Loading Skeleton ─────────────────────────────────────────────────────────

function ReleaseNotesSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i}>
          <CardHeader className="pb-2">
            <Skeleton className="h-5 w-32" />
          </CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export function ReleaseNotesTab({ cycleName, data, isLoading }: ReleaseNotesTabProps) {
  const [copied, setCopied] = React.useState(false);

  const grouped = React.useMemo(() => {
    if (!data) return new Map<Category, ReleaseEntry[]>();
    return groupEntriesByCategory(data.entries);
  }, [data]);

  const totalEntries = data?.entries.length ?? 0;

  const handleExportMarkdown = React.useCallback(async () => {
    const markdown = buildMarkdown(cycleName, grouped);
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard write failed silently — browser may have denied permission
    }
  }, [cycleName, grouped]);

  if (isLoading) {
    return (
      <div className="p-6">
        <ReleaseNotesSkeleton />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="size-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Release Notes</h2>
          {data && (
            <Badge variant="secondary" className="ml-1">
              {totalEntries} {totalEntries === 1 ? 'issue' : 'issues'}
            </Badge>
          )}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleExportMarkdown}
          disabled={!data || totalEntries === 0}
          aria-label="Export release notes as Markdown and copy to clipboard"
        >
          {copied ? (
            <>
              <Check className="size-4 mr-2 text-green-500" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="size-4 mr-2" />
              Export as Markdown
            </>
          )}
        </Button>
      </div>

      {/* Empty state */}
      {totalEntries === 0 && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <FileText className="size-12 text-muted-foreground/40 mb-4" />
            <p className="text-muted-foreground font-medium">No completed issues in this cycle</p>
            <p className="text-sm text-muted-foreground/70 mt-1">
              Complete issues to see them here as release notes.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Grouped categories */}
      {totalEntries > 0 &&
        CATEGORY_ORDER.map((cat) => {
          const entries = grouped.get(cat);
          if (!entries || entries.length === 0) return null;

          return (
            <Card key={cat}>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Badge variant={CATEGORY_BADGE_VARIANTS[cat]}>{CATEGORY_LABELS[cat]}</Badge>
                  <span className="text-muted-foreground font-normal text-sm">
                    {entries.length} {entries.length === 1 ? 'issue' : 'issues'}
                  </span>
                </CardTitle>
                <CardDescription className="sr-only">
                  {CATEGORY_LABELS[cat]} release entries
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-1">
                  {entries.map((entry) => (
                    <div
                      key={entry.issueId}
                      className="flex items-center gap-3 py-2 px-3 rounded-md hover:bg-muted/50"
                    >
                      <span className="text-sm font-mono text-muted-foreground shrink-0">
                        {entry.identifier}
                      </span>
                      <span className="text-sm flex-1 truncate">{entry.name}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
    </div>
  );
}
