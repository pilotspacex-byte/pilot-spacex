/**
 * RolesSettingsPage - Custom RBAC role management.
 *
 * AUTH-04, AUTH-05: List, create, edit, delete custom workspace roles.
 * Permission grid grouped by resource with manage-implies-lower logic.
 */

'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { AlertCircle, Loader2, Pencil, Plus, Trash2 } from 'lucide-react';
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
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { useStore } from '@/stores';
import { ApiError } from '@/services/api';
import {
  useCustomRoles,
  useCreateRole,
  useUpdateRole,
  useDeleteRole,
  type CustomRole,
  type CreateRoleInput,
} from '../hooks/use-custom-roles';

// ---- Permission definitions ----

const RESOURCES = [
  'issues',
  'notes',
  'cycles',
  'members',
  'settings',
  'ai',
  'integrations',
] as const;
const ACTIONS = ['read', 'write', 'delete', 'manage'] as const;

type Resource = (typeof RESOURCES)[number];
type Action = (typeof ACTIONS)[number];

/** manage implies delete, write, read */
function expandPermissions(permissions: string[]): string[] {
  const expanded = new Set(permissions);
  for (const perm of permissions) {
    const [resource, action] = perm.split(':');
    if (action === 'manage') {
      expanded.add(`${resource}:delete`);
      expanded.add(`${resource}:write`);
      expanded.add(`${resource}:read`);
    }
    if (action === 'delete') {
      expanded.add(`${resource}:write`);
      expanded.add(`${resource}:read`);
    }
    if (action === 'write') {
      expanded.add(`${resource}:read`);
    }
  }
  return [...expanded];
}

// ---- Permission Grid Component ----

interface PermissionGridProps {
  selectedPermissions: string[];
  onChange: (permissions: string[]) => void;
}

function PermissionGrid({ selectedPermissions, onChange }: PermissionGridProps) {
  const selected = new Set(selectedPermissions);

  const handleToggle = (resource: Resource, action: Action) => {
    const perm = `${resource}:${action}`;
    const next = new Set(selected);

    if (next.has(perm)) {
      next.delete(perm);
      // If removing manage, also remove implied lower ones only if manage was the sole reason
      // Simple approach: just toggle the single permission
    } else {
      next.add(perm);
    }

    onChange(expandPermissions([...next]));
  };

  return (
    <div className="space-y-3" role="group" aria-label="Permission matrix">
      <div className="grid grid-cols-5 gap-x-4 gap-y-1 text-xs font-medium text-muted-foreground">
        <span />
        {ACTIONS.map((action) => (
          <span key={action} className="text-center capitalize">
            {action}
          </span>
        ))}
      </div>
      {RESOURCES.map((resource) => (
        <div key={resource} className="grid grid-cols-5 items-center gap-x-4 gap-y-1">
          <span className="text-sm font-medium capitalize">{resource}</span>
          {ACTIONS.map((action) => {
            const perm = `${resource}:${action}`;
            const checked = selected.has(perm);
            return (
              <div key={action} className="flex justify-center">
                <Checkbox
                  id={`perm-${perm}`}
                  checked={checked}
                  onCheckedChange={() => handleToggle(resource, action)}
                  aria-label={`${resource} ${action}`}
                />
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

// ---- Role Dialog Component ----

interface RoleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editRole?: CustomRole;
  workspaceSlug: string;
}

function RoleDialog({ open, onOpenChange, editRole, workspaceSlug }: RoleDialogProps) {
  const isEdit = !!editRole;
  const createRole = useCreateRole(workspaceSlug);
  const updateRole = useUpdateRole(workspaceSlug, editRole?.id ?? '');

  const [name, setName] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [permissions, setPermissions] = React.useState<string[]>([]);
  const [nameError, setNameError] = React.useState<string | null>(null);
  const [permError, setPermError] = React.useState<string | null>(null);
  const [dupError, setDupError] = React.useState<string | null>(null);

  // Reset form when dialog opens / role changes
  React.useEffect(() => {
    if (open) {
      setName(editRole?.name ?? '');
      setDescription(editRole?.description ?? '');
      setPermissions(editRole?.permissions ?? []);
      setNameError(null);
      setPermError(null);
      setDupError(null);
    }
  }, [open, editRole]);

  const validate = (): boolean => {
    let valid = true;
    if (!name.trim()) {
      setNameError('Name is required.');
      valid = false;
    } else {
      setNameError(null);
    }
    if (permissions.length === 0) {
      setPermError('At least one permission is required.');
      valid = false;
    } else {
      setPermError(null);
    }
    return valid;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setDupError(null);

    if (!validate()) return;

    const data: CreateRoleInput = {
      name: name.trim(),
      description: description.trim() || undefined,
      permissions,
    };

    try {
      if (isEdit) {
        await updateRole.mutateAsync(data);
        toast.success(`Role "${name}" updated`);
      } else {
        await createRole.mutateAsync(data);
        toast.success(`Role "${name}" created`);
      }
      onOpenChange(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setDupError('A role with this name already exists.');
      } else {
        const msg = err instanceof ApiError ? (err.detail ?? err.message) : 'An error occurred.';
        toast.error(isEdit ? 'Failed to update role' : 'Failed to create role', {
          description: msg,
        });
      }
    }
  };

  const isPending = createRole.isPending || updateRole.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Role' : 'Create Role'}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Update the role name, description, and permissions.'
              : 'Define a new custom role for this workspace.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5 pt-2">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="role-name">Name</Label>
            <Input
              id="role-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Developer"
              disabled={isPending}
              aria-invalid={!!(nameError || dupError)}
              aria-describedby={
                nameError ? 'role-name-error' : dupError ? 'role-dup-error' : undefined
              }
            />
            {nameError && (
              <p id="role-name-error" className="text-sm text-destructive" role="alert">
                {nameError}
              </p>
            )}
            {dupError && (
              <p id="role-dup-error" className="text-sm text-destructive" role="alert">
                {dupError}
              </p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="role-description">Description (optional)</Label>
            <Textarea
              id="role-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this role can do"
              disabled={isPending}
              rows={2}
            />
          </div>

          {/* Permissions Grid */}
          <div className="space-y-2">
            <Label>Permissions</Label>
            <p className="text-xs text-muted-foreground">
              &ldquo;manage&rdquo; implies delete, write, and read for that resource.
            </p>
            <div className="rounded-lg border border-border p-4">
              <PermissionGrid selectedPermissions={permissions} onChange={setPermissions} />
            </div>
            {permError && (
              <p className="text-sm text-destructive" role="alert">
                {permError}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending} aria-busy={isPending}>
              {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
              {isPending ? 'Saving...' : isEdit ? 'Save Changes' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---- Permission Badges ----

function PermissionBadges({ permissions }: { permissions: string[] }) {
  const MAX_VISIBLE = 5;
  const visible = permissions.slice(0, MAX_VISIBLE);
  const overflow = permissions.length - MAX_VISIBLE;

  return (
    <div className="flex flex-wrap gap-1">
      {visible.map((perm) => (
        <Badge key={perm} variant="outline" className="font-mono text-xs">
          {perm}
        </Badge>
      ))}
      {overflow > 0 && (
        <Badge variant="secondary" className="text-xs">
          +{overflow} more
        </Badge>
      )}
    </div>
  );
}

// ---- Main Page ----

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-96" />
      </div>
      <Skeleton className="h-[300px] w-full" />
    </div>
  );
}

export function RolesSettingsPage() {
  const { workspaceStore } = useStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const isAdmin = workspaceStore.isAdmin;

  const { data: roles, isLoading, error } = useCustomRoles(workspaceSlug);
  const deleteRole = useDeleteRole(workspaceSlug);

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingRole, setEditingRole] = React.useState<CustomRole | undefined>(undefined);
  const [deletingRole, setDeletingRole] = React.useState<CustomRole | undefined>(undefined);

  const handleEdit = (role: CustomRole) => {
    setEditingRole(role);
    setDialogOpen(true);
  };

  const handleCreate = () => {
    setEditingRole(undefined);
    setDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deletingRole) return;
    try {
      await deleteRole.mutateAsync(deletingRole.id);
      toast.success(`Role "${deletingRole.name}" deleted`);
    } catch {
      toast.error('Failed to delete role');
    } finally {
      setDeletingRole(undefined);
    }
  };

  // Admin-only guard
  if (!isAdmin) {
    return (
      <div className="max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="space-y-1 mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">Custom Roles</h1>
          <p className="text-sm text-muted-foreground">
            Define custom permission sets for workspace members.
          </p>
        </div>
        <Alert className="border-amber-500/30 bg-amber-50 text-amber-800">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Access restricted</AlertTitle>
          <AlertDescription>
            Only workspace admins and owners can manage custom roles. Contact your workspace admin
            to manage custom roles.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load roles</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : 'An error occurred.'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header row */}
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Custom Roles</h1>
            <p className="text-sm text-muted-foreground">
              Define custom permission sets for workspace members.
            </p>
          </div>
          <Button onClick={handleCreate} aria-label="Create Role">
            <Plus className="mr-1.5 h-4 w-4" />
            Create Role
          </Button>
        </div>

        {/* Roles Table */}
        <Card>
          <CardHeader>
            <CardTitle>Roles</CardTitle>
            <CardDescription>
              {roles && roles.length > 0
                ? `${roles.length} custom role${roles.length === 1 ? '' : 's'} defined`
                : 'No custom roles defined yet.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {!roles || roles.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                <p className="text-sm font-medium text-muted-foreground">No custom roles yet.</p>
                <p className="text-sm text-muted-foreground">
                  Create your first role to get started.
                </p>
                <Button variant="outline" size="sm" onClick={handleCreate}>
                  <Plus className="mr-1.5 h-3.5 w-3.5" />
                  Create Role
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="hidden sm:table-cell">Description</TableHead>
                    <TableHead>Permissions</TableHead>
                    <TableHead className="w-[120px] text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {roles.map((role) => (
                    <TableRow key={role.id}>
                      <TableCell className="font-medium">{role.name}</TableCell>
                      <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                        {role.description ?? <span className="italic">No description</span>}
                      </TableCell>
                      <TableCell>
                        <PermissionBadges permissions={role.permissions} />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={() => handleEdit(role)}
                            aria-label={`Edit ${role.name}`}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                            <span className="sr-only">Edit</span>
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                            onClick={() => setDeletingRole(role)}
                            aria-label={`Delete ${role.name}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            <span className="sr-only">Delete</span>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create / Edit Dialog */}
      <RoleDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editRole={editingRole}
        workspaceSlug={workspaceSlug}
      />

      {/* Delete Confirmation */}
      <AlertDialog
        open={!!deletingRole}
        onOpenChange={(open) => {
          if (!open) setDeletingRole(undefined);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete role &ldquo;{deletingRole?.name}&rdquo;?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. Members using this role will revert to their built-in
              role.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleDeleteConfirm}
              disabled={deleteRole.isPending}
            >
              {deleteRole.isPending ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
