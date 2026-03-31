/**
 * EditAssignmentsDialog — Admin dialog to bulk-update a member's project assignments.
 *
 * T030: Shows checkboxes for each non-archived project; pre-checks current assignments.
 * Workspace role select. Soft-warning on demotion.
 * Optimistic update via TanStack mutation + invalidateQueries on save.
 *
 * A4-E09: Renamed to "Edit Permissions"; (current) label on active role;
 *   admin/owner info callout instead of checkboxes; auto-remove on → admin promotion;
 *   description text added.
 */

'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { workspaceMembersKeys } from '@/features/issues/hooks/use-workspace-members';
import { selectAllProjects, useProjects } from '@/features/projects/hooks/useProjects';
import { projectMemberKeys, useBulkUpdateAssignments } from '@/services/api/project-members';
import type { WorkspaceRole } from '@/stores/WorkspaceStore';
import { useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Check, Info, Loader2 } from 'lucide-react';
import * as React from 'react';
import { toast } from 'sonner';

interface EditAssignmentsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  userId: string;
  memberName: string;
  currentRole: WorkspaceRole;
  /** Currently assigned project IDs */
  currentProjectIds: string[];
}

export function EditAssignmentsDialog({
  open,
  onOpenChange,
  workspaceId,
  userId,
  memberName,
  currentRole,
  currentProjectIds,
}: EditAssignmentsDialogProps) {
  const queryClient = useQueryClient();
  const bulkUpdate = useBulkUpdateAssignments(workspaceId);

  const { data: projectsData } = useProjects({ workspaceId, enabled: open });
  const allProjects = selectAllProjects(projectsData).filter((p) => !p.is_archived);

  const [selectedIds, setSelectedIds] = React.useState<string[]>(currentProjectIds);
  const [role, setRole] = React.useState<WorkspaceRole>(currentRole);

  // Sync state when dialog opens (handles re-opens with fresh data)
  React.useEffect(() => {
    if (open) {
      setSelectedIds(currentProjectIds);
      setRole(currentRole);
    }
  }, [open, currentProjectIds, currentRole]);

  const isDemotion =
    (currentRole === 'admin' || currentRole === 'owner') && (role === 'member' || role === 'guest');

  // Admins/Owners have implicit access to all projects — project checkboxes don't apply
  const isAdminOrOwner = role === 'admin' || role === 'owner';

  const toggleProject = (projectId: string) => {
    setSelectedIds((prev) =>
      prev.includes(projectId) ? prev.filter((id) => id !== projectId) : [...prev, projectId]
    );
  };

  const handleSave = async () => {
    let effectiveSelectedIds = selectedIds;
    // A4-E09-e: Promoting to admin → remove all project assignments automatically
    if (role === 'admin' && (currentRole === 'member' || currentRole === 'guest')) {
      effectiveSelectedIds = [];
    }

    const addIds = effectiveSelectedIds.filter((id) => !currentProjectIds.includes(id));
    const removeIds = currentProjectIds.filter((id) => !effectiveSelectedIds.includes(id));

    const projectAssignments = [
      ...addIds.map((id) => ({ projectId: id, action: 'add' as const })),
      ...removeIds.map((id) => ({ projectId: id, action: 'remove' as const })),
    ];

    try {
      await bulkUpdate.mutateAsync({
        userId,
        payload: {
          workspaceRole: role !== currentRole ? role : undefined,
          projectAssignments,
        },
      });

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: workspaceMembersKeys.all(workspaceId) }),
        queryClient.invalidateQueries({ queryKey: projectMemberKeys.all }),
      ]);

      toast.success('Permissions updated', {
        description: `${memberName}'s permissions have been updated.`,
      });
      onOpenChange(false);
    } catch {
      toast.error('Failed to update permissions');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Permissions</DialogTitle>
          <DialogDescription>
            Manage workspace role and project access for{' '}
            <span className="font-medium">{memberName}</span>.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* A4-E09-f: Description text */}
          <p className="text-sm text-muted-foreground">
            Workspace role controls what this member can manage. Project assignments control which
            projects they can access (Members and Guests only).
          </p>

          {/* Role select — owner: non-interactive; others: all 3 options with current annotation */}
          <div className="space-y-2">
            <Label htmlFor="edit-role">Workspace Role</Label>
            {currentRole === 'owner' ? (
              <div className="flex items-center rounded-md border border-input bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
                Owner — ownership transfer is a separate action
              </div>
            ) : (
              <Select
                value={role}
                onValueChange={(v) => setRole(v as WorkspaceRole)}
                disabled={bulkUpdate.isPending}
              >
                <SelectTrigger id="edit-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(['admin', 'member', 'guest'] as const).map((r) => (
                    <SelectItem key={r} value={r}>
                      {r.charAt(0).toUpperCase() + r.slice(1)}
                      {r === currentRole ? ' (current)' : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Demotion warning */}
          {isDemotion && (
            <Alert variant="default" className="border-amber-200 bg-amber-50 text-amber-900">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <AlertDescription className="text-sm">
                Changing this member&apos;s role to <strong>{role}</strong> will reduce their
                workspace permissions. Make sure they are assigned to the correct projects.
              </AlertDescription>
            </Alert>
          )}

          {/* Project assignments — A4-E09-d: disabled for Admin/Owner */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Project Assignments</Label>
              {!isAdminOrOwner && (
                <Badge variant="secondary" className="text-xs">
                  {selectedIds.length} selected
                </Badge>
              )}
            </div>
            {isAdminOrOwner ? (
              <div className="flex items-start gap-2 rounded-md border bg-muted/30 px-3 py-2.5 text-sm text-muted-foreground">
                <Info className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Admins have access to all workspace projects automatically. Project assignments
                  apply to Members and Guests only.
                </span>
              </div>
            ) : (
              <ScrollArea className="h-48 rounded-md border">
                <div className="p-2 space-y-1">
                  {allProjects.length === 0 ? (
                    <p className="py-4 text-center text-sm text-muted-foreground">
                      No projects in this workspace.
                    </p>
                  ) : (
                    allProjects.map((project) => {
                      const checked = selectedIds.includes(project.id);
                      return (
                        <label
                          key={project.id}
                          className="flex cursor-pointer items-center gap-3 rounded px-2 py-1.5 hover:bg-accent transition-colors"
                        >
                          <Checkbox
                            checked={checked}
                            onCheckedChange={() => toggleProject(project.id)}
                            disabled={bulkUpdate.isPending}
                            aria-label={`Toggle ${project.name}`}
                          />
                          <span className="font-mono text-xs text-muted-foreground">
                            {project.identifier}
                          </span>
                          <span className="text-sm flex-1 truncate">{project.name}</span>
                          {checked && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
                        </label>
                      );
                    })
                  )}
                </div>
              </ScrollArea>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={bulkUpdate.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={bulkUpdate.isPending}
            aria-busy={bulkUpdate.isPending}
          >
            {bulkUpdate.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            )}
            {bulkUpdate.isPending ? 'Saving…' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
