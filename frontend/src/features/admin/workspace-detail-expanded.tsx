'use client';

/**
 * WorkspaceDetailExpanded — Expanded row detail panel for a single workspace.
 *
 * Shows top 5 members, last 10 AI actions, and quota config.
 * Plain React component — no MobX, no observer().
 */

import { AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useAdminWorkspaceDetail } from './hooks/use-admin-workspaces';

interface WorkspaceDetailExpandedProps {
  token: string;
  slug: string;
}

function formatDate(isoString: string): string {
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(isoString));
  } catch {
    return isoString;
  }
}

export function WorkspaceDetailExpanded({ token, slug }: WorkspaceDetailExpandedProps) {
  const { data, isLoading, error } = useAdminWorkspaceDetail(token, slug);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-4 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading workspace detail...</span>
      </div>
    );
  }

  if (error) {
    const message = error instanceof Error ? error.message : 'Failed to load workspace detail';
    return (
      <Alert variant="destructive" className="my-2">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{message}</AlertDescription>
      </Alert>
    );
  }

  if (!data) return null;

  const { top_members, recent_ai_actions, quota_config } = data;

  return (
    <div className="grid grid-cols-1 gap-6 py-4 lg:grid-cols-3">
      {/* Top 5 Members */}
      <div className="lg:col-span-1">
        <h4 className="mb-2 text-sm font-semibold text-foreground">Top Members (by activity)</h4>
        {top_members.length === 0 ? (
          <p className="text-sm text-muted-foreground">No member activity recorded.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Email</TableHead>
                <TableHead className="text-right text-xs">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {top_members.map((member) => (
                <TableRow key={member.user_id}>
                  <TableCell className="text-xs">{member.email}</TableCell>
                  <TableCell className="text-right text-xs">{member.action_count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Last 10 AI Actions */}
      <div className="lg:col-span-1">
        <h4 className="mb-2 text-sm font-semibold text-foreground">Recent AI Actions</h4>
        {recent_ai_actions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No AI actions recorded.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Actor</TableHead>
                <TableHead className="text-xs">Action</TableHead>
                <TableHead className="text-xs">Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent_ai_actions.map((action, index) => (
                <TableRow key={index}>
                  <TableCell className="max-w-[100px] truncate text-xs">{action.actor}</TableCell>
                  <TableCell className="max-w-[100px] truncate text-xs">{action.action}</TableCell>
                  <TableCell className="text-xs">{formatDate(action.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Quota Config */}
      <div className="lg:col-span-1">
        <h4 className="mb-2 text-sm font-semibold text-foreground">Quota Configuration</h4>
        <dl className="space-y-2">
          <div className="flex justify-between text-sm">
            <dt className="text-muted-foreground">Standard RPM limit</dt>
            <dd className="font-medium">{quota_config.rate_limit_standard_rpm ?? 'Default'}</dd>
          </div>
          <div className="flex justify-between text-sm">
            <dt className="text-muted-foreground">AI RPM limit</dt>
            <dd className="font-medium">{quota_config.rate_limit_ai_rpm ?? 'Default'}</dd>
          </div>
          <div className="flex justify-between text-sm">
            <dt className="text-muted-foreground">Storage quota</dt>
            <dd className="font-medium">
              {quota_config.storage_quota_mb != null
                ? `${quota_config.storage_quota_mb} MB`
                : 'Default'}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
