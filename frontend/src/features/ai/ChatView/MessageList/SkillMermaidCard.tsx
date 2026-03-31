/**
 * SkillMermaidCard — renders a mermaid skill graph inline in ChatView.
 *
 * Thin wrapper around MermaidPreview with chat card styling.
 * Uses dynamic() import to keep mermaid lazy-loaded (avoids bundling in initial chunk).
 *
 * Phase 64-03
 */
'use client';

import { memo } from 'react';
import dynamic from 'next/dynamic';
import { GitBranch } from 'lucide-react';

/** Lazy-loaded MermaidPreview — avoids adding mermaid to initial bundle */
const MermaidPreview = dynamic(
  () =>
    import('@/features/notes/editor/extensions/pm-blocks/MermaidPreview').then((m) => ({
      default: m.MermaidPreview,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-32 animate-pulse bg-muted rounded-lg"
        aria-label="Loading diagram..."
        role="status"
      />
    ),
  }
);

export interface SkillMermaidCardProps {
  /** Mermaid diagram source code */
  code: string;
  /** Optional skill name shown in the header */
  skillName?: string;
}

export const SkillMermaidCard = memo<SkillMermaidCardProps>(function SkillMermaidCard({
  code,
  skillName,
}) {
  return (
    <div
      className="mx-4 my-3 rounded-[14px] border bg-background p-4 animate-fade-up"
      role="figure"
      aria-label={skillName ? `Skill graph for ${skillName}` : 'Skill graph'}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <GitBranch className="h-4 w-4 text-primary" aria-hidden="true" />
        <span className="font-medium text-sm">
          {skillName ? `Skill Graph: ${skillName}` : 'Skill Graph'}
        </span>
      </div>

      {/* Diagram */}
      <MermaidPreview code={code} className="my-2" />
    </div>
  );
});

SkillMermaidCard.displayName = 'SkillMermaidCard';
