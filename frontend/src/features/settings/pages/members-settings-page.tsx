/**
 * MembersSettingsPage - Workspace members management.
 *
 * T022: Member list, pending invitations, invite/remove/role-change actions.
 * Admin-only editing, read-only for non-admins.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { AlertCircle, Clock, Loader2, Mail, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useStore } from '@/stores';
import type { WorkspaceRole } from '@/stores/WorkspaceStore';
import { useWorkspaceMembers } from '@/features/issues/hooks/use-workspace-members';
import { useWorkspaceInvitations, useCancelInvitation } from '../hooks/use-workspace-invitations';
import { ConfirmActionDialog } from '../components/confirm-action-dialog';
import { MemberRow, ROLE_HIERARCHY } from '../components/member-row';
import { InviteMemberDialog } from '../components/invite-member-dialog';

function MembersLoadingSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-[72px] w-full rounded-lg" />
      ))}
    </div>
  );
}

export const MembersSettingsPage = observer(function MembersSettingsPage() {
  const { authStore, workspaceStore } = useStore();
  const params = useParams();
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

  const { data: invitations, isLoading: invitationsLoading } = useWorkspaceInvitations(workspaceId);

  const cancelInvitation = useCancelInvitation(workspaceId);

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
      return new Date(a.joined_at).getTime() - new Date(b.joined_at).getTime();
    });
  }, [members]);

  const pendingInvitations = React.useMemo(() => {
    if (!invitations) return [];
    return invitations.filter((inv) => inv.status === 'pending');
  }, [invitations]);

  const handleRoleChange = async (userId: string, role: WorkspaceRole) => {
    const member = members?.find((m) => m.user_id === userId);
    if (!member) return;

    setUpdatingMemberId(userId);
    const result = await workspaceStore.updateMemberRole(workspaceId, userId, role);
    setUpdatingMemberId(null);

    if (result) {
      toast.success('Role updated', {
        description: `${member.full_name || member.email} is now a ${role}.`,
      });
    } else {
      toast.error('Failed to update role', {
        description: workspaceStore.error ?? 'An unexpected error occurred.',
      });
    }
  };

  const handleRemoveMember = (userId: string) => {
    const member = members?.find((m) => m.user_id === userId);
    if (!member) return;

    const displayName = member.full_name || member.email;
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
    const member = members?.find((m) => m.user_id === userId);
    if (!member) return;

    const displayName = member.full_name || member.email;
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

  if (membersLoading) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
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
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
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

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Members</h1>
            <p className="text-sm text-muted-foreground">
              Manage workspace members, roles, and invitations.
            </p>
          </div>
          {isAdmin && <InviteMemberDialog workspaceId={workspaceId} />}
        </div>

        {/* Members List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Workspace Members
              <Badge variant="secondary">{members?.length ?? 0}</Badge>
            </CardTitle>
            <CardDescription>
              {isAdmin
                ? 'Manage roles and access for workspace members.'
                : 'View workspace members and their roles.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2" role="list" aria-label="Workspace members">
              {sortedMembers.map((member) => (
                <MemberRow
                  key={member.user_id}
                  member={member}
                  currentUserRole={workspaceStore.currentUserRole}
                  isCurrentUser={member.user_id === currentUserId}
                  onRoleChange={handleRoleChange}
                  onRemove={handleRemoveMember}
                  onTransferOwnership={handleTransferOwnership}
                  isUpdating={updatingMemberId === member.user_id}
                />
              ))}
              {sortedMembers.length === 0 && (
                <p className="py-8 text-center text-sm text-muted-foreground">No members found.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Pending Invitations */}
        {isAdmin && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Pending Invitations
                {pendingInvitations.length > 0 && (
                  <Badge variant="secondary">{pendingInvitations.length}</Badge>
                )}
              </CardTitle>
              <CardDescription>
                Invitations that have been sent but not yet accepted.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {invitationsLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : pendingInvitations.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  No pending invitations.
                </p>
              ) : (
                <div className="space-y-2" role="list" aria-label="Pending invitations">
                  {pendingInvitations.map((invitation) => (
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
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
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
