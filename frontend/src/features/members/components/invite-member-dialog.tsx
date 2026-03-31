/**
 * InviteMemberDialog - Dialog for inviting new workspace members.
 *
 * T024: Email input, role select, submit via WorkspaceStore.inviteMember.
 * T027: Project multi-select for member/guest roles (at least one required).
 * Handles 409 conflict for already-invited/existing members.
 */

'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
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
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { workspaceMembersKeys } from '@/features/issues/hooks/use-workspace-members';
import { selectAllProjects, useProjects } from '@/features/projects/hooks/useProjects';
import { cn } from '@/lib/utils';
import { useStore } from '@/stores';
import type { WorkspaceRole } from '@/stores/WorkspaceStore';
import { useQueryClient } from '@tanstack/react-query';
import { Check, ChevronsUpDown, Loader2, UserPlus } from 'lucide-react';
import { observer } from 'mobx-react-lite';
import * as React from 'react';
import { toast } from 'sonner';
import { workspaceInvitationsKeys } from '../hooks/use-workspace-invitations';

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
  const [projectError, setProjectError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [selectedProjectIds, setSelectedProjectIds] = React.useState<string[]>([]);
  const [projectPickerOpen, setProjectPickerOpen] = React.useState(false);

  const { data: projectsData } = useProjects({ workspaceId, enabled: open });
  const allProjects = selectAllProjects(projectsData).filter((p) => !p.is_archived);

  const showProjectPicker = role === 'member' || role === 'guest';

  const resetForm = () => {
    setEmail('');
    setRole('member');
    setEmailError(null);
    setProjectError(null);
    setSelectedProjectIds([]);
    setProjectPickerOpen(false);
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

    const emailValid = validateEmail(email);
    if (!emailValid) return;

    setIsSubmitting(true);

    await workspaceStore.inviteMember(workspaceId, {
      email: email.trim(),
      role,
      project_assignments: selectedProjectIds.map((id) => ({ project_id: id })),
    });

    setIsSubmitting(false);

    if (workspaceStore.error) {
      const errorMsg = workspaceStore.error;
      if (errorMsg === 'conflict:already_member_or_invited') {
        setEmailError('This email has already been invited or is an existing member.');
      } else {
        toast.error('Invitation failed', { description: errorMsg });
      }
      return;
    }

    // Both immediate member (result !== null) and pending invite (result === null, no error) are success
    toast.success('Invitation sent', {
      description: `An invitation has been sent to ${email.trim()}.`,
    });
    queryClient.invalidateQueries({ queryKey: workspaceMembersKeys.all(workspaceId) });
    queryClient.invalidateQueries({ queryKey: workspaceInvitationsKeys.all(workspaceId) });
    resetForm();
    setOpen(false);
  };

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) {
      resetForm();
    }
  };

  const toggleProject = (projectId: string) => {
    setSelectedProjectIds((prev) =>
      prev.includes(projectId) ? prev.filter((id) => id !== projectId) : [...prev, projectId]
    );
    if (projectError) setProjectError(null);
  };

  const selectedProjects = allProjects.filter((p) => selectedProjectIds.includes(p.id));

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
              onValueChange={(value) => {
                setRole(value as WorkspaceRole);
                if (value === 'admin') {
                  setSelectedProjectIds([]);
                  setProjectError(null);
                }
              }}
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

          {/* Project assignment — required for member/guest roles */}
          {showProjectPicker && (
            <div className="space-y-2">
              <Label>Projects</Label>
              <Popover open={projectPickerOpen} onOpenChange={setProjectPickerOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={projectPickerOpen}
                    aria-label="Select projects"
                    disabled={isSubmitting}
                    className={cn(
                      'w-full justify-between font-normal',
                      projectError && 'border-destructive'
                    )}
                  >
                    <span className="truncate">
                      {selectedProjects.length === 0
                        ? 'Select projects…'
                        : selectedProjects.map((p) => p.identifier).join(', ')}
                    </span>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search projects…" />
                    <CommandList>
                      <CommandEmpty>No projects found.</CommandEmpty>
                      <CommandGroup>
                        {allProjects.map((project) => (
                          <CommandItem
                            key={project.id}
                            value={`${project.identifier} ${project.name}`}
                            onSelect={() => toggleProject(project.id)}
                          >
                            <Check
                              className={cn(
                                'mr-2 h-4 w-4',
                                selectedProjectIds.includes(project.id)
                                  ? 'opacity-100'
                                  : 'opacity-0'
                              )}
                            />
                            <span className="font-mono text-xs text-muted-foreground mr-2">
                              {project.identifier}
                            </span>
                            {project.name}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>

              {selectedProjects.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedProjects.map((p) => (
                    <Badge key={p.id} variant="secondary" className="text-xs">
                      {p.identifier}
                    </Badge>
                  ))}
                </div>
              )}

              {projectError && (
                <p className="text-sm text-destructive" role="alert">
                  {projectError}
                </p>
              )}
              <p className="text-sm text-muted-foreground">
                Optionally assign to one or more projects.
              </p>
            </div>
          )}

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
