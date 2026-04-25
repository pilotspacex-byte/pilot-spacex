/**
 * SkillCard — Phase 91 Plan 03 Task 2.
 *
 * Per-skill card surfaced in the gallery grid. Wraps Phase 85 ArtifactCard
 * with type="SKILL" density="full" and supplies:
 *   - body slot: skill icon (lucide via resolveLucideIcon, fallback Sparkles)
 *               + 2-line-clamp description (only when non-empty)
 *               + first feature_module chip (only when present)
 *   - footer slot: "{N} refs · {relativeTime}" in JBM 10/600 muted
 *
 * onClick is owned by the parent (gallery wires router.push); SkillCard has
 * no router dependency, which keeps it trivial to render in isolation tests.
 *
 * UI-SPEC §Surface 1 — Skills Gallery (`91-UI-SPEC.md`).
 */
'use client';

import { Network, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ArtifactCard } from '@/components/artifacts/ArtifactCard';
import type { Skill } from '@/types/skill';
import { resolveLucideIcon } from '../lib/skill-icon';

export interface SkillCardProps {
  skill: Skill;
  onClick?: () => void;
}

function relativeTime(iso: string | null): string {
  if (!iso) return '—';
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true });
  } catch {
    return '—';
  }
}

function SkillCardFooter({ skill }: { skill: Skill }) {
  const refsCount = skill.reference_files.length;
  const refsLabel = refsCount === 1 ? '1 ref' : `${refsCount} refs`;
  return (
    <div
      data-testid="skill-card-footer"
      className="flex items-center gap-1 font-mono text-[10px] font-semibold text-muted-foreground"
    >
      <Network className="h-3 w-3" aria-hidden />
      <span>{refsLabel}</span>
      <span aria-hidden> · </span>
      <Clock className="h-3 w-3" aria-hidden />
      <span>{relativeTime(skill.updated_at)}</span>
    </div>
  );
}

export function SkillCard({ skill, onClick }: SkillCardProps) {
  const Icon = resolveLucideIcon(skill.icon);
  const featureTag = skill.feature_module?.[0];
  return (
    <ArtifactCard
      type="SKILL"
      id={skill.slug}
      title={skill.name}
      updatedAt={skill.updated_at ?? new Date(0).toISOString()}
      density="full"
      onClick={onClick}
      footer={<SkillCardFooter skill={skill} />}
    >
      <div className="flex items-start gap-3">
        <Icon
          className="h-5 w-5 shrink-0"
          style={{ color: '#7c5cff' }}
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          {skill.description && (
            <p
              data-testid="skill-card-description"
              className="line-clamp-2 text-[13px] font-medium text-muted-foreground"
            >
              {skill.description}
            </p>
          )}
          {featureTag && (
            <span
              data-testid="skill-card-feature-chip"
              className="mt-2 inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[13px] font-medium"
            >
              {featureTag}
            </span>
          )}
        </div>
      </div>
    </ArtifactCard>
  );
}
