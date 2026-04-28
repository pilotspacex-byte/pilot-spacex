/**
 * SkillDetailModal — View and edit a user skill in a modal dialog.
 *
 * Read mode: shows skill info, rendered markdown content, meta dates.
 * Edit mode: editable name + SkillEditor for content.
 */

'use client';

import * as React from 'react';
import { Pencil, Power, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { MarkdownContent } from '@/features/ai/ChatView/MessageList/MarkdownContent';
import type { UserSkill } from '@/services/api/user-skills';
import { SkillEditor } from './skill-editor';

interface SkillDetailModalProps {
  skill: UserSkill | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEdit: (skill: UserSkill, updates: { skill_content?: string; skill_name?: string }) => void;
  onToggleActive: (skill: UserSkill) => void;
  onDelete: (skill: UserSkill) => void;
  isSaving?: boolean;
}

export function SkillDetailModal({
  skill,
  open,
  onOpenChange,
  onEdit,
  onToggleActive,
  onDelete,
  isSaving = false,
}: SkillDetailModalProps) {
  const [editing, setEditing] = React.useState(false);
  const [editableName, setEditableName] = React.useState('');

  // Reset edit state when modal opens/closes or skill changes
  React.useEffect(() => {
    if (open && skill) {
      setEditing(false);
      setEditableName(skill.skill_name ?? skill.template_name ?? '');
    }
  }, [open, skill]);

  if (!skill) return null;

  const displayName = skill.skill_name ?? skill.template_name ?? 'Custom Skill';

  const handleSave = (content: string) => {
    const updates: { skill_content?: string; skill_name?: string } = {
      skill_content: content,
    };
    const trimmedName = editableName.trim();
    if (trimmedName && trimmedName !== displayName) {
      updates.skill_name = trimmedName;
    }
    onEdit(skill, updates);
    setEditing(false);
  };

  const handleToggle = () => {
    onToggleActive(skill);
    onOpenChange(false);
  };

  const handleDelete = () => {
    onDelete(skill);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] flex flex-col p-0 gap-0 overflow-hidden">
        {/* Header */}
        <DialogHeader className="px-6 pt-6 pb-4 border-b shrink-0">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className={`shrink-0 h-2.5 w-2.5 rounded-full ${
                  skill.is_active ? 'bg-emerald-500' : 'bg-muted-foreground/40'
                }`}
              />
              <DialogTitle className="truncate">{displayName}</DialogTitle>
              <Badge variant={skill.is_active ? 'default' : 'secondary'} className="shrink-0">
                {skill.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
            {!editing && (
              <div className="flex gap-1 shrink-0">
                <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                  <Pencil className="h-3.5 w-3.5 mr-1.5" />
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={handleToggle}
                  aria-label={skill.is_active ? 'Deactivate skill' : 'Activate skill'}
                >
                  <Power className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive hover:text-destructive"
                  onClick={handleDelete}
                  aria-label="Delete skill"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            )}
          </div>
          {skill.experience_description && !editing && (
            <p className="text-sm text-muted-foreground mt-1.5 line-clamp-2">
              {skill.experience_description}
            </p>
          )}
        </DialogHeader>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {editing ? (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="skill-detail-name">Skill Name</Label>
                <Input
                  id="skill-detail-name"
                  value={editableName}
                  onChange={(e) => setEditableName(e.target.value)}
                  placeholder="e.g. Senior Backend Developer"
                  maxLength={200}
                />
              </div>
              <SkillEditor
                initialContent={skill.skill_content}
                onSave={handleSave}
                onCancel={() => setEditing(false)}
                isSaving={isSaving}
              />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Meta info */}
              <div className="flex gap-4 text-xs text-muted-foreground">
                {skill.template_name && (
                  <span>
                    Template: <span className="text-foreground">{skill.template_name}</span>
                  </span>
                )}
                <span>
                  Created:{' '}
                  <span className="text-foreground">
                    {new Date(skill.created_at).toLocaleDateString()}
                  </span>
                </span>
                <span>
                  Updated:{' '}
                  <span className="text-foreground">
                    {new Date(skill.updated_at).toLocaleDateString()}
                  </span>
                </span>
              </div>

              {/* Rendered markdown skill content */}
              <div className="rounded-lg border bg-muted/30 p-4">
                <MarkdownContent content={skill.skill_content} />
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
