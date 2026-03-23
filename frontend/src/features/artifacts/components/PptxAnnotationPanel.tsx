'use client';

/**
 * PptxAnnotationPanel — collapsible right panel showing per-slide annotations.
 *
 * Props:
 *   workspaceId, projectId, artifactId — for API calls
 *   currentSlide — the 0-based slide index (re-queries when this changes)
 *   currentUserId — to gate edit/delete actions to annotation author
 *
 * Layout: 320px side panel with border-l, flex column.
 * Toggle button shown in panel header area; collapses to a narrow icon strip.
 *
 * Data: TanStack Query hooks (not MobX) — annotations are server state.
 */

import * as React from 'react';
import { MessageSquarePlus, Pencil, Trash2, X, ChevronRight, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  useSlideAnnotations,
  useCreateAnnotation,
  useUpdateAnnotation,
  useDeleteAnnotation,
} from '../hooks/use-slide-annotations';
import type { ArtifactAnnotation } from '@/services/api/artifact-annotations';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRelativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

// ---------------------------------------------------------------------------
// AnnotationCard
// ---------------------------------------------------------------------------

interface AnnotationCardProps {
  annotation: ArtifactAnnotation;
  isOwner: boolean;
  onEdit: (id: string, content: string) => void;
  onDelete: (id: string) => void;
  editingId: string | null;
  editDraft: string;
  onEditDraftChange: (v: string) => void;
  onEditSave: () => void;
  onEditCancel: () => void;
  isUpdating: boolean;
  isDeleting: boolean;
}

function AnnotationCard({
  annotation,
  isOwner,
  onEdit,
  onDelete,
  editingId,
  editDraft,
  onEditDraftChange,
  onEditSave,
  onEditCancel,
  isUpdating,
  isDeleting,
}: AnnotationCardProps) {
  const isEditing = editingId === annotation.id;
  const isTemp = annotation.id.startsWith('temp-');

  return (
    <div
      className={cn(
        'rounded-lg bg-background p-3 space-y-2 border border-border/40 shadow-sm transition-opacity',
        (isDeleting || isTemp) && 'opacity-50'
      )}
    >
      {/* Header: author avatar + timestamp */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="size-5 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
            <span className="text-[9px] font-bold text-primary/80 uppercase">
              {annotation.userId?.[0]?.toUpperCase() ?? '?'}
            </span>
          </div>
          <span className="text-[11px] text-muted-foreground/70 truncate">
            {formatRelativeTime(annotation.updatedAt)}
          </span>
        </div>

        {/* Edit / delete — owner only */}
        {isOwner && !isTemp && !isEditing && (
          <div className="flex items-center gap-0.5 shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="size-6"
              onClick={() => onEdit(annotation.id, annotation.content)}
              aria-label="Edit annotation"
              disabled={isDeleting}
            >
              <Pencil className="size-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="size-6 text-destructive hover:text-destructive"
              onClick={() => onDelete(annotation.id)}
              aria-label="Delete annotation"
              disabled={isDeleting}
            >
              <Trash2 className="size-3" />
            </Button>
          </div>
        )}
      </div>

      {/* Content — or edit textarea */}
      {isEditing ? (
        <div className="space-y-2">
          <Textarea
            value={editDraft}
            onChange={(e) => onEditDraftChange(e.target.value)}
            className="min-h-[80px] text-sm resize-none"
            autoFocus
            aria-label="Edit annotation content"
          />
          <div className="flex items-center justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={onEditCancel}
              disabled={isUpdating}
            >
              <X className="size-3 mr-1" />
              Cancel
            </Button>
            <Button
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={onEditSave}
              disabled={isUpdating || !editDraft.trim()}
            >
              <Check className="size-3 mr-1" />
              Save
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-sm whitespace-pre-wrap break-words">{annotation.content}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PptxAnnotationPanel — main export
// ---------------------------------------------------------------------------

export interface PptxAnnotationPanelProps {
  workspaceId: string;
  projectId: string;
  artifactId: string;
  currentSlide: number;
  currentUserId: string;
}

export function PptxAnnotationPanel({
  workspaceId,
  projectId,
  artifactId,
  currentSlide,
  currentUserId,
}: PptxAnnotationPanelProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [newContent, setNewContent] = React.useState('');
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editDraft, setEditDraft] = React.useState('');
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

  // Reset new annotation textarea when slide changes
  React.useEffect(() => {
    setNewContent('');
    setEditingId(null);
    setEditDraft('');
  }, [currentSlide]);

  // TanStack Query hooks
  const {
    data: annotations = [],
    isLoading,
    isError,
  } = useSlideAnnotations(workspaceId, projectId, artifactId, currentSlide);

  const createMutation = useCreateAnnotation(workspaceId, projectId, artifactId);
  const updateMutation = useUpdateAnnotation(workspaceId, projectId, artifactId);
  const deleteMutation = useDeleteAnnotation(workspaceId, projectId, artifactId);

  const annotationCount = annotations.length;

  // Handlers
  const handleCreate = () => {
    if (!newContent.trim()) return;
    createMutation.mutate(
      { slideIndex: currentSlide, content: newContent.trim() },
      {
        onSuccess: () => setNewContent(''),
      }
    );
  };

  const handleEditStart = (id: string, content: string) => {
    setEditingId(id);
    setEditDraft(content);
  };

  const handleEditSave = () => {
    if (!editingId || !editDraft.trim()) return;
    updateMutation.mutate(
      { annotationId: editingId, content: editDraft.trim(), slideIndex: currentSlide },
      {
        onSuccess: () => {
          setEditingId(null);
          setEditDraft('');
        },
        onError: () => {
          // Toast already shown in hook; keep edit mode open
        },
      }
    );
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditDraft('');
  };

  const handleDelete = (annotationId: string) => {
    setDeletingId(annotationId);
    deleteMutation.mutate(
      { annotationId, slideIndex: currentSlide },
      {
        onSettled: () => setDeletingId(null),
      }
    );
  };

  const handleNewContentKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd+Enter / Ctrl+Enter submits the form
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleCreate();
    }
  };

  // ---------------------------------------------------------------------------
  // Collapsed state — narrow toggle strip
  // ---------------------------------------------------------------------------
  if (!isOpen) {
    return (
      <div className="shrink-0 flex flex-col items-center border-l border-border/60 py-3 px-1.5 gap-2 bg-muted/10">
        <Button
          variant="ghost"
          size="icon"
          className="size-8 relative hover:bg-primary/10"
          onClick={() => setIsOpen(true)}
          aria-label="Open annotation panel"
          title={`Annotations (${annotationCount})`}
        >
          <MessageSquarePlus className="size-4" />
          {annotationCount > 0 && (
            <span className="absolute -top-1 -right-1 size-[18px] rounded-full bg-primary text-primary-foreground text-[9px] flex items-center justify-center font-bold leading-none ring-2 ring-background">
              {annotationCount > 9 ? '9+' : annotationCount}
            </span>
          )}
        </Button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Expanded panel — 320px side panel
  // ---------------------------------------------------------------------------
  return (
    <div className="shrink-0 w-80 flex flex-col border-l border-border/60 bg-background">
      {/* Panel header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/60 shrink-0 bg-muted/20">
        <div className="flex items-center gap-2 min-w-0">
          <MessageSquarePlus className="size-3.5 text-primary/70 shrink-0" />
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground truncate">
            Slide {currentSlide + 1}
          </span>
          {annotationCount > 0 && (
            <span className="text-[10px] text-muted-foreground/70 tabular-nums shrink-0">
              ({annotationCount})
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="size-6"
          onClick={() => setIsOpen(false)}
          aria-label="Close annotation panel"
        >
          <ChevronRight className="size-3.5" />
        </Button>
      </div>

      {/* Annotation list */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-3 space-y-3">
          {isLoading ? (
            <div
              className="flex items-center justify-center py-8"
              role="status"
              aria-label="Loading annotations"
            >
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-primary" />
            </div>
          ) : isError ? (
            <p className="text-sm text-destructive text-center py-8">
              Failed to load annotations. Please try again.
            </p>
          ) : annotations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
              <div className="size-10 rounded-full bg-muted/80 flex items-center justify-center mb-3">
                <MessageSquarePlus className="size-4 text-muted-foreground/60" />
              </div>
              <p className="text-xs text-muted-foreground">No annotations on this slide yet.</p>
            </div>
          ) : (
            annotations.map((annotation) => (
              <AnnotationCard
                key={annotation.id}
                annotation={annotation}
                isOwner={annotation.userId === currentUserId}
                onEdit={handleEditStart}
                onDelete={handleDelete}
                editingId={editingId}
                editDraft={editDraft}
                onEditDraftChange={setEditDraft}
                onEditSave={handleEditSave}
                onEditCancel={handleEditCancel}
                isUpdating={updateMutation.isPending}
                isDeleting={deletingId === annotation.id}
              />
            ))
          )}
        </div>
      </ScrollArea>

      {/* New annotation form */}
      <div className="shrink-0 p-3 border-t border-border/60 space-y-2 bg-muted/10">
        <Textarea
          placeholder="Add a note..."
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          onKeyDown={handleNewContentKeyDown}
          className="min-h-[72px] text-sm resize-none bg-background"
          aria-label="New annotation content"
          disabled={createMutation.isPending}
        />
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-muted-foreground/60">
            {newContent.trim() ? 'Cmd+Enter to submit' : ''}
          </span>
          <Button
            size="sm"
            className="h-7 px-3 text-xs"
            onClick={handleCreate}
            disabled={!newContent.trim() || createMutation.isPending}
          >
            {createMutation.isPending ? 'Adding...' : 'Add'}
          </Button>
        </div>
      </div>
    </div>
  );
}
