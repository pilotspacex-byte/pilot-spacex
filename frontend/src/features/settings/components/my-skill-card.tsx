/**
 * MySkillCard — Displays a user's personalized skill.
 *
 * Compact card with status indicator, toggle, and delete actions.
 * Click card to open SkillDetailModal for viewing/editing.
 * Plain component (NOT observer) — receives all data via props.
 * Source: Phase 20, P20-10
 */

'use client';

import { Power, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { UserSkill } from '@/services/api/user-skills';

interface MySkillCardProps {
  skill: UserSkill;
  onToggleActive: (skill: UserSkill) => void;
  onDelete: (skill: UserSkill) => void;
  onClick: (skill: UserSkill) => void;
}

export function MySkillCard({ skill, onToggleActive, onDelete, onClick }: MySkillCardProps) {
  const displayName = skill.skill_name ?? skill.template_name ?? 'Custom Skill';

  return (
    <article
      className={`group relative flex items-center gap-3 rounded-xl border bg-card p-3 transition-all duration-200 hover:shadow-md hover:border-border/80 cursor-pointer ${
        !skill.is_active ? 'opacity-50' : ''
      }`}
      data-testid="my-skill-card"
      onClick={() => onClick(skill)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          // Ignore events bubbling from inner buttons (toggle, delete)
          if (e.target !== e.currentTarget) return;
          e.preventDefault();
          onClick(skill);
        }
      }}
    >
      {/* Status dot */}
      <div
        className={`shrink-0 h-2 w-2 rounded-full ${
          skill.is_active ? 'bg-emerald-500' : 'bg-muted-foreground/40'
        }`}
        aria-label={skill.is_active ? 'Active' : 'Inactive'}
      />

      {/* Content */}
      <div className="min-w-0 flex-1">
        <h3 className="text-sm font-medium truncate">{displayName}</h3>
        {skill.experience_description && (
          <p className="text-xs text-muted-foreground truncate mt-0.5">
            {skill.experience_description}
          </p>
        )}
      </div>

      {/* Actions — visible on hover */}
      <div
        className="flex gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={(e) => e.stopPropagation()}
      >
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => onToggleActive(skill)}
          aria-label={skill.is_active ? 'Deactivate skill' : 'Activate skill'}
        >
          <Power className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-destructive hover:text-destructive"
          onClick={() => onDelete(skill)}
          aria-label="Delete skill"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </article>
  );
}
