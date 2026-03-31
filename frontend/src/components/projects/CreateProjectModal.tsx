'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { useCreateProject } from '@/features/projects/hooks';
import { useWorkspaceMembers } from '@/features/issues/hooks/use-workspace-members';
import type { Project } from '@/types';

interface CreateProjectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  onSuccess?: (project: Project) => void;
}

function generateIdentifier(name: string): string {
  const words = name.split(/\s+/).filter(Boolean);
  if (words.length === 0) return '';
  const initials = words.map((w) => w.charAt(0).toUpperCase()).join('');
  // For single-word names, take first 2-3 chars to meet min_length=2
  if (initials.length < 2 && words.length === 1) {
    const word = words[0]!;
    return word
      .replace(/[^A-Za-z0-9]/g, '')
      .toUpperCase()
      .slice(0, 3);
  }
  return initials.slice(0, 5);
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
  const [leadId, setLeadId] = useState<string>('');
  const [identifierManuallyEdited, setIdentifierManuallyEdited] = useState(false);

  const { data: membersData } = useWorkspaceMembers(workspaceId);
  const members = membersData?.items ?? [];

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
    setLeadId('');
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

  const isFormValid = name.trim().length > 0 && identifier.trim().length >= 2;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;

    createProject({
      name: name.trim(),
      identifier: identifier.trim(),
      description: description.trim() || undefined,
      icon: icon.trim() || undefined,
      leadId: leadId || undefined,
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
                <p className="text-[11px] text-muted-foreground">
                  Auto-generated. 2–5 uppercase chars.
                </p>
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
              <Label htmlFor="project-lead">Lead</Label>
              <Select value={leadId} onValueChange={(v) => setLeadId(v === '__none__' ? '' : v)}>
                <SelectTrigger id="project-lead">
                  <SelectValue placeholder="Select lead (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">
                    <span className="text-muted-foreground">No lead</span>
                  </SelectItem>
                  {members.map((member) => (
                    <SelectItem key={member.userId} value={member.userId}>
                      {member.fullName || member.email}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
            <Button type="submit" disabled={!isFormValid || isPending}>
              {isPending ? 'Creating...' : 'Create Project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
