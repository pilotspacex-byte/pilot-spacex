/**
 * PermissionAuditLog — paginated, admin-only audit log of AI permission changes.
 *
 * Phase 69 DD-003. Backend: GET /ai/permissions/audit-log?limit&offset.
 */

'use client';

import * as React from 'react';
import { ChevronLeft, ChevronRight, ScrollText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useAIPermissionsAuditLog } from '../hooks/use-ai-permissions';
import { parseToolName } from '../types/ai-permissions';

const PAGE_SIZE = 50;

interface PermissionAuditLogProps {
  workspaceId: string | undefined;
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diffSec = Math.floor((Date.now() - then) / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

export function PermissionAuditLog({ workspaceId }: PermissionAuditLogProps) {
  const [page, setPage] = React.useState(0);
  const offset = page * PAGE_SIZE;
  const { data, isLoading, error } = useAIPermissionsAuditLog(workspaceId, {
    limit: PAGE_SIZE,
    offset,
  });

  const entries = data ?? [];
  const hasNext = entries.length === PAGE_SIZE;
  const hasPrev = page > 0;

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <ScrollText className="h-4 w-4 text-muted-foreground" />
              Permission Audit Log
            </CardTitle>
            <CardDescription>
              All permission changes are recorded. Showing {entries.length} entries (page{' '}
              {page + 1}).
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-2 p-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="p-4 text-sm text-destructive" role="alert">
            Failed to load audit log: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        ) : entries.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground">No audit entries.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tool</TableHead>
                <TableHead>Change</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead className="text-right">When</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((entry) => {
                const { shortName } = parseToolName(entry.tool_name);
                return (
                  <TableRow key={entry.id}>
                    <TableCell>
                      <code className="text-xs font-mono">{shortName}</code>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5 text-xs">
                        <Badge variant="outline" className="text-[10px]">
                          {entry.old_mode ?? '—'}
                        </Badge>
                        <span className="text-muted-foreground">→</span>
                        <Badge variant="secondary" className="text-[10px]">
                          {entry.new_mode}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <code className="text-[11px] text-muted-foreground">
                        {entry.actor_user_id ? `${entry.actor_user_id.slice(0, 8)}…` : 'system'}
                      </code>
                    </TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground">
                      {relativeTime(entry.created_at)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
        <div className="flex items-center justify-end gap-2 border-t p-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={!hasPrev || isLoading}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasNext || isLoading}
            aria-label="Next page"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
