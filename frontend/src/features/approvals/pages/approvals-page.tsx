/**
 * ApprovalsPage — AI approval request queue for workspace Owners/Admins.
 *
 * AIGOV-01: Human-in-the-loop review of AI action requests per DD-003.
 *
 * Features:
 * - Pending / Expired tabs
 * - Table with expandable rows per approval request
 * - Empty states with clear messaging
 * - Skeleton loading state
 *
 * Plain React component — NOT observer().
 * Data fetching via TanStack Query (useApprovals, useResolveApproval).
 */

'use client';

import { useParams } from 'next/navigation';
import { ShieldCheck, Inbox } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useWorkspaceStore } from '@/stores/RootStore';
import { useApprovals, useResolveApproval } from '../hooks/use-approvals';
import { ApprovalRow } from '../components/approval-row';
import type { ApprovalStatus } from '@/types';

// ---- Skeleton ----

function ApprovalSkeletonRows() {
  return (
    <>
      {[1, 2, 3].map((i) => (
        <TableRow key={i}>
          {[32, 120, 200, 80, 80, 80, 120].map((w, j) => (
            <TableCell key={j}>
              <Skeleton className={`h-4 w-[${w}px]`} />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

// ---- Table Shell ----

interface ApprovalTableProps {
  workspaceId: string;
  status: ApprovalStatus;
}

function ApprovalTable({ workspaceId, status }: ApprovalTableProps) {
  const { data, isLoading, error } = useApprovals(workspaceId, status);
  const resolveMutation = useResolveApproval(workspaceId);

  const items = data?.items ?? [];

  return (
    <Card>
      <CardContent className="p-0">
        {error ? (
          <div className="p-6 text-sm text-destructive">
            Failed to load approvals:{' '}
            {error instanceof Error ? error.message : 'An error occurred.'}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>Action Type</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Urgency</TableHead>
                <TableHead>Requested By</TableHead>
                <TableHead>Time</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <ApprovalSkeletonRows />
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-12 text-center">
                    <div className="flex flex-col items-center gap-2 text-muted-foreground">
                      <Inbox className="h-8 w-8" aria-hidden />
                      <p className="text-sm font-medium">
                        {status === 'pending'
                          ? 'No pending approvals'
                          : 'No expired approval requests'}
                      </p>
                      {status === 'pending' && (
                        <p className="text-xs">
                          AI-initiated actions requiring review will appear here.
                        </p>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                items.map((approval) => (
                  <ApprovalRow
                    key={approval.id}
                    approval={approval}
                    resolveMutation={resolveMutation}
                  />
                ))
              )}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

// ---- Main Component ----

export function ApprovalsPage() {
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const workspaceStore = useWorkspaceStore();

  // Resolve workspace UUID from slug — the approvals API requires an id-like value.
  // The approvalsApi ignores the workspaceId param (backend uses JWT context), but
  // we still need it as a React Query key discriminator.
  const workspaceId =
    workspaceStore.getWorkspaceBySlug(workspaceSlug)?.id ??
    workspaceStore.currentWorkspaceId ??
    workspaceSlug;

  const { data: pendingData } = useApprovals(workspaceId, 'pending');
  const pendingCount = pendingData?.pending_count ?? pendingData?.items.length ?? 0;

  return (
    <div className="max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted shrink-0">
            <ShieldCheck className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">Approvals</h1>
              {pendingCount > 0 && (
                <Badge variant="default" className="text-xs" data-testid="pending-count-badge">
                  {pendingCount}
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              Review AI-initiated actions that require human approval per workspace policy.
            </p>
          </div>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="pending">
          <TabsList>
            <TabsTrigger value="pending" data-testid="tab-pending">
              Pending
              {pendingCount > 0 && (
                <Badge variant="secondary" className="ml-1.5 text-xs px-1.5 py-0">
                  {pendingCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="expired" data-testid="tab-expired">
              Expired
            </TabsTrigger>
          </TabsList>

          <TabsContent value="pending" className="mt-4">
            <ApprovalTable workspaceId={workspaceId} status="pending" />
          </TabsContent>

          <TabsContent value="expired" className="mt-4">
            <ApprovalTable workspaceId={workspaceId} status="expired" />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
