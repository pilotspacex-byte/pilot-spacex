'use client';

/**
 * PinnedArtifactsList — Display and manage pinned artifacts (notes, issues, specs, decisions)
 *
 * Generalized from the v2 `PinnedNotesList` for the v3 sidebar. The component keeps its original
 * behaviour (drag-drop reorder, click-to-navigate, per-row action menu) and adds an `artifactType`
 * prop so callers can pin future artifact kinds. Existing call sites default to `NOTE` and do not
 * need to pass the new prop.
 */
import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { AnimatePresence, Reorder } from 'motion/react';
import {
  FileText,
  CircleDot,
  FileCode,
  Lightbulb,
  Pin,
  PinOff,
  Trash2,
  Copy,
  ExternalLink,
  MoreHorizontal,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

/**
 * v3 artifact types that can be pinned in the sidebar. The card anatomy is unified
 * (see `.planning/design.md` §4.3), but the sidebar row uses one accent icon per type.
 */
export type PinnedArtifactType = 'NOTE' | 'ISSUE' | 'SPEC' | 'DECISION';

export interface PinnedArtifact {
  id: string;
  title: string;
  updatedAt: string;
}

// Back-compat: existing callers imported `PinnedNote` from this module.
export type PinnedNote = PinnedArtifact;

export interface PinnedArtifactsListProps {
  /** List of pinned artifacts */
  notes: PinnedArtifact[];
  /** Workspace slug for navigation */
  workspaceSlug: string;
  /** Currently selected artifact id */
  selectedNoteId?: string;
  /** Callback when order changes */
  onReorder: (noteIds: string[]) => void;
  /** Callback to unpin */
  onUnpin: (noteId: string) => void;
  /** Callback to delete */
  onDelete?: (noteId: string) => void;
  /** Callback to duplicate */
  onDuplicate?: (noteId: string) => void;
  /**
   * Artifact type — controls row icon, navigation path, and aria labels.
   * Defaults to `NOTE` so the rename is non-breaking for existing call sites.
   */
  artifactType?: PinnedArtifactType;
}

// Back-compat alias so existing imports do not break during the v3 rollout.
export type PinnedNotesListProps = PinnedArtifactsListProps;

interface ArtifactTypeConfig {
  icon: LucideIcon;
  /** Accent color class for the icon. Sidebar v3 uses muted icons with semantic hue. */
  accentClass: string;
  /** Path segment under the workspace slug. */
  routeSegment: string;
  /** Singular noun used in the empty state copy. */
  label: string;
}

const ARTIFACT_TYPE_CONFIG: Record<PinnedArtifactType, ArtifactTypeConfig> = {
  NOTE: {
    icon: FileText,
    accentClass: 'text-[color:var(--brand-primary,theme(colors.amber.500))]',
    routeSegment: 'notes',
    label: 'notes',
  },
  ISSUE: {
    icon: CircleDot,
    accentClass: 'text-blue-500',
    routeSegment: 'issues',
    label: 'issues',
  },
  SPEC: {
    icon: FileCode,
    accentClass: 'text-purple-500',
    routeSegment: 'specs',
    label: 'specs',
  },
  DECISION: {
    icon: Lightbulb,
    accentClass: 'text-amber-500',
    routeSegment: 'decisions',
    label: 'decisions',
  },
};

interface PinnedArtifactItemProps {
  note: PinnedArtifact;
  isSelected: boolean;
  workspaceSlug: string;
  config: ArtifactTypeConfig;
  onUnpin: () => void;
  onDelete?: () => void;
  onDuplicate?: () => void;
}

function PinnedArtifactItem({
  note,
  isSelected,
  workspaceSlug,
  config,
  onUnpin,
  onDelete,
  onDuplicate,
}: PinnedArtifactItemProps) {
  const href = `/${workspaceSlug}/${config.routeSegment}/${note.id}`;

  const handleCopyLink = useCallback(() => {
    navigator.clipboard.writeText(`${window.location.origin}${href}`);
  }, [href]);

  const handleOpenNewTab = useCallback(() => {
    window.open(href, '_blank');
  }, [href]);

  const Icon = config.icon;

  return (
    <Reorder.Item
      value={note}
      className={cn(
        'group flex items-center gap-2 rounded-md px-2 py-1.5 cursor-grab active:cursor-grabbing',
        'transition-colors',
        isSelected ? 'bg-accent' : 'hover:bg-accent/50'
      )}
      whileDrag={{ scale: 1.02, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
    >
      <Icon className={cn('h-3.5 w-3.5 shrink-0', config.accentClass)} aria-hidden="true" />
      <Link
        href={href}
        className="flex-1 min-w-0 text-sm truncate"
        onClick={(e) => e.stopPropagation()}
      >
        {note.title || 'Untitled'}
      </Link>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            className="h-6 w-6 opacity-0 group-hover:opacity-100 shrink-0"
            onClick={(e) => e.stopPropagation()}
            aria-label={`Actions for ${note.title || 'Untitled'}`}
          >
            <MoreHorizontal className="h-3.5 w-3.5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          <DropdownMenuItem onClick={onUnpin}>
            <PinOff className="mr-2 h-4 w-4" />
            Unpin
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleCopyLink}>
            <Copy className="mr-2 h-4 w-4" />
            Copy link
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleOpenNewTab}>
            <ExternalLink className="mr-2 h-4 w-4" />
            Open in new tab
          </DropdownMenuItem>
          {onDuplicate && (
            <DropdownMenuItem onClick={onDuplicate}>
              <FileText className="mr-2 h-4 w-4" />
              Duplicate
            </DropdownMenuItem>
          )}
          {onDelete && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive" onClick={onDelete}>
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </Reorder.Item>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-4 text-center">
      <Pin className="h-5 w-5 text-muted-foreground/30 mb-2" aria-hidden="true" />
      <p className="text-xs text-muted-foreground">No pinned {label}</p>
    </div>
  );
}

/**
 * `PinnedArtifactsList` renders a re-orderable list of pinned artifacts for the sidebar.
 * Defaults to `NOTE` so existing callers continue to work without changes.
 */
export const PinnedArtifactsList = observer(function PinnedArtifactsList({
  notes,
  workspaceSlug,
  selectedNoteId,
  onReorder,
  onUnpin,
  onDelete,
  onDuplicate,
  artifactType = 'NOTE',
}: PinnedArtifactsListProps) {
  const config = ARTIFACT_TYPE_CONFIG[artifactType];

  const handleReorder = useCallback(
    (newOrder: PinnedArtifact[]) => {
      onReorder(newOrder.map((note) => note.id));
    },
    [onReorder]
  );

  if (notes.length === 0) {
    return <EmptyState label={config.label} />;
  }

  return (
    <Reorder.Group axis="y" values={notes} onReorder={handleReorder} className="space-y-0.5">
      <AnimatePresence mode="popLayout">
        {notes.map((note) => (
          <PinnedArtifactItem
            key={note.id}
            note={note}
            isSelected={selectedNoteId === note.id}
            workspaceSlug={workspaceSlug}
            config={config}
            onUnpin={() => onUnpin(note.id)}
            onDelete={onDelete ? () => onDelete(note.id) : undefined}
            onDuplicate={onDuplicate ? () => onDuplicate(note.id) : undefined}
          />
        ))}
      </AnimatePresence>
    </Reorder.Group>
  );
});

// Back-compat alias — v2 callers imported `PinnedNotesList`. Keep exported during rollout.
export const PinnedNotesList = PinnedArtifactsList;

export default PinnedArtifactsList;
