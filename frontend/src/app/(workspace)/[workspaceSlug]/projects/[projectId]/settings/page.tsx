'use client';

import { useState } from 'react';
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
import type { Project } from '@/types';

function ProjectSettingsForm({
  project,
  workspaceSlug,
}: {
  project: Project;
  workspaceSlug: string;
}) {
  const router = useRouter();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspaceId ?? '';

  const [name, setName] = useState(project.name);
  const [identifier, setIdentifier] = useState(project.identifier);
  const [description, setDescription] = useState(project.description ?? '');
  const [icon, setIcon] = useState(project.icon ?? '');
  const [deleteConfirm, setDeleteConfirm] = useState('');

  const { mutate: updateProject, isPending: isUpdating } = useUpdateProject({
    workspaceId,
  });

  const { mutate: deleteProject, isPending: isDeleting } = useDeleteProject({
    workspaceId,
    onSuccess: () => {
      router.push(`/${workspaceSlug}/projects`);
    },
  });

  const handleSave = () => {
    updateProject({
      projectId: project.id,
      data: {
        name: name.trim(),
        identifier: identifier.trim(),
        description: description.trim() || undefined,
        icon: icon.trim() || undefined,
      },
    });
  };

  const handleDelete = () => {
    if (deleteConfirm !== project.name) return;
    deleteProject(project.id);
  };

  const handleReset = () => {
    setName(project.name);
    setIdentifier(project.identifier);
    setDescription(project.description ?? '');
    setIcon(project.icon ?? '');
  };

  const hasChanges =
    name !== project.name ||
    identifier !== project.identifier ||
    description !== (project.description ?? '') ||
    icon !== (project.icon ?? '');

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
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="settings-identifier">Identifier</Label>
              <Input
                id="settings-identifier"
                value={identifier}
                onChange={(e) =>
                  setIdentifier(
                    e.target.value
                      .toUpperCase()
                      .replace(/[^A-Z0-9]/g, '')
                      .slice(0, 5)
                  )
                }
                className="font-mono"
                maxLength={5}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="settings-icon">Icon</Label>
              <Input
                id="settings-icon"
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                maxLength={4}
              />
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="settings-description">Description</Label>
            <Textarea
              id="settings-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
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

export default function ProjectSettingsPage() {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();
  const { data: project } = useProject({ projectId: params.projectId });

  if (!project) return null;

  // Key-based reset: form re-mounts with correct initial values when project data changes
  return <ProjectSettingsForm key={project.id} project={project} workspaceSlug={params.workspaceSlug} />;
}
