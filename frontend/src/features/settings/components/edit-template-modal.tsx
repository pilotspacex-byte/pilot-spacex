/**
 * EditTemplateModal — Admin dialog for editing workspace skill templates.
 *
 * Pre-fills form with existing template data. Built-in templates cannot be edited.
 * Source: Phase 20, P20-09
 */

'use client';

import * as React from 'react';
import { Pencil } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useUpdateSkillTemplate } from '@/services/api/skill-templates';
import type { SkillTemplate } from '@/services/api/skill-templates';

interface EditTemplateModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceSlug: string;
  template: SkillTemplate;
}

export function EditTemplateModal({
  open,
  onOpenChange,
  workspaceSlug,
  template,
}: EditTemplateModalProps) {
  const updateTemplate = useUpdateSkillTemplate(workspaceSlug);

  const [name, setName] = React.useState(template.name);
  const [description, setDescription] = React.useState(template.description);
  const [skillContent, setSkillContent] = React.useState(template.skill_content);
  const [icon, setIcon] = React.useState(template.icon);

  // Sync form when template changes
  React.useEffect(() => {
    setName(template.name);
    setDescription(template.description);
    setSkillContent(template.skill_content);
    setIcon(template.icon);
  }, [template]);

  const handleClose = React.useCallback(() => {
    onOpenChange(false);
  }, [onOpenChange]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !description.trim() || !skillContent.trim()) return;

    updateTemplate.mutate(
      {
        id: template.id,
        data: {
          name: name.trim(),
          description: description.trim(),
          skill_content: skillContent.trim(),
          icon: icon.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success('Template updated');
          handleClose();
        },
        onError: () => {
          toast.error('Failed to update template');
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Pencil className="h-5 w-5 text-primary" />
            Edit Template
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label htmlFor="edit-tpl-name">Name</Label>
            <Input
              id="edit-tpl-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Senior Backend Developer"
              maxLength={200}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="edit-tpl-description">Description</Label>
            <Input
              id="edit-tpl-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this skill template"
              maxLength={500}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="edit-tpl-content">Skill Content</Label>
            <Textarea
              id="edit-tpl-content"
              value={skillContent}
              onChange={(e) => setSkillContent(e.target.value)}
              placeholder="Write the skill instructions..."
              rows={8}
              className="resize-none font-mono text-sm"
              required
            />
            <p className="text-xs text-muted-foreground">
              {skillContent.trim().split(/\s+/).filter(Boolean).length} words
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="edit-tpl-icon">Icon (optional)</Label>
            <Input
              id="edit-tpl-icon"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              placeholder="e.g. an emoji like 🔧 or 🎯"
              maxLength={10}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={updateTemplate.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={
                !name.trim() ||
                !description.trim() ||
                !skillContent.trim() ||
                updateTemplate.isPending
              }
            >
              {updateTemplate.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
