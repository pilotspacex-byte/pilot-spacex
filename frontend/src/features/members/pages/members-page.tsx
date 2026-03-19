/**
 * MembersPage — Workspace members management with list layout.
 *
 * Route: /[workspaceSlug]/members
 * Features: search, role filter, vertical list, invite dialog, pending invitations tab.
 * Admin-only editing, read-only for non-admins.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import { AlertCircle, Clock, Loader2, Mail, Search, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useStore } from '@/stores';
import type { WorkspaceRole } from '@/stores/WorkspaceStore';
import { useWorkspaceMembers } from '@/features/issues/hooks/use-workspace-members';
import { workspacesApi } from '@/services/api/workspaces';
import {
  useWorkspaceInvitations,
  useCancelInvitation,
} from '@/features/members/hooks/use-workspace-invitations';
import { ConfirmActionDialog } from '@/features/settings/components/confirm-action-dialog';
import { InviteMemberDialog } from '@/features/members/components/invite-member-dialog';
import { MemberCard } from '@/features/members/components/member-card';
import { ROLE_HIERARCHY } from '@/features/members/utils/member-utils';

function MembersLoadingSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full rounded-lg" />
      ))}
    </div>
  );
}

export const MembersPage = observer(function MembersPage() {
  const { authStore, workspaceStore } = useStore();
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params?.workspaceSlug as string;

  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;
  const currentUserId = authStore.user?.id ?? '';

  const isAdmin = workspaceStore.isAdmin;

  const {
    data: members,
    isLoading: membersLoading,
    error: membersError,
  } = useWorkspaceMembers(workspaceId);

  const { data: invitations, isLoading: invitationsLoading } = useWorkspaceInvitations(
    workspaceId,
    isAdmin
  );
  const cancelInvitation = useCancelInvitation(workspaceId);

  const [searchQuery, setSearchQuery] = React.useState('');
  const [roleFilter, setRoleFilter] = React.useState<string>('all');
  const [updatingMemberId, setUpdatingMemberId] = React.useState<string | null>(null);
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

  const sortedMembers = React.useMemo(() => {
    if (!members) return [];
    return [...members].sort((a, b) => {
      const roleA = ROLE_HIERARCHY[a.role] ?? 99;
      const roleB = ROLE_HIERARCHY[b.role] ?? 99;
      if (roleA !== roleB) return roleA - roleB;
      return new Date(a.joinedAt).getTime() - new Date(b.joinedAt).getTime();
    });
  }, [members]);

  const filteredMembers = React.useMemo(() => {
    let result = sortedMembers;

    if (roleFilter !== 'all') {
      result = result.filter((m) => m.role === roleFilter);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      result = result.filter(
        (m) => (m.fullName?.toLowerCase().includes(q) ?? false) || m.email.toLowerCase().includes(q)
      );
    }

    return result;
  }, [sortedMembers, roleFilter, searchQuery]);

  const adminCount = React.useMemo(() => {
    if (!sortedMembers) return 0;
    return sortedMembers.filter((m) => m.role === 'admin' || m.role === 'owner').length;
  }, [sortedMembers]);

  const pendingInvitations = React.useMemo(() => {
    if (!invitations) return [];
    return invitations.filter((inv) => inv.status === 'pending');
  }, [invitations]);

  const handleRoleChange = async (userId: string, role: WorkspaceRole) => {
    const member = members?.find((m) => m.userId === userId);
    if (!member) return;

    setUpdatingMemberId(userId);
    const result = await workspaceStore.updateMemberRole(workspaceId, userId, role);
    setUpdatingMemberId(null);

    if (result) {
      toast.success('Role updated', {
        description: `${member.fullName || member.email} is now a ${role}.`,
      });
    } else {
      toast.error('Failed to update role', {
        description: workspaceStore.error ?? 'An unexpected error occurred.',
      });
    }
  };

  const handleRemoveMember = (userId: string) => {
    const member = members?.find((m) => m.userId === userId);
    if (!member) return;

    const isLastAdminCheck =
      (member.role === 'admin' || member.role === 'owner') &&
      (members?.filter((m) => m.role === 'admin' || m.role === 'owner').length ?? 0) <= 1;
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
    const member = members?.find((m) => m.userId === userId);
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

  const handleAvailabilityChange = async (userId: string, hours: number) => {
    try {
      await workspacesApi.updateMemberAvailability(workspaceId, userId, hours);
      toast.success('Availability updated', {
        description: `Weekly available hours set to ${hours}h.`,
      });
    } catch {
      toast.error('Failed to update availability');
    }
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
      </div>

      {/* Card Grid */}
      {filteredMembers.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <Search className="h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">
            {searchQuery || roleFilter !== 'all'
              ? 'No members matching your filters.'
              : 'No members found.'}
          </p>
          {(searchQuery || roleFilter !== 'all') && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearchQuery('');
                setRoleFilter('all');
              }}
            >
              Clear filters
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-2" role="list" aria-label="Workspace members">
          {filteredMembers.map((member) => (
            <div key={member.userId} role="listitem">
              <MemberCard
                member={member}
                currentUserRole={workspaceStore.currentUserRole}
                isCurrentUser={member.userId === currentUserId}
                isLastAdmin={
                  (member.role === 'admin' || member.role === 'owner') && adminCount <= 1
                }
                onRoleChange={handleRoleChange}
                onRemove={handleRemoveMember}
                onTransferOwnership={handleTransferOwnership}
                onAvailabilityChange={handleAvailabilityChange}
                isUpdating={updatingMemberId === member.userId}
                onNavigate={handleNavigate}
              />
            </div>
          ))}
        </div>
      )}
    </>
  );

  const invitationsContent = (
    <div className="space-y-2" role="list" aria-label="Pending invitations">
      {invitationsLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : pendingInvitations.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <Mail className="h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">No pending invitations.</p>
          {isAdmin && <InviteMemberDialog workspaceId={workspaceId} />}
        </div>
      ) : (
        pendingInvitations.map((invitation) => (
          <div
            key={invitation.id}
            className="flex flex-col gap-2 rounded-lg border border-border p-3 sm:flex-row sm:items-center sm:gap-4"
            role="listitem"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
              <Mail className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{invitation.email}</p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>Invited {new Date(invitation.createdAt).toLocaleDateString()}</span>
              </div>
            </div>
            <Badge variant="outline" className="capitalize">
              {invitation.role}
            </Badge>
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
          </div>
        ))
      )}
    </div>
  );

  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">Members</h1>
              <Badge variant="secondary">{members?.length ?? 0}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {isAdmin
                ? 'Manage workspace members, roles, and invitations.'
                : 'View workspace members and their roles.'}
            </p>
          </div>
          {isAdmin && <InviteMemberDialog workspaceId={workspaceId} />}
        </div>

        {/* Content: Tabs for admin, plain grid for non-admin */}
        {isAdmin ? (
          <Tabs defaultValue="members">
            <TabsList>
              <TabsTrigger value="members">Members</TabsTrigger>
              <TabsTrigger value="invitations" className="gap-1.5">
                Invitations
                {pendingInvitations.length > 0 && (
                  <Badge variant="secondary" className="h-5 min-w-5 px-1 text-xs">
                    {pendingInvitations.length}
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
      </div>
    </div>
  );
});
