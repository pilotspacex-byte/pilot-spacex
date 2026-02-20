'use client';

import { useState, useReducer, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { AlertTriangle } from 'lucide-react';
import { useProject, useUpdateProject, useDeleteProject } from '@/features/projects/hooks';
import { useWorkspaceStore } from '@/stores/RootStore';

interface FormState {
  name: string;
  identifier: string;
  description: string;
  icon: string;
}

type FormAction =
  | { type: 'SET_NAME'; value: string }
  | { type: 'SET_IDENTIFIER'; value: string }
  | { type: 'SET_DESCRIPTION'; value: string }
  | { type: 'SET_ICON'; value: string };

function formReducer(state: FormState, action: FormAction): FormState {
  switch (action.type) {
    case 'SET_NAME':
      return { ...state, name: action.value };
    case 'SET_IDENTIFIER':
      return { ...state, identifier: action.value };
    case 'SET_DESCRIPTION':
      return { ...state, description: action.value };
    case 'SET_ICON':
      return { ...state, icon: action.value };
  }
}

function initForm(
  project: { name: string; identifier: string; description?: string; icon?: string } | undefined
): FormState {
  return {
    name: project?.name ?? '',
    identifier: project?.identifier ?? '',
    description: project?.description ?? '',
    icon: project?.icon ?? '',
  };
}

export default function ProjectSettingsPage() {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();
  const router = useRouter();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspaceId ?? '';

  const { data: project } = useProject({ projectId: params.projectId });

  const [form, dispatch] = useReducer(formReducer, project, initForm);
  const [deleteConfirm, setDeleteConfirm] = useState('');

  const { mutate: updateProject, isPending: isUpdating } = useUpdateProject({
    workspaceId,
  });

  const { mutate: deleteProject, isPending: isDeleting } = useDeleteProject({
    workspaceId,
    onSuccess: () => {
      router.push(`/${params.workspaceSlug}/projects`);
    },
  });

  const handleReset = useCallback(() => {
    if (!project) return;
    dispatch({ type: 'SET_NAME', value: project.name });
    dispatch({ type: 'SET_IDENTIFIER', value: project.identifier });
    dispatch({ type: 'SET_DESCRIPTION', value: project.description ?? '' });
    dispatch({ type: 'SET_ICON', value: project.icon ?? '' });
  }, [project]);

  if (!project) return null;

  const handleSave = () => {
    updateProject({
      projectId: params.projectId,
      data: {
        name: form.name.trim(),
        identifier: form.identifier.trim(),
        description: form.description.trim() || undefined,
        icon: form.icon.trim() || undefined,
      },
    });
  };

  const handleDelete = () => {
    if (deleteConfirm !== project.name) return;
    deleteProject(params.projectId);
  };

  const hasChanges =
    form.name !== project.name ||
    form.identifier !== project.identifier ||
    form.description !== (project.description ?? '') ||
    form.icon !== (project.icon ?? '');

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <h2 className="text-xl font-semibold">Settings</h2>

      {/* General settings */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">General</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="settings-name">Name</Label>
            <Input
              id="settings-name"
              value={form.name}
              onChange={(e) => dispatch({ type: 'SET_NAME', value: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="settings-identifier">Identifier</Label>
              <Input
                id="settings-identifier"
                value={form.identifier}
                onChange={(e) =>
                  dispatch({
                    type: 'SET_IDENTIFIER',
                    value: e.target.value
                      .toUpperCase()
                      .replace(/[^A-Z0-9]/g, '')
                      .slice(0, 5),
                  })
                }
                className="font-mono"
                maxLength={5}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="settings-icon">Icon</Label>
              <Input
                id="settings-icon"
                value={form.icon}
                onChange={(e) => dispatch({ type: 'SET_ICON', value: e.target.value })}
                maxLength={4}
              />
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="settings-description">Description</Label>
            <Textarea
              id="settings-description"
              value={form.description}
              onChange={(e) => dispatch({ type: 'SET_DESCRIPTION', value: e.target.value })}
              rows={3}
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={handleSave} disabled={!hasChanges || isUpdating}>
              {isUpdating ? 'Saving...' : 'Save Changes'}
            </Button>
            {hasChanges && (
              <Button variant="ghost" onClick={handleReset}>
                Reset
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Danger zone */}
      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base text-destructive flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            Danger Zone
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Deleting a project is permanent and cannot be undone. All issues, cycles, and data will
            be lost.
          </p>
          <Separator />
          <div className="grid gap-2">
            <Label htmlFor="delete-confirm">
              Type <strong>{project.name}</strong> to confirm
            </Label>
            <Input
              id="delete-confirm"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              placeholder={project.name}
            />
          </div>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteConfirm !== project.name || isDeleting}
          >
            {isDeleting ? 'Deleting...' : 'Delete Project'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
