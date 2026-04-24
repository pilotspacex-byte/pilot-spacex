/**
 * InlineArtifactCard — Phase 87 Plan 04 (CHAT-04).
 *
 * Variant dispatcher rendered inside the assistant message body slot.
 * Picks one of three variants and either delegates to the Phase 85
 * `<ArtifactCard>` (Full) or renders bespoke chrome (Group, Compact pill)
 * because Phase 85 only ships `full | preview | compact` densities — Group
 * is its own anatomy.
 *
 * Click handlers route through Phase 86 `useArtifactPeekState().openPeek`,
 * which mutates `?peek={id}&peekType={type}` on the URL.
 *
 * Per `.claude/rules/icons.md`: Compact icon resolution uses a LOCAL Lucide
 * component map (`INLINE_TYPE_ICON`). Phase 85 `ARTIFACT_TYPE_TOKENS` does
 * NOT carry an `iconName` field — DO NOT introduce one.
 *
 * Surgical-changes discipline (CLAUDE.md Rule 1.3):
 *   - DO NOT modify `ArtifactCard.tsx`
 *   - DO NOT modify `ARTIFACT_TYPE_TOKENS`
 *   - DO NOT modify `useArtifactPeekState`
 */
'use client';

import * as React from 'react';
import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  CheckSquare,
  Code2,
  FileCode,
  FileImage,
  FileSpreadsheet,
  FileText,
  FileType,
  GitCommit,
  Link as LinkIcon,
  Presentation,
} from 'lucide-react';

import { ArtifactCard } from '@/components/artifacts/ArtifactCard';
import { useArtifactPeekState } from '@/hooks/use-artifact-peek-state';
import { ARTIFACT_TYPE_TOKENS, type ArtifactTokenKey } from '@/lib/artifact-tokens';
import { artifactLabel } from '@/lib/artifact-labels';

// ---------------------------------------------------------------------------
// Public contract — backend message envelope shape.
// ---------------------------------------------------------------------------

export type InlineArtifactVariant = 'full' | 'group' | 'compact';

export interface InlineArtifactGroupRow {
  id: string;
  type: ArtifactTokenKey;
  title: string;
  state?: string;
  stateColor?: string;
  updatedAt: string;
}

export interface InlineArtifactRef {
  id: string;
  type: ArtifactTokenKey;
  /** REQUIRED for compact variant; backend supplies at envelope time. */
  title?: string;
  /** Required for Full variant; backend supplies at envelope time. */
  updatedAt?: string;
  /** Optional metadata passed straight through to ArtifactCard. */
  snippet?: string;
  projectName?: string;
  projectColor?: string;
  variant?: InlineArtifactVariant;
  group?: {
    label: string;
    rows: InlineArtifactGroupRow[];
  };
}

export interface InlineArtifactCardProps {
  artifact: InlineArtifactRef;
}

// ---------------------------------------------------------------------------
// Local Lucide icon map for the Compact pill.
//
// Phase 85 `ARTIFACT_TYPE_TOKENS` carries colour/gradient only; no iconName.
// Per `.claude/rules/icons.md` we use Lucide component imports — never name
// strings. Update this map (additive) when new artifact types ship.
// ---------------------------------------------------------------------------
type LucideIcon = React.ComponentType<{
  className?: string;
  style?: React.CSSProperties;
}>;

export const INLINE_TYPE_ICON: Record<ArtifactTokenKey, LucideIcon> = {
  // Tier 1 native
  NOTE: FileText,
  ISSUE: CheckSquare,
  SPEC: FileText,
  DECISION: GitCommit,
  // Tier 2 file
  MD: FileText,
  HTML: Code2,
  CODE: FileCode,
  PDF: FileType,
  CSV: FileSpreadsheet,
  IMG: FileImage,
  PPTX: Presentation,
  LINK: LinkIcon,
};

const TIER_ONE_TYPES = new Set<ArtifactTokenKey>([
  'NOTE',
  'SPEC',
  'ISSUE',
  'DECISION',
]);

function resolveVariant(ref: InlineArtifactRef): InlineArtifactVariant {
  if (ref.variant) return ref.variant;
  if (ref.group) return 'group';
  if (TIER_ONE_TYPES.has(ref.type)) return 'full';
  return 'compact';
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

export function InlineArtifactCard({ artifact }: InlineArtifactCardProps) {
  const variant = resolveVariant(artifact);
  const { openPeek } = useArtifactPeekState();

  if (variant === 'full') {
    return (
      <FullVariant
        artifact={artifact}
        onOpenPeek={() => openPeek(artifact.id, artifact.type)}
      />
    );
  }
  if (variant === 'group') {
    return (
      <GroupVariant
        artifact={artifact}
        onOpenRowPeek={(rowId, rowType) => openPeek(rowId, rowType)}
      />
    );
  }
  return (
    <CompactVariant
      artifact={artifact}
      onOpenPeek={() => openPeek(artifact.id, artifact.type)}
    />
  );
}

// ---------------------------------------------------------------------------
// Full variant — delegates to Phase 85 ArtifactCard at preview density.
// Header click opens peek; chevron toggles inline body without opening peek.
// ---------------------------------------------------------------------------

function FullVariant({
  artifact,
  onOpenPeek,
}: {
  artifact: InlineArtifactRef;
  onOpenPeek: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const title = artifact.title ?? '';
  const updatedAt = artifact.updatedAt ?? '';

  return (
    <div data-inline-card="full">
      <div className="relative">
        <div
          data-full-header-target=""
          onClick={onOpenPeek}
          className="cursor-pointer"
        >
          <ArtifactCard
            id={artifact.id}
            type={artifact.type}
            title={title}
            updatedAt={updatedAt}
            snippet={artifact.snippet}
            projectName={artifact.projectName}
            projectColor={artifact.projectColor}
            density="preview"
          />
        </div>
        <button
          type="button"
          aria-label={expanded ? 'Collapse body' : 'Expand body'}
          onClick={(e) => {
            e.stopPropagation();
            setExpanded((v) => !v);
          }}
          className="absolute top-3 right-3 z-10 rounded p-1 hover:bg-black/[0.04]"
        >
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>
      </div>
      {expanded && (
        <div className="mt-2 motion-safe:transition-all motion-safe:duration-200 motion-safe:ease-out">
          <ArtifactCard
            id={artifact.id}
            type={artifact.type}
            title={title}
            updatedAt={updatedAt}
            snippet={artifact.snippet}
            projectName={artifact.projectName}
            projectColor={artifact.projectColor}
            density="full"
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Group variant — bespoke chrome (no Phase 85 density covers this anatomy).
// 5 rows visible by default + "Show N more" expander. Each row opens peek.
// ---------------------------------------------------------------------------

function GroupVariant({
  artifact,
  onOpenRowPeek,
}: {
  artifact: InlineArtifactRef;
  onOpenRowPeek: (id: string, type: ArtifactTokenKey) => void;
}) {
  const rows = artifact.group?.rows ?? [];
  const label = artifact.group?.label ?? '';
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? rows : rows.slice(0, 5);
  const hidden = Math.max(0, rows.length - 5);

  return (
    <div data-inline-card="group" className="rounded-[22px] border bg-card">
      <div className="flex h-10 items-center justify-between border-b border-border/60 px-4">
        <span className="text-[13px] font-semibold">{label}</span>
        <span className="font-mono text-[11px] text-muted-foreground">
          {rows.length}
        </span>
      </div>
      {rows.length === 0 ? (
        <div className="flex h-9 items-center px-4 text-[13px] text-muted-foreground">
          No items
        </div>
      ) : (
        <ul role="list" className="divide-y divide-border/30">
          {visible.map((row) => (
            <li
              key={row.id}
              role="listitem"
              data-inline-group-row=""
              onClick={() => onOpenRowPeek(row.id, row.type)}
              className="flex h-9 cursor-pointer items-center gap-3 px-4 hover:bg-accent/30"
            >
              {row.state && (
                <>
                  <span
                    aria-hidden="true"
                    className="h-2 w-2 flex-shrink-0 rounded-full"
                    style={{ background: row.stateColor ?? '#94a3b8' }}
                  />
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {row.state}
                  </span>
                </>
              )}
              <span className="flex-1 truncate text-[13px]">{row.title}</span>
              <time className="font-mono text-[10px] text-muted-foreground">
                {row.updatedAt}
              </time>
            </li>
          ))}
        </ul>
      )}
      {!expanded && hidden > 0 && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="h-10 w-full px-4 text-left text-[13px] font-medium text-[#29a386] hover:underline"
        >
          {hidden === 1 ? 'Show 1 more' : `Show ${hidden} more`}
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compact pill — single-row 9999-radius chip with type icon + envelope title.
// ---------------------------------------------------------------------------

function CompactVariant({
  artifact,
  onOpenPeek,
}: {
  artifact: InlineArtifactRef;
  onOpenPeek: () => void;
}) {
  const tokens = ARTIFACT_TYPE_TOKENS[artifact.type];
  const Icon = INLINE_TYPE_ICON[artifact.type];
  const typeLabel = artifactLabel(artifact.type, false);
  const title = artifact.title ?? '';

  return (
    <button
      type="button"
      data-inline-card="compact"
      data-compact-pill=""
      onClick={onOpenPeek}
      className="inline-flex h-7 max-w-[280px] cursor-pointer items-center gap-2 rounded-full border bg-card px-3 hover:bg-accent/30"
      style={{ borderColor: tokens.accent + '55' }}
    >
      <Icon
        className="h-3.5 w-3.5 flex-shrink-0"
        style={{ color: tokens.accent }}
      />
      <span
        className="flex-shrink-0 font-mono text-[10px] font-semibold uppercase tracking-wider"
        style={{ color: tokens.badgeText }}
      >
        {typeLabel}
      </span>
      <span className="truncate text-xs font-medium">{title}</span>
    </button>
  );
}
