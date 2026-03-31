/**
 * MembersPage — Workspace members management with table layout.
 *
 * Route: /[workspaceSlug]/members
 * Features: search, role filter, table layout, pagination, invite dialog, pending invitations tab.
 * Admin-only editing, read-only for non-admins.
 *
 * E-04: Table layout for members and invitations.
 * E-05: Client-side pagination for both tabs.
 * E-06: Member count badge on Members tab trigger, not header.
 */

'use client';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  useWorkspaceMembers,
  workspaceMembersKeys,
} from '@/features/issues/hooks/use-workspace-members';
import { EditAssignmentsDialog } from '@/features/members/components/edit-assignments-dialog';
import { InviteMemberDialog } from '@/features/members/components/invite-member-dialog';
import { MemberTableRow } from '@/features/members/components/member-table-row';
import {
  useCancelInvitation,
  useWorkspaceInvitations,
} from '@/features/members/hooks/use-workspace-invitations';
import { selectAllProjects, useProjects } from '@/features/projects/hooks/useProjects';
import { ConfirmActionDialog } from '@/features/settings/components/confirm-action-dialog';
import { useStore } from '@/stores';
import type { WorkspaceRole } from '@/stores/WorkspaceStore';
import { useQueryClient } from '@tanstack/react-query';
import { AlertCircle, ChevronLeft, ChevronRight, Clock, Loader2, Mail, Search, Trash2 } from 'lucide-react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import * as React from 'react';
import { toast } from 'sonner';

function MembersLoadingSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  );
}

const ITEMS_PER_PAGE = 25;

function PaginationControls({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-end gap-2 pt-2">
      <Button
        variant="outline"
        size="sm"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        aria-label="Previous page"
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <span className="text-xs text-muted-foreground">
        {page} / {totalPages}
      </span>
      <Button
        variant="outline"
        size="sm"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        aria-label="Next page"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}

export const MembersPage = observer(function MembersPage() {
  const { authStore, workspaceStore } = useStore();
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const workspaceSlug = params?.workspaceSlug as string;

  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;

  const refreshMembers = React.useCallback(
    () => void queryClient.invalidateQueries({ queryKey: workspaceMembersKeys.all(workspaceId) }),
    [queryClient, workspaceId]
  );
  const currentUserId = authStore.user?.id ?? '';

  const isAdmin = workspaceStore.isAdmin;

  const [searchQuery, setSearchQuery] = React.useState('');
  const [roleFilter, setRoleFilter] = React.useState<string>('all');
  const [projectFilter, setProjectFilter] = React.useState<string | null>(null);
  const [membersPage, setMembersPage] = React.useState(1);
  const [invitationsPage, setInvitationsPage] = React.useState(1);
  const [debouncedSearch, setDebouncedSearch] = React.useState('');

  // Debounce search by 300ms
  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const {
    data: membersData,
    isLoading: membersLoading,
    error: membersError,
  } = useWorkspaceMembers(workspaceId, {
    projectId: projectFilter,
    search: debouncedSearch,
    role: roleFilter === 'all' ? undefined : roleFilter,
    page: membersPage,
    pageSize: ITEMS_PER_PAGE,
  });

  const { data: projectsData } = useProjects({ workspaceId, enabled: isAdmin });

  const { data: invitationsData, isLoading: invitationsLoading } = useWorkspaceInvitations(
    workspaceId,
    isAdmin,
    { page: invitationsPage, pageSize: ITEMS_PER_PAGE }
  );
  const cancelInvitation = useCancelInvitation(workspaceId);
  const [updatingMemberId, setUpdatingMemberId] = React.useState<string | null>(null);
  const [editAssignmentsTarget, setEditAssignmentsTarget] = React.useState<{
    userId: string;
    name: string;
    role: WorkspaceRole;
    projectIds: string[];
  } | null>(null);
  const [confirmDialog, setConfirmDialog] = React.useState<{
    open: boolean;
    title: string;
    description: string;
    confirmLabel: string;
    variant: 'default' | 'destructive';
    onConfirm: () => void;
  }>({
    open: false,
    title: '',
    description: '',
    confirmLabel: 'Confirm',
    variant: 'default',
    onConfirm: () => {},
  });

  const closeConfirmDialog = React.useCallback(() => {
    setConfirmDialog((prev) => ({ ...prev, open: false }));
  }, []);

  // Reset page when filters change
  React.useEffect(() => {
    setMembersPage(1);
  }, [roleFilter, debouncedSearch, projectFilter]);

  const members = React.useMemo(() => membersData?.items ?? [], [membersData?.items]);
  const membersTotalPages = Math.max(1, Math.ceil((membersData?.total ?? 0) / ITEMS_PER_PAGE));

  const adminCount = React.useMemo(
    () => members.filter((m) => m.role === 'admin' || m.role === 'owner').length,
    [members]
  );

  const invitations = invitationsData?.items ?? [];
  const invitationsTotalPages = Math.max(
    1,
    Math.ceil((invitationsData?.total ?? 0) / ITEMS_PER_PAGE)
  );

  const handleRoleChange = (userId: string, role: WorkspaceRole) => {
    const member = members.find((m) => m.userId === userId);
    if (!member) return;

    const displayName = member.fullName || member.email;
    const currentRole = member.role;

    // Skip confirmation if role hasn't changed
    if (currentRole === role) return;

    setConfirmDialog({
      open: true,
      title: 'Change member role',
      description: `Change ${displayName}'s role from ${currentRole} to ${role}?`,
      confirmLabel: 'Change Role',
      variant: 'default',
      onConfirm: async () => {
        closeConfirmDialog();
        setUpdatingMemberId(userId);
        const result = await workspaceStore.updateMemberRole(workspaceId, userId, role);
        setUpdatingMemberId(null);

        if (result) {
          refreshMembers();
          toast.success('Role updated', {
            description: `${displayName} is now a ${role}.`,
          });
        } else {
          toast.error('Failed to update role', {
            description: workspaceStore.error ?? 'An unexpected error occurred.',
          });
        }
      },
    });
  };

  const handleRemoveMember = (userId: string) => {
    const member = members.find((m) => m.userId === userId);
    if (!member) return;

    const isLastAdminCheck =
      (member.role === 'admin' || member.role === 'owner') &&
      (members.filter((m) => m.role === 'admin' || m.role === 'owner').length ?? 0) <= 1;
    if (isLastAdminCheck) {
      toast.error('Cannot remove the only admin', {
        description: 'This workspace must have at least one admin.',
      });
      return;
    }

    const displayName = member.fullName || member.email;
    setConfirmDialog({
      open: true,
      title: 'Remove member',
      description: `Remove ${displayName} from this workspace? This action cannot be undone.`,
      confirmLabel: 'Remove',
      variant: 'destructive',
      onConfirm: async () => {
        closeConfirmDialog();
        setUpdatingMemberId(userId);
        const success = await workspaceStore.removeMember(workspaceId, userId);
        setUpdatingMemberId(null);

        if (success) {
          refreshMembers();
          toast.success('Member removed', {
            description: `${displayName} has been removed from the workspace.`,
          });
        } else {
          toast.error('Failed to remove member', {
            description: workspaceStore.error ?? 'An unexpected error occurred.',
          });
        }
      },
    });
  };

  const handleCancelInvitation = (invitationId: string, email: string) => {
    setConfirmDialog({
      open: true,
      title: 'Cancel invitation',
      description: `Cancel the invitation for ${email}?`,
      confirmLabel: 'Cancel invitation',
      variant: 'default',
      onConfirm: async () => {
        closeConfirmDialog();
        try {
          await cancelInvitation.mutateAsync(invitationId);
          toast.success('Invitation cancelled', {
            description: `The invitation for ${email} has been cancelled.`,
          });
        } catch {
          toast.error('Failed to cancel invitation');
        }
      },
    });
  };

  const handleTransferOwnership = (userId: string) => {
    const member = members.find((m) => m.userId === userId);
    if (!member) return;

    const displayName = member.fullName || member.email;
    setConfirmDialog({
      open: true,
      title: 'Transfer ownership',
      description: `Transfer workspace ownership to ${displayName}? You will be demoted to admin. This action cannot be undone.`,
      confirmLabel: 'Transfer',
      variant: 'destructive',
      onConfirm: async () => {
        closeConfirmDialog();
        setUpdatingMemberId(userId);
        const result = await workspaceStore.updateMemberRole(workspaceId, userId, 'owner');
        setUpdatingMemberId(null);

        if (result) {
          refreshMembers();
          toast.success('Ownership transferred', {
            description: `${displayName} is now the workspace owner.`,
          });
        } else {
          toast.error('Failed to transfer ownership', {
            description: workspaceStore.error ?? 'An unexpected error occurred.',
          });
        }
      },
    });
  };

  const handleEditAssignments = (userId: string) => {
    const member = members.find((m) => m.userId === userId);
    if (!member) return;
    setEditAssignmentsTarget({
      userId: member.userId,
      name: member.fullName || member.email,
      role: member.role as WorkspaceRole,
      projectIds: member.projects?.map((p) => p.id) ?? [],
    });
  };

  const handleNavigate = (userId: string) => {
    router.push(`/${workspaceSlug}/members/${userId}`);
  };

  if (membersLoading) {
    return (
      <div className="px-4 py-6 sm:px-6 lg:px-8">
        <div className="space-y-6">
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-full sm:w-96" />
          </div>
          <MembersLoadingSkeleton />
        </div>
      </div>
    );
  }

  if (membersError) {
    return (
      <div className="px-4 py-6 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load members</AlertTitle>
          <AlertDescription>
            {membersError instanceof Error ? membersError.message : 'An error occurred.'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const membersContent = (
    <>
      {/* Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search members..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
            aria-label="Search members"
          />
        </div>
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-[140px]" aria-label="Filter by role">
            <SelectValue placeholder="All Roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Roles</SelectItem>
            <SelectItem value="owner">Owner</SelectItem>
            <SelectItem value="admin">Admin</SelectItem>
            <SelectItem value="member">Member</SelectItem>
            <SelectItem value="guest">Guest</SelectItem>
          </SelectContent>
        </Select>
        {isAdmin && (
          <Select
            value={projectFilter ?? 'all'}
            onValueChange={(v) => setProjectFilter(v === 'all' ? null : v)}
          >
            <SelectTrigger className="w-[160px]" aria-label="Filter by project">
              <SelectValue placeholder="All Projects" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Projects</SelectItem>
              {selectAllProjects(projectsData)
                .filter((p) => !p.is_archived)
                .map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        )}
        {projectFilter && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setProjectFilter(null)}
            aria-label="Show all members"
          >
            Show All
          </Button>
        )}
      </div>

      {/* Members Table */}
          {members.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <Search className="h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">
            {searchQuery || roleFilter !== 'all' || projectFilter
              ? 'No members matching your filters.'
              : 'No members found.'}
          </p>
          {(searchQuery || roleFilter !== 'all' || projectFilter) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearchQuery('');
                setRoleFilter('all');
                setProjectFilter(null);
              }}
            >
              Clear filters
            </Button>
          )}
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Member</TableHead>
                <TableHead className="hidden sm:table-cell">Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className="hidden md:table-cell">Projects</TableHead>
                <TableHead className="hidden sm:table-cell">Joined</TableHead>
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.map((member) => (
                <MemberTableRow
                  key={member.userId}
                  member={member}
                  currentUserRole={workspaceStore.currentUserRole}
                  isCurrentUser={member.userId === currentUserId}
                  isLastAdmin={
                    (member.role === 'admin' || member.role === 'owner') && adminCount <= 1
                  }
                  onRoleChange={handleRoleChange}
                  onRemove={handleRemoveMember}
                  onTransferOwnership={handleTransferOwnership}
                  onEditAssignments={isAdmin ? handleEditAssignments : undefined}
                  isUpdating={updatingMemberId === member.userId}
                  onNavigate={handleNavigate}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <PaginationControls
        page={membersPage}
        totalPages={membersTotalPages}
        onPageChange={setMembersPage}
      />
    </>
  );

  const invitationsContent = (
    <div className="space-y-2" aria-label="Pending invitations">
      {invitationsLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : invitations.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <Mail className="h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">No pending invitations.</p>
          {isAdmin && <InviteMemberDialog workspaceId={workspaceId} />}
        </div>
      ) : (
        <>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="hidden sm:table-cell">Invited</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {invitations.map((invitation) => (
                  <TableRow key={invitation.id}>
                    <td className="p-3 align-middle text-sm font-medium">
                      <div className="flex items-center gap-2">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted">
                          <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                        </div>
                        {invitation.email}
                      </div>
                    </td>
                    <td className="p-3 align-middle">
                      <Badge variant="outline" className="capitalize text-xs">
                        {invitation.role}
                      </Badge>
                    </td>
                    <td className="p-3 align-middle hidden sm:table-cell text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(invitation.createdAt).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="p-3 align-middle w-10 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                        onClick={() => handleCancelInvitation(invitation.id, invitation.email)}
                        disabled={cancelInvitation.isPending}
                        aria-label={`Cancel invitation for ${invitation.email}`}
                      >
                        {cancelInvitation.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    </td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <PaginationControls
            page={invitationsPage}
            totalPages={invitationsTotalPages}
            onPageChange={setInvitationsPage}
          />
        </>
      )}
    </div>
  );

  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Members</h1>
            <p className="text-sm text-muted-foreground">
              {isAdmin
                ? 'Manage workspace members, roles, and invitations.'
                : 'View workspace members and their roles.'}
            </p>
          </div>
          {isAdmin && <InviteMemberDialog workspaceId={workspaceId} />}
        </div>

        {/* Content: Tabs for admin, plain table for non-admin */}
        {isAdmin ? (
          <Tabs defaultValue="members">
            <TabsList>
              <TabsTrigger value="members" className="gap-1.5">
                Members
                {(membersData?.total ?? 0) > 0 && (
                  <Badge variant="secondary" className="h-5 min-w-5 px-1 text-xs">
                    {membersData?.total ?? 0}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="invitations" className="gap-1.5">
                Invitations
                {(invitationsData?.total ?? 0) > 0 && (
                  <Badge variant="secondary" className="h-5 min-w-5 px-1 text-xs">
                    {invitationsData?.total ?? 0}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>
            <TabsContent value="members" className="space-y-4 mt-4">
              {membersContent}
            </TabsContent>
            <TabsContent value="invitations" className="mt-4">
              {invitationsContent}
            </TabsContent>
          </Tabs>
        ) : (
          <div className="space-y-4">{membersContent}</div>
        )}

        <ConfirmActionDialog
          open={confirmDialog.open}
          onConfirm={confirmDialog.onConfirm}
          onCancel={closeConfirmDialog}
          title={confirmDialog.title}
          description={confirmDialog.description}
          confirmLabel={confirmDialog.confirmLabel}
          variant={confirmDialog.variant}
        />

        {editAssignmentsTarget && (
          <EditAssignmentsDialog
            open={!!editAssignmentsTarget}
            onOpenChange={(open) => {
              if (!open) setEditAssignmentsTarget(null);
            }}
            workspaceId={workspaceId}
            userId={editAssignmentsTarget.userId}
            memberName={editAssignmentsTarget.name}
            currentRole={editAssignmentsTarget.role}
            currentProjectIds={editAssignmentsTarget.projectIds}
          />
        )}
      </div>
    </div>
  );
});
