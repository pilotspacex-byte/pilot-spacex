/**
 * ToolPermissionsTable — granular per-MCP-tool permission grid (Phase 69 DD-003).
 *
 * Renders all tools returned by GET /ai/permissions, grouped by MCP server.
 * Each row exposes a 3-mode segmented control: Auto / Ask / Deny.
 *
 * DD-003 INVARIANT (non-negotiable, tested):
 *   When `can_set_auto === false`, the "Auto" option MUST be removed from the DOM
 *   (not disabled, not hidden via CSS) and a Tooltip + ShieldAlert icon explains
 *   the constraint. This prevents users from selecting auto on always-approval tools.
 */

'use client';

import * as React from 'react';
import { Shield, ShieldAlert, ShieldOff } from 'lucide-react';
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  useAIPermissions,
  useSetToolPermission,
} from '../hooks/use-ai-permissions';
import {
  parseToolName,
  type ToolPermission,
  type ToolPermissionMode,
} from '../types/ai-permissions';

interface ToolPermissionsTableProps {
  workspaceId: string | undefined;
}

const MODE_META: Record<
  ToolPermissionMode,
  { label: string; Icon: React.ComponentType<{ className?: string }>; activeClass: string }
> = {
  auto: {
    label: 'Auto',
    Icon: Shield,
    activeClass: 'bg-primary/10 text-primary border-primary/30',
  },
  ask: {
    label: 'Ask',
    Icon: ShieldAlert,
    activeClass: 'bg-warning/10 text-warning border-warning/30',
  },
  deny: {
    label: 'Deny',
    Icon: ShieldOff,
    activeClass: 'bg-destructive/10 text-destructive border-destructive/30',
  },
};

export function ToolPermissionsTable({ workspaceId }: ToolPermissionsTableProps) {
  const { data, isLoading, error } = useAIPermissions(workspaceId);
  const setMode = useSetToolPermission(workspaceId);

  // Group tools by MCP server
  const grouped = React.useMemo(() => {
    const map = new Map<string, ToolPermission[]>();
    for (const perm of data ?? []) {
      const { server } = parseToolName(perm.tool_name);
      const list = map.get(server) ?? [];
      list.push(perm);
      map.set(server, list);
    }
    // Sort tools within each group by short name
    for (const [, list] of map) {
      list.sort((a, b) =>
        parseToolName(a.tool_name).shortName.localeCompare(parseToolName(b.tool_name).shortName)
      );
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [data]);

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-base">Per-Tool Permissions</CardTitle>
        <CardDescription>
          Configure approval mode for each MCP tool. Tools marked with{' '}
          <ShieldAlert className="inline h-3.5 w-3.5 text-amber-500 align-middle" /> always
          require approval (DD-003).
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="p-4 text-sm text-destructive" role="alert">
            Failed to load permissions: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        ) : grouped.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground">No tools available.</div>
        ) : (
          <TooltipProvider delayDuration={150}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[55%]">Tool</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead className="w-24 text-right">Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {grouped.map(([server, tools]) => (
                  <React.Fragment key={server}>
                    <TableRow>
                      <TableCell
                        colSpan={3}
                        className="bg-muted/50 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                      >
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-[10px]">
                            {server}
                          </Badge>
                          <span>{tools.length} tools</span>
                        </div>
                      </TableCell>
                    </TableRow>
                    {tools.map((perm) => {
                      const { shortName } = parseToolName(perm.tool_name);
                      return (
                        <ToolRow
                          key={perm.tool_name}
                          perm={perm}
                          shortName={shortName}
                          isPending={
                            setMode.isPending && setMode.variables?.tool_name === perm.tool_name
                          }
                          onChange={(mode) =>
                            setMode.mutate({ tool_name: perm.tool_name, mode })
                          }
                        />
                      );
                    })}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </TooltipProvider>
        )}
      </CardContent>
    </Card>
  );
}

interface ToolRowProps {
  perm: ToolPermission;
  shortName: string;
  isPending: boolean;
  onChange: (mode: ToolPermissionMode) => void;
}

function ToolRow({ perm, shortName, isPending, onChange }: ToolRowProps) {
  // DD-003 INVARIANT: build the allowed mode list — when can_set_auto is false,
  // 'auto' is REMOVED entirely (not disabled).
  const allowedModes: ToolPermissionMode[] = perm.can_set_auto
    ? ['auto', 'ask', 'deny']
    : ['ask', 'deny'];

  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-2">
          <code className="text-sm font-mono">{shortName}</code>
          {!perm.can_set_auto && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  className="inline-flex"
                  aria-label="Always requires approval per DD-003"
                  data-testid={`always-approval-${perm.tool_name}`}
                >
                  <ShieldAlert className="h-3.5 w-3.5 text-amber-500" aria-hidden="true" />
                </span>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p className="max-w-xs text-xs">
                  Requires approval (DD-003). The Auto option is disabled for this tool by
                  policy.
                </p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div
          role="radiogroup"
          aria-label={`Permission mode for ${shortName}`}
          className="inline-flex items-center gap-1 rounded-md border bg-background p-0.5"
        >
          {allowedModes.map((mode) => {
            const meta = MODE_META[mode];
            const isActive = perm.mode === mode;
            return (
              <Button
                key={mode}
                type="button"
                role="radio"
                aria-checked={isActive}
                size="sm"
                variant="ghost"
                disabled={isPending}
                onClick={() => {
                  if (!isActive) onChange(mode);
                }}
                className={cn(
                  'h-7 gap-1 px-2 text-xs font-medium border border-transparent',
                  isActive && meta.activeClass
                )}
                data-testid={`mode-${mode}-${perm.tool_name}`}
              >
                <meta.Icon className="h-3 w-3" aria-hidden="true" />
                {meta.label}
              </Button>
            );
          })}
        </div>
      </TableCell>
      <TableCell className="text-right">
        <Badge
          variant="outline"
          className="text-[10px] uppercase tracking-wide text-muted-foreground"
        >
          {perm.source}
        </Badge>
      </TableCell>
    </TableRow>
  );
}
