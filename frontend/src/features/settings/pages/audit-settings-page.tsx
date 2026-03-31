/**
 * AuditSettingsPage - Read-only audit log viewer for workspace admins.
 * AUDIT-03..06: Filter UI, Export UI, Retention note, zero write affordances.
 * NOTE: MUST NOT be wrapped in observer() — plain React component.
 */

'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { AlertCircle, ChevronDown, ChevronRight, Download, Loader2, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useStore } from '@/stores';
import { useWorkspaceMembers } from '@/features/issues/hooks/use-workspace-members';
import {
  useAuditLog,
  useExportAuditLog,
  useRollbackAIArtifact,
  type AuditFilters,
  type AuditLogEntry,
} from '../hooks/use-audit-log';
import { formatAction, formatResourceType } from '../utils/audit-labels';

const EXPORT_WARNING_THRESHOLD = 10_000;

const ACTION_OPTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'issue.create', label: 'issue.create' },
  { value: 'issue.update', label: 'issue.update' },
  { value: 'issue.delete', label: 'issue.delete' },
  { value: 'note.create', label: 'note.create' },
  { value: 'note.update', label: 'note.update' },
  { value: 'note.delete', label: 'note.delete' },
  { value: 'member.invite', label: 'member.invite' },
  { value: 'member.remove', label: 'member.remove' },
  { value: 'role.assign', label: 'role.assign' },
  { value: 'settings.update', label: 'settings.update' },
  { value: 'ai.action', label: 'ai.action' },
];

const RESOURCE_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'issue', label: 'issue' },
  { value: 'note', label: 'note' },
  { value: 'member', label: 'member' },
  { value: 'workspace', label: 'workspace' },
  { value: 'role', label: 'role' },
  { value: 'settings', label: 'settings' },
  { value: 'ai', label: 'ai' },
];

function formatTimestamp(isoString: string): string {
  return new Date(isoString).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function truncate(value: string | null, length: number): string {
  if (!value) return '—';
  return value.length > length ? value.slice(0, length) + '…' : value;
}

function ActorTypeBadge({ actorType }: { actorType: AuditLogEntry['actorType'] }) {
  const variants: Record<AuditLogEntry['actorType'], 'default' | 'secondary' | 'outline'> = {
    USER: 'secondary',
    SYSTEM: 'outline',
    AI: 'default',
  };

  return (
    <Badge variant={variants[actorType]} className="text-xs">
      {actorType}
    </Badge>
  );
}

function AuditSkeletonRows() {
  return (
    <>
      {[1, 2, 3, 4, 5].map((i) => (
        <TableRow key={i}>
          {[140, 120, 100, 80, 80, 80].map((w, j) => (
            <TableCell key={j}>
              <Skeleton data-testid="skeleton" className={`h-4 w-[${w}px]`} />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

function ExpandedRowContent({
  entry,
  workspaceSlug,
  onRollback,
  isRollingBack,
}: {
  entry: AuditLogEntry;
  workspaceSlug: string;
  onRollback?: () => void;
  isRollingBack?: boolean;
}) {
  return (
    <div className="space-y-3 px-4 py-3 bg-muted/30 border-t">
      {/* Payload diff */}
      {entry.payload ? (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Payload Diff
          </p>
          <pre className="text-xs font-mono bg-muted rounded p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-64">
            {JSON.stringify(entry.payload, null, 2)}
          </pre>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">No payload recorded.</p>
      )}

      {/* AI fields — only shown for AI actor */}
      {entry.actorType === 'AI' && (
        <div className="space-y-2 pt-1 border-t">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            AI Details
          </p>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">Model</p>
              <p className="font-mono">{entry.aiModel ?? '—'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Token Cost</p>
              <p>{entry.aiTokenCost != null ? `$${entry.aiTokenCost.toFixed(6)}` : '—'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Rationale</p>
              <p className="text-xs">{entry.aiRationale ?? '—'}</p>
            </div>
          </div>
          {entry.approvalRequestId && (
            <a
              href={`/${workspaceSlug}/approvals?highlight=${entry.approvalRequestId}`}
              className="inline-block text-xs text-primary hover:underline mt-1"
            >
              View approval request →
            </a>
          )}
          {onRollback && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRollback();
              }}
              disabled={isRollingBack}
              className="inline-flex items-center gap-1.5 text-xs text-destructive hover:underline disabled:opacity-50 mt-1"
              aria-label="Rollback this AI action"
            >
              <RotateCcw className="h-3 w-3" aria-hidden />
              {isRollingBack ? 'Rolling back\u2026' : 'Rollback'}
            </button>
          )}
        </div>
      )}

      {/* Full resource ID */}
      <div className="text-xs text-muted-foreground pt-1 border-t">
        <span className="font-medium">Full Resource ID:</span>{' '}
        <span className="font-mono">{entry.resourceId ?? '—'}</span>
      </div>
    </div>
  );
}

export function AuditSettingsPage() {
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const { workspaceStore } = useStore();
  const workspaceId = workspaceStore.getWorkspaceBySlug?.(workspaceSlug)?.id ?? workspaceSlug;

  const { data: membersData } = useWorkspaceMembers(workspaceId);
  const members = membersData?.items ?? [];
  const actorNameMap = React.useMemo(
    () => new Map(members.map((m) => [m.userId, m.fullName ?? m.email.split('@')[0] ?? m.email])),
    [members]
  );

  const [actorInput, setActorInput] = React.useState('');
  const [debouncedActorId, setDebouncedActorId] = React.useState('');
  const [selectedActorType, setSelectedActorType] = React.useState<'AI' | 'USER' | 'SYSTEM' | ''>(
    ''
  );
  const [selectedAction, setSelectedAction] = React.useState('');
  const [selectedResourceType, setSelectedResourceType] = React.useState('');
  const [startDate, setStartDate] = React.useState('');
  const [endDate, setEndDate] = React.useState('');
  const [cursor, setCursor] = React.useState<string | null>(null);

  // Debounce actor input 300ms
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedActorId(actorInput.trim());
      setCursor(null); // reset pagination on filter change
    }, 300);
    return () => clearTimeout(timer);
  }, [actorInput]);

  // Reset cursor when other filters change
  React.useEffect(() => {
    setCursor(null);
  }, [selectedActorType, selectedAction, selectedResourceType, startDate, endDate]);

  const filters: AuditFilters = {
    ...(debouncedActorId ? { actor_id: debouncedActorId } : {}),
    ...(selectedActorType ? { actor_type: selectedActorType } : {}),
    ...(selectedAction ? { action: selectedAction } : {}),
    ...(selectedResourceType ? { resource_type: selectedResourceType } : {}),
    ...(startDate ? { start_date: startDate } : {}),
    ...(endDate ? { end_date: endDate } : {}),
  };

  const { data, isLoading, error, isFetching } = useAuditLog(workspaceSlug, filters, cursor);
  const { triggerExport, isExporting } = useExportAuditLog(workspaceSlug);
  const rollbackMutation = useRollbackAIArtifact(workspaceSlug);

  const [exportFormat, setExportFormat] = React.useState<'json' | 'csv' | null>(null);
  const [showExportWarning, setShowExportWarning] = React.useState(false);

  const [expandedRowIds, setExpandedRowIds] = React.useState<Set<string>>(new Set());

  const toggleRow = (id: string) => {
    setExpandedRowIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleExportClick = (format: 'json' | 'csv') => {
    const totalCount = data?.items.length ?? 0;
    if (totalCount > EXPORT_WARNING_THRESHOLD) {
      setExportFormat(format);
      setShowExportWarning(true);
    } else {
      void doExport(format);
    }
  };

  const doExport = async (format: 'json' | 'csv') => {
    try {
      await triggerExport(format, filters);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Export failed';
      toast.error(msg);
    }
  };

  const handleExportConfirm = async () => {
    setShowExportWarning(false);
    if (exportFormat) {
      await doExport(exportFormat);
      setExportFormat(null);
    }
  };

  const entries = data?.items ?? [];
  const totalCount = entries.length;
  const nextCursor = data?.nextCursor ?? null;

  return (
    <div className="max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Audit Log</h1>
          <p className="text-sm text-muted-foreground">
            Read-only record of all actions in this workspace. Audit records cannot be modified or
            deleted.
          </p>
        </div>

        {/* Filter Bar */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
              {/* Actor search */}
              <div className="space-y-1.5">
                <Label htmlFor="actor-search" className="text-xs">
                  Actor ID
                </Label>
                <Input
                  id="actor-search"
                  placeholder="Filter by actor…"
                  value={actorInput}
                  onChange={(e) => setActorInput(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>

              {/* Action filter */}
              <div className="space-y-1.5">
                <Label htmlFor="action-select" className="text-xs">
                  Action
                </Label>
                <Select
                  value={selectedAction}
                  onValueChange={(v) => setSelectedAction(v === '' ? '' : v)}
                >
                  <SelectTrigger id="action-select" aria-label="Action" className="h-8 text-sm">
                    <SelectValue placeholder="All Actions" />
                  </SelectTrigger>
                  <SelectContent>
                    {ACTION_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value === '' ? '_all_' : opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Resource Type filter */}
              <div className="space-y-1.5">
                <Label htmlFor="resource-type-select" className="text-xs">
                  Resource Type
                </Label>
                <Select
                  value={selectedResourceType}
                  onValueChange={(v) => setSelectedResourceType(v === '' ? '' : v)}
                >
                  <SelectTrigger
                    id="resource-type-select"
                    aria-label="Resource Type"
                    className="h-8 text-sm"
                  >
                    <SelectValue placeholder="All Types" />
                  </SelectTrigger>
                  <SelectContent>
                    {RESOURCE_TYPE_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value === '' ? '_all_' : opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Actor Type filter */}
              <div className="space-y-1.5">
                <Label htmlFor="actor-type-select" className="text-xs">
                  Actor Type
                </Label>
                <Select
                  value={selectedActorType || '_all_'}
                  onValueChange={(v) =>
                    setSelectedActorType(v === '_all_' ? '' : (v as 'AI' | 'USER' | 'SYSTEM'))
                  }
                >
                  <SelectTrigger
                    id="actor-type-select"
                    aria-label="Actor Type"
                    className="h-8 text-sm"
                  >
                    <SelectValue placeholder="All types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_all_">All types</SelectItem>
                    <SelectItem value="USER">User</SelectItem>
                    <SelectItem value="AI">AI</SelectItem>
                    <SelectItem value="SYSTEM">System</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Start Date */}
              <div className="space-y-1.5">
                <Label htmlFor="start-date" className="text-xs">
                  Start Date
                </Label>
                <Input
                  id="start-date"
                  type="date"
                  aria-label="Start Date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>

              {/* End Date */}
              <div className="space-y-1.5">
                <Label htmlFor="end-date" className="text-xs">
                  End Date
                </Label>
                <Input
                  id="end-date"
                  type="date"
                  aria-label="End Date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Export + Count Bar */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {isLoading ? (
              <Skeleton data-testid="skeleton" className="inline-block h-4 w-32" />
            ) : (
              <>
                {totalCount.toLocaleString()} {totalCount === 1 ? 'entry' : 'entries'}
              </>
            )}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExportClick('json')}
              disabled={isExporting || isLoading}
              aria-label="Export JSON"
            >
              {isExporting ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" aria-hidden />
              ) : (
                <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
              )}
              Export JSON
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExportClick('csv')}
              disabled={isExporting || isLoading}
              aria-label="Export CSV"
            >
              {isExporting ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" aria-hidden />
              ) : (
                <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
              )}
              Export CSV
            </Button>
          </div>
        </div>

        {/* Audit Table */}
        <Card>
          <CardContent className="p-0">
            {error ? (
              <div className="p-6">
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Failed to load audit log</AlertTitle>
                  <AlertDescription>
                    {error instanceof Error ? error.message : 'An error occurred.'}
                  </AlertDescription>
                </Alert>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8" />
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Actor</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Resource Type</TableHead>
                    <TableHead>Resource ID</TableHead>
                    <TableHead>IP Address</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading ? (
                    <AuditSkeletonRows />
                  ) : entries.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                        No audit log entries found.
                      </TableCell>
                    </TableRow>
                  ) : (
                    entries.map((entry) => {
                      const isExpanded = expandedRowIds.has(entry.id);
                      const isRollbackEligible =
                        entry.actorType === 'AI' &&
                        (entry.resourceType === 'issue' || entry.resourceType === 'note') &&
                        (entry.action.endsWith('.create') || entry.action.endsWith('.update'));
                      const handleRollback = isRollbackEligible
                        ? () =>
                            rollbackMutation.mutate(entry.id, {
                              onSuccess: () => toast.success('Rolled back successfully'),
                              onError: (err) =>
                                toast.error(err instanceof Error ? err.message : 'Rollback failed'),
                            })
                        : undefined;
                      return (
                        <React.Fragment key={entry.id}>
                          <TableRow
                            className="cursor-pointer hover:bg-muted/50 select-none"
                            onClick={() => toggleRow(entry.id)}
                            aria-expanded={isExpanded}
                          >
                            {/* Expand chevron */}
                            <TableCell className="w-8 pr-0">
                              {isExpanded ? (
                                <ChevronDown
                                  className="h-3.5 w-3.5 text-muted-foreground"
                                  aria-hidden
                                />
                              ) : (
                                <ChevronRight
                                  className="h-3.5 w-3.5 text-muted-foreground"
                                  aria-hidden
                                />
                              )}
                            </TableCell>

                            {/* Timestamp */}
                            <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                              {formatTimestamp(entry.createdAt)}
                            </TableCell>

                            {/* Actor */}
                            <TableCell>
                              <div className="flex items-center gap-1.5">
                                {entry.actorId ? (
                                  <span className="text-xs">
                                    {actorNameMap.get(entry.actorId) ?? truncate(entry.actorId, 8)}
                                  </span>
                                ) : (
                                  <span className="text-xs text-muted-foreground">—</span>
                                )}
                                <ActorTypeBadge actorType={entry.actorType} />
                              </div>
                            </TableCell>

                            {/* Action */}
                            <TableCell>
                              <span className="text-sm">{formatAction(entry.action)}</span>
                            </TableCell>

                            {/* Resource Type */}
                            <TableCell>
                              <span className="text-sm">
                                {formatResourceType(entry.resourceType)}
                              </span>
                            </TableCell>

                            {/* Resource ID (first 8 chars) */}
                            <TableCell>
                              <span className="font-mono text-xs text-muted-foreground">
                                {truncate(entry.resourceId, 8)}
                              </span>
                            </TableCell>

                            {/* IP Address */}
                            <TableCell>
                              <span className="font-mono text-xs text-muted-foreground">
                                {entry.ipAddress ?? '—'}
                              </span>
                            </TableCell>
                          </TableRow>

                          {/* Expanded row */}
                          {isExpanded && (
                            <TableRow>
                              <TableCell colSpan={7} className="p-0">
                                <ExpandedRowContent
                                  entry={entry}
                                  workspaceSlug={workspaceSlug}
                                  onRollback={handleRollback}
                                  isRollingBack={
                                    rollbackMutation.isPending &&
                                    rollbackMutation.variables === entry.id
                                  }
                                />
                              </TableCell>
                            </TableRow>
                          )}
                        </React.Fragment>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Load More */}
        {nextCursor && (
          <div className="flex justify-center">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCursor(nextCursor)}
              disabled={isFetching}
            >
              {isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden /> : null}
              Load more
            </Button>
          </div>
        )}

        {/* Retention note (AUDIT-05: no UI config in this phase) */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Retention Policy</CardTitle>
            <CardDescription>
              Audit log retention is configured via the API (PATCH
              /workspaces/&#123;slug&#125;/audit/retention). Default retention: 90 days. Contact
              your admin to change the retention window.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* Export Warning AlertDialog (10k rows) */}
      <AlertDialog open={showExportWarning} onOpenChange={setShowExportWarning}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Large export warning</AlertDialogTitle>
            <AlertDialogDescription>
              This export contains <strong>{totalCount.toLocaleString()}</strong> rows, which
              exceeds 10,000 records. The download may take a moment. Do you want to continue?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => {
                setShowExportWarning(false);
                setExportFormat(null);
              }}
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={() => void handleExportConfirm()}>
              Download anyway
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
