/**
 * InviteMemberDialog - Dialog for inviting new workspace members.
 *
 * T024: Email input, role select, submit via WorkspaceStore.inviteMember.
 * Handles 409 conflict for already-invited/existing members.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useStore } from '@/stores';
import type { WorkspaceRole } from '@/stores/WorkspaceStore';
import { workspaceMembersKeys } from '@/features/issues/hooks/use-workspace-members';
import { workspaceInvitationsKeys } from '../hooks/use-workspace-invitations';
import { useQueryClient } from '@tanstack/react-query';

interface InviteMemberDialogProps {
  workspaceId: string;
  children?: React.ReactNode;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const InviteMemberDialog = observer(function InviteMemberDialog({
  workspaceId,
  children,
}: InviteMemberDialogProps) {
  const { workspaceStore } = useStore();
  const queryClient = useQueryClient();

  const [open, setOpen] = React.useState(false);
  const [email, setEmail] = React.useState('');
  const [role, setRole] = React.useState<WorkspaceRole>('member');
  const [emailError, setEmailError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const resetForm = () => {
    setEmail('');
    setRole('member');
    setEmailError(null);
  };

  const validateEmail = (value: string): boolean => {
    if (!value.trim()) {
      setEmailError('Email is required.');
      return false;
    }
    if (!EMAIL_REGEX.test(value)) {
      setEmailError('Please enter a valid email address.');
      return false;
    }
    setEmailError(null);
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateEmail(email)) return;

    setIsSubmitting(true);

    const result = await workspaceStore.inviteMember(workspaceId, { email: email.trim(), role });

    setIsSubmitting(false);

    if (result) {
      toast.success('Invitation sent', {
        description: `An invitation has been sent to ${email.trim()}.`,
      });
      queryClient.invalidateQueries({ queryKey: workspaceMembersKeys.all(workspaceId) });
      queryClient.invalidateQueries({ queryKey: workspaceInvitationsKeys.all(workspaceId) });
      resetForm();
      setOpen(false);
    } else {
      const errorMsg = workspaceStore.error ?? 'Failed to send invitation.';
      if (errorMsg.toLowerCase().includes('already') || errorMsg.includes('409')) {
        setEmailError('This email has already been invited or is an existing member.');
      } else {
        toast.error('Invitation failed', { description: errorMsg });
      }
    }
  };

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) {
      resetForm();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        {children ?? (
          <Button>
            <UserPlus className="mr-2 h-4 w-4" />
            Invite Member
          </Button>
        )}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invite Member</DialogTitle>
          <DialogDescription>
            Send an invitation to join this workspace. They will receive an email with instructions.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email */}
          <div className="space-y-2">
            <Label htmlFor="invite-email">Email Address</Label>
            <Input
              id="invite-email"
              type="email"
              placeholder="colleague@company.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (emailError) setEmailError(null);
              }}
              disabled={isSubmitting}
              aria-invalid={!!emailError}
              aria-describedby={emailError ? 'invite-email-error' : undefined}
              autoFocus
            />
            {emailError && (
              <p id="invite-email-error" className="text-sm text-destructive" role="alert">
                {emailError}
              </p>
            )}
          </div>

          {/* Role */}
          <div className="space-y-2">
            <Label htmlFor="invite-role">Role</Label>
            <Select
              value={role}
              onValueChange={(value) => setRole(value as WorkspaceRole)}
              disabled={isSubmitting}
            >
              <SelectTrigger id="invite-role" aria-label="Select role for new member">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="member">Member</SelectItem>
                <SelectItem value="guest">Guest</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              {role === 'admin' &&
                'Admins can manage members, settings, and all workspace content.'}
              {role === 'member' && 'Members can create and edit issues, notes, and projects.'}
              {role === 'guest' && 'Guests have read-only access to shared content.'}
            </p>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} aria-busy={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
              {isSubmitting ? 'Sending...' : 'Send Invitation'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
});
