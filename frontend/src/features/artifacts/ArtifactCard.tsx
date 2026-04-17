'use client';

/**
 * ArtifactCard — unified card for the 12 v3 artifact types.
 *
 * Design spec: .planning/design.md v3 §Artifact Type System
 *
 * Tier 1 (native): NOTE, ISSUE, SPEC, DECISION
 * Tier 2 (file):   MD, HTML, CODE, PDF, CSV, IMG, PPTX, LINK
 *
 * Visual contract:
 *   - Radius 22px (md/lg) or 16px (sm)
 *   - Gradient top border in artifact type color (`var(--color-artifact-{type})`)
 *   - Icon badge, 1-line title, 2-line snippet, footer with timestamp + state
 *   - Hover elevates to L2 shadow
 *
 * Interaction contract:
 *   - onClick receives preference over onPeek only if both are omitted
 *   - If onPeek is passed, clicking fires onPeek({ type, id })
 *   - Else if onClick is passed, fires onClick()
 *   - Else navigates via router.push to the artifact's canonical route
 *
 * Note: plain React component — not wrapped in observer(). If the caller needs
 * MobX reactivity, wrap the parent in observer() and pass plain props through.
 */

import { memo, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  CircleDot,
  Code,
  ExternalLink,
  FileSpreadsheet,
  FileText,
  FileType,
  Globe,
  Image as ImageIcon,
  Link as LinkIcon,
  Presentation,
  Scale,
  ScrollText,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ArtifactType =
  // Tier 1 — native
  | 'NOTE'
  | 'ISSUE'
  | 'SPEC'
  | 'DECISION'
  // Tier 2 — file
  | 'MD'
  | 'HTML'
  | 'CODE'
  | 'PDF'
  | 'CSV'
  | 'IMG'
  | 'PPTX'
  | 'LINK';

interface CommonArtifactProps {
  /** Fires when the card is opened in a peek drawer. Takes precedence over onClick. */
  onPeek?: (target: { type: ArtifactType; id: string }) => void;
  /** Fires when clicked if onPeek is not provided. Takes precedence over default navigation. */
  onClick?: () => void;
  className?: string;
  /** Size variant — sm collapses padding and uses the 16px list-card radius. */
  size?: 'sm' | 'md' | 'lg';
}

interface AssigneeLite {
  name: string;
  avatarUrl?: string;
}

export type ArtifactCardProps =
  | (CommonArtifactProps & {
      type: 'NOTE';
      id: string;
      title: string;
      snippet?: string;
      updatedAt: string;
      projectName?: string;
      pinned?: boolean;
    })
  | (CommonArtifactProps & {
      type: 'ISSUE';
      id: string;
      identifier: string;
      title: string;
      state: string;
      priority?: string;
      assignee?: AssigneeLite;
      updatedAt?: string;
    })
  | (CommonArtifactProps & {
      type: 'SPEC' | 'DECISION';
      id: string;
      title: string;
      status?: string;
      snippet?: string;
      updatedAt: string;
    })
  | (CommonArtifactProps & {
      type: 'MD' | 'HTML' | 'CODE' | 'PDF' | 'CSV' | 'IMG' | 'PPTX';
      id: string;
      filename: string;
      size?: number;
      updatedAt: string;
    })
  | (CommonArtifactProps & {
      type: 'LINK';
      id: string;
      url: string;
      title?: string;
      updatedAt?: string;
    });

// ---------------------------------------------------------------------------
// Static lookups — hoisted so memoized children don't re-create them
// ---------------------------------------------------------------------------

const ICON_BY_TYPE: Readonly<Record<ArtifactType, LucideIcon>> = {
  NOTE: FileText,
  ISSUE: CircleDot,
  SPEC: ScrollText,
  DECISION: Scale,
  MD: FileText,
  HTML: Globe,
  CODE: Code,
  PDF: FileType,
  CSV: FileSpreadsheet,
  IMG: ImageIcon,
  PPTX: Presentation,
  LINK: LinkIcon,
};

const LABEL_BY_TYPE: Readonly<Record<ArtifactType, string>> = {
  NOTE: 'Note',
  ISSUE: 'Issue',
  SPEC: 'Spec',
  DECISION: 'Decision',
  MD: 'Markdown',
  HTML: 'HTML',
  CODE: 'Code',
  PDF: 'PDF',
  CSV: 'CSV',
  IMG: 'Image',
  PPTX: 'Presentation',
  LINK: 'Link',
};

/**
 * Resolve the CSS variable name for a given artifact type.
 * Exported so other surfaces (e.g. PeekDrawer header, composer chips) can
 * reuse the same color mapping without reimplementing it.
 */
export function resolveArtifactColor(type: ArtifactType): string {
  return `var(--color-artifact-${type.toLowerCase()})`;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const UNITS: ReadonlyArray<readonly [number, string]> = [
  [86_400_000, 'd'],
  [3_600_000, 'h'],
  [60_000, 'm'],
];

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  if (diff < 60_000) return 'just now';
  for (const [ms, unit] of UNITS) {
    if (diff >= ms) return `${Math.floor(diff / ms)}${unit} ago`;
  }
  return 'just now';
}

const SIZE_UNITS = ['B', 'KB', 'MB', 'GB'] as const;

function formatFileSize(bytes?: number): string | null {
  if (bytes === undefined || bytes === null || bytes < 0) return null;
  if (bytes === 0) return '0 B';
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), SIZE_UNITS.length - 1);
  const value = bytes / Math.pow(1024, exp);
  return `${value.toFixed(value >= 10 || exp === 0 ? 0 : 1)} ${SIZE_UNITS[exp]}`;
}

function hostnameFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function initialsFromName(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

function getTitle(props: ArtifactCardProps): string {
  switch (props.type) {
    case 'NOTE':
    case 'ISSUE':
    case 'SPEC':
    case 'DECISION':
      return props.title;
    case 'MD':
    case 'HTML':
    case 'CODE':
    case 'PDF':
    case 'CSV':
    case 'IMG':
    case 'PPTX':
      return props.filename;
    case 'LINK':
      return props.title ?? hostnameFromUrl(props.url);
  }
}

// ---------------------------------------------------------------------------
// Subtitle / footer renderers (no hooks — safe to call from the memo body)
// ---------------------------------------------------------------------------

function Subtitle(props: ArtifactCardProps) {
  switch (props.type) {
    case 'NOTE':
      return props.snippet ? (
        <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
          {props.snippet}
        </p>
      ) : null;
    case 'ISSUE':
      return (
        <p className="font-mono text-xs text-muted-foreground tracking-wide">{props.identifier}</p>
      );
    case 'SPEC':
    case 'DECISION':
      return props.snippet ? (
        <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
          {props.snippet}
        </p>
      ) : null;
    case 'MD':
    case 'HTML':
    case 'CODE':
    case 'PDF':
    case 'CSV':
    case 'IMG':
    case 'PPTX': {
      const size = formatFileSize(props.size);
      return size ? <p className="text-xs text-muted-foreground">{size}</p> : null;
    }
    case 'LINK':
      return <p className="text-xs text-muted-foreground truncate">{hostnameFromUrl(props.url)}</p>;
  }
}

function Footer(props: ArtifactCardProps) {
  const updatedAt =
    'updatedAt' in props && props.updatedAt ? formatRelativeTime(props.updatedAt) : null;

  switch (props.type) {
    case 'NOTE':
      return (
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span className="truncate">{props.projectName ?? 'Workspace'}</span>
          <span className="font-mono tabular-nums shrink-0">{updatedAt}</span>
        </div>
      );
    case 'ISSUE':
      return (
        <div className="flex items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-1.5 min-w-0">
            <Badge variant="secondary" className="text-[10px] font-medium uppercase tracking-wide">
              {props.state}
            </Badge>
            {props.priority ? (
              <span className="text-muted-foreground truncate">{props.priority}</span>
            ) : null}
          </div>
          {props.assignee ? (
            <Avatar className="h-5 w-5 shrink-0">
              {props.assignee.avatarUrl ? (
                <AvatarImage src={props.assignee.avatarUrl} alt={props.assignee.name} />
              ) : null}
              <AvatarFallback className="text-[10px]">
                {initialsFromName(props.assignee.name)}
              </AvatarFallback>
            </Avatar>
          ) : null}
        </div>
      );
    case 'SPEC':
    case 'DECISION':
      return (
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span className="truncate">{props.status ?? '—'}</span>
          <span className="font-mono tabular-nums shrink-0">{updatedAt}</span>
        </div>
      );
    case 'MD':
    case 'HTML':
    case 'CODE':
    case 'PDF':
    case 'CSV':
    case 'IMG':
    case 'PPTX':
      return (
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span className="uppercase tracking-wider">{LABEL_BY_TYPE[props.type]}</span>
          <span className="font-mono tabular-nums shrink-0">{updatedAt}</span>
        </div>
      );
    case 'LINK':
      return updatedAt ? (
        <div className="flex items-center justify-end gap-2 text-xs text-muted-foreground">
          <span className="font-mono tabular-nums shrink-0">{updatedAt}</span>
        </div>
      ) : null;
  }
}

// ---------------------------------------------------------------------------
// Default navigation
// ---------------------------------------------------------------------------

function resolveHref(props: ArtifactCardProps, workspaceSlug: string | undefined): string | null {
  if (!workspaceSlug && props.type !== 'LINK') return null;
  switch (props.type) {
    case 'NOTE':
      return `/${workspaceSlug}/notes/${props.id}`;
    case 'ISSUE':
      return `/${workspaceSlug}/issues/${props.id}`;
    case 'SPEC':
    case 'DECISION':
      return `/${workspaceSlug}/notes/${props.id}`;
    case 'MD':
    case 'HTML':
    case 'CODE':
    case 'PDF':
    case 'CSV':
    case 'IMG':
    case 'PPTX':
      // File artifacts live on their parent project — fall back to peek-via-URL
      return `/${workspaceSlug}/?peek=${props.type.toLowerCase()}:${props.id}`;
    case 'LINK':
      return props.url;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Unified artifact card. Memoized because list-heavy routes (homepage grid,
 * project overview, peek-drawer footer) render dozens at a time with stable
 * props — memoization prevents an O(N) re-render on unrelated state changes.
 */
export const ArtifactCard = memo(function ArtifactCard(props: ArtifactCardProps) {
  const { className, size = 'md', onPeek, onClick } = props;
  const router = useRouter();
  const params = useParams<{ workspaceSlug?: string }>();
  const workspaceSlug = params?.workspaceSlug;

  const Icon = ICON_BY_TYPE[props.type];
  const typeColor = resolveArtifactColor(props.type);
  const typeLabel = LABEL_BY_TYPE[props.type];
  const title = getTitle(props);

  const handleActivate = useCallback(() => {
    if (onPeek) {
      onPeek({ type: props.type, id: props.id });
      return;
    }
    if (onClick) {
      onClick();
      return;
    }
    const href = resolveHref(props, workspaceSlug);
    if (!href) return;
    if (props.type === 'LINK') {
      window.open(href, '_blank', 'noopener,noreferrer');
    } else {
      router.push(href);
    }
  }, [onPeek, onClick, props, router, workspaceSlug]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLElement>) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleActivate();
      }
    },
    [handleActivate]
  );

  const isCompact = size === 'sm';
  const radiusClass = isCompact ? 'rounded-[16px]' : 'rounded-[22px]';
  const paddingClass = isCompact ? 'p-3' : size === 'lg' ? 'p-5' : 'p-4';

  return (
    <article
      role="button"
      tabIndex={0}
      aria-label={`${typeLabel}: ${title}`}
      onClick={handleActivate}
      onKeyDown={handleKeyDown}
      className={cn(
        'group relative flex flex-col gap-2 overflow-hidden',
        'bg-card text-card-foreground border border-border/70',
        'shadow-[var(--shadow-l1)]',
        'transition-[transform,box-shadow,border-color] duration-200 ease-out',
        'hover:-translate-y-0.5 hover:shadow-[var(--shadow-l2)] hover:border-border',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        'cursor-pointer select-none',
        radiusClass,
        paddingClass,
        className
      )}
    >
      {/* Gradient top border — the signature v3 tell */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-[3px]"
        style={{
          background: `linear-gradient(90deg, ${typeColor} 0%, ${typeColor} 55%, transparent 100%)`,
          opacity: 0.85,
        }}
      />

      {/* Header row — icon badge + type label */}
      <header className="flex items-center gap-2">
        <span
          className={cn(
            'inline-flex items-center justify-center shrink-0',
            isCompact ? 'h-6 w-6 rounded-md' : 'h-7 w-7 rounded-lg'
          )}
          style={{
            backgroundColor: `color-mix(in oklab, ${typeColor} 14%, transparent)`,
            color: typeColor,
          }}
          aria-hidden="true"
        >
          <Icon className={isCompact ? 'h-3.5 w-3.5' : 'h-4 w-4'} />
        </span>
        <span
          className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-foreground"
          style={{ color: typeColor }}
        >
          {typeLabel}
        </span>
        {props.type === 'NOTE' && props.pinned ? (
          <span className="ml-auto text-[10px] font-medium text-[color:var(--priority-medium)]">
            Pinned
          </span>
        ) : null}
        {props.type === 'LINK' ? (
          <ExternalLink
            className="ml-auto h-3.5 w-3.5 text-muted-foreground/70"
            aria-hidden="true"
          />
        ) : null}
      </header>

      {/* Title */}
      <h3
        className={cn(
          'font-medium leading-snug line-clamp-1 text-foreground',
          isCompact ? 'text-sm' : 'text-[15px]'
        )}
        title={title}
      >
        {title}
      </h3>

      {/* Subtitle / snippet */}
      <Subtitle {...props} />

      {/* Footer — timestamp, state, metadata */}
      <div className="mt-auto pt-1">
        <Footer {...props} />
      </div>
    </article>
  );
});

ArtifactCard.displayName = 'ArtifactCard';
