'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { useCreateProject } from '@/features/projects/hooks';
import type { Project } from '@/types';

interface CreateProjectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  onSuccess?: (project: Project) => void;
}

function generateIdentifier(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase())
    .join('')
    .slice(0, 5);
}

export function CreateProjectModal({
  open,
  onOpenChange,
  workspaceId,
  onSuccess,
}: CreateProjectModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [icon, setIcon] = useState('');
  const [identifierManuallyEdited, setIdentifierManuallyEdited] = useState(false);

  const { mutate: createProject, isPending } = useCreateProject({
    workspaceId,
    onSuccess: (project) => {
      resetForm();
      onOpenChange(false);
      onSuccess?.(project);
    },
  });

  const resetForm = useCallback(() => {
    setName('');
    setDescription('');
    setIdentifier('');
    setIcon('');
    setIdentifierManuallyEdited(false);
  }, []);

  useEffect(() => {
    if (!open) resetForm();
  }, [open, resetForm]);

  const handleNameChange = (value: string) => {
    setName(value);
    if (!identifierManuallyEdited) {
      setIdentifier(generateIdentifier(value));
    }
  };

  const handleIdentifierChange = (value: string) => {
    setIdentifier(
      value
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, '')
        .slice(0, 5)
    );
    setIdentifierManuallyEdited(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !identifier.trim()) return;

    createProject({
      name: name.trim(),
      identifier: identifier.trim(),
      description: description.trim() || undefined,
      icon: icon.trim() || undefined,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create Project</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="project-name">
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="project-name"
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="e.g., Authentication Service"
                autoFocus
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="project-identifier">Identifier</Label>
                <Input
                  id="project-identifier"
                  value={identifier}
                  onChange={(e) => handleIdentifierChange(e.target.value)}
                  placeholder="AUTH"
                  className="font-mono"
                  maxLength={5}
                />
                <p className="text-[11px] text-muted-foreground">Auto-generated. Max 5 chars.</p>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="project-icon">Icon</Label>
                <Input
                  id="project-icon"
                  value={icon}
                  onChange={(e) => setIcon(e.target.value)}
                  placeholder="🚀"
                  maxLength={4}
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="project-description">Description</Label>
              <Textarea
                id="project-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this project about?"
                rows={3}
              />
            </div>
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
            <Button type="submit" disabled={!name.trim() || !identifier.trim() || isPending}>
              {isPending ? 'Creating...' : 'Create Project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
