/**
 * SkillCard - Display and manage a single role skill in settings.
 *
 * T038: Role skill card with view/edit modes, action buttons.
 * Source: FR-009, FR-010, FR-015, US6
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { ChevronDown, ChevronUp, Pencil, RotateCcw, Sparkles, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { getRoleIcon } from '@/components/role-skill/role-icons';
import { useRoleSkillStore } from '@/stores/RootStore';
import { SkillEditor } from './skill-editor';
import { WordCountBar } from './word-count-bar';
import type { RoleSkill } from '@/services/api/role-skills';

interface SkillCardProps {
  skill: RoleSkill;
  onEdit: (skillId: string, content: string) => void;
  onRegenerate: (skillId: string) => void;
  onReset: (skillId: string) => void;
  onRemove: (skillId: string) => void;
  isSaving?: boolean;
}

const COLLAPSED_HEIGHT = 200;

export const SkillCard = observer(function SkillCard({
  skill,
  onEdit,
  onRegenerate,
  onReset,
  onRemove,
  isSaving = false,
}: SkillCardProps) {
  const roleSkillStore = useRoleSkillStore();
  const isEditing = roleSkillStore.editingSkillId === skill.id;
  const [isExpanded, setIsExpanded] = React.useState(false);
  const contentRef = React.useRef<HTMLDivElement>(null);
  const [needsExpand, setNeedsExpand] = React.useState(false);

  const IconComponent = getRoleIcon(skill.roleType);

  React.useEffect(() => {
    if (contentRef.current) {
      setNeedsExpand(contentRef.current.scrollHeight > COLLAPSED_HEIGHT);
    }
  }, [skill.skillContent]);

  const handleStartEdit = () => {
    roleSkillStore.setEditingSkillId(skill.id);
  };

  const handleCancelEdit = () => {
    roleSkillStore.clearEditingSkillId();
  };

  const handleSave = (content: string) => {
    onEdit(skill.id, content);
  };

  return (
    <article
      className={cn(
        'rounded-lg border transition-shadow',
        skill.isPrimary ? 'border-2 border-primary bg-primary/5' : 'border-border bg-card'
      )}
      aria-label={`${skill.roleName} role skill`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 pb-3">
        <div className="flex items-center gap-3">
          {React.createElement(IconComponent, {
            className: 'h-5 w-5 text-muted-foreground',
          })}
          <div>
            <h3 className="text-base font-semibold">{skill.roleName}</h3>
            <p className="text-xs text-muted-foreground">{skill.roleType.replace(/_/g, ' ')}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {skill.isPrimary && (
            <span className="rounded-sm bg-primary px-2 py-0.5 text-xs font-semibold text-white">
              PRIMARY
            </span>
          )}
          {skill.templateUpdateAvailable && (
            <span className="rounded-sm bg-[#6B8FAD]/15 px-2 py-0.5 text-xs font-medium text-[#6B8FAD]">
              Update available
            </span>
          )}
          {isEditing && (
            <Button variant="ghost" size="sm" onClick={handleCancelEdit}>
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="px-4 pb-3">
        {isEditing ? (
          <SkillEditor
            initialContent={skill.skillContent}
            onSave={handleSave}
            onCancel={handleCancelEdit}
            isSaving={isSaving}
          />
        ) : (
          <>
            {/* Skill content preview */}
            <div
              ref={contentRef}
              className={cn(
                'rounded-lg border border-border-subtle bg-background p-3',
                'font-mono text-sm leading-relaxed whitespace-pre-wrap',
                'overflow-hidden transition-all duration-200',
                !isExpanded && needsExpand && 'relative'
              )}
              style={{
                maxHeight: isExpanded ? 'none' : `${COLLAPSED_HEIGHT}px`,
              }}
              aria-label={`${skill.roleName} skill content`}
            >
              {skill.skillContent}
              {!isExpanded && needsExpand && (
                <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-background to-transparent" />
              )}
            </div>

            {/* Expand/collapse toggle */}
            {needsExpand && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className={cn(
                  'mt-1 flex w-full items-center justify-center gap-1',
                  'text-xs text-muted-foreground hover:text-foreground',
                  'focus-visible:ring-[3px] focus-visible:ring-primary/30 focus-visible:outline-none',
                  'rounded py-1'
                )}
                aria-expanded={isExpanded}
                aria-controls={`skill-content-${skill.id}`}
              >
                {isExpanded ? (
                  <>
                    Show less <ChevronUp className="h-3 w-3" />
                  </>
                ) : (
                  <>
                    Show more <ChevronDown className="h-3 w-3" />
                  </>
                )}
              </button>
            )}

            {/* Word count */}
            <div className="mt-2">
              <WordCountBar wordCount={skill.wordCount} />
            </div>

            {/* Action buttons */}
            <div className="mt-3 flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleStartEdit}>
                <Pencil className="mr-1.5 h-3.5 w-3.5" />
                Edit
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onRegenerate(skill.id)}
                className="border-[#6B8FAD]/30 text-[#6B8FAD] hover:bg-[#6B8FAD]/10"
              >
                <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                Regenerate AI
              </Button>
              <Button variant="ghost" size="sm" onClick={() => onReset(skill.id)}>
                <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                Reset
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onRemove(skill.id)}
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                Remove
              </Button>
            </div>
          </>
        )}
      </div>
    </article>
  );
});
