'use client';

/**
 * PptxAnnotationPanel -- Per-slide annotation CRUD panel for PPTX previews.
 *
 * Renders alongside the slide canvas in FilePreviewModal. Supports:
 * - Create via textarea + "Add Note" button (or Cmd/Ctrl+Enter)
 * - Inline edit (owner-only) with Save/Cancel
 * - Optimistic delete (owner-only) with no confirmation dialog
 * - Collapsed strip with count badge (capped at "9+")
 * - Resets textarea and edit state on slide change
 *
 * IMPORTANT: Plain React component (NOT observer) to avoid React 19
 * flushSync issues with TipTap portals.
 */

import * as React from 'react';
import { ChevronRight, Check, MessageSquarePlus, Pencil, Trash2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { usePptxAnnotations } from '../hooks/usePptxAnnotations';

export interface PptxAnnotationPanelProps {
  workspaceId: string;
  projectId: string;
  artifactId: string;
  slideIndex: number;
  currentUserId: string;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

/** Format an ISO timestamp as a relative time string (e.g., "2m ago", "3h ago"). */
function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffSeconds = Math.max(0, Math.floor((now - then) / 1000));

  if (diffSeconds < 60) return 'just now';
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export default function PptxAnnotationPanel({
  workspaceId,
  projectId,
  artifactId,
  slideIndex,
  currentUserId,
  isCollapsed,
  onToggleCollapse,
}: PptxAnnotationPanelProps) {
  const { annotations, total, isLoading, createAnnotation, updateAnnotation, deleteAnnotation } =
    usePptxAnnotations({ workspaceId, projectId, artifactId, slideIndex });

  const [newContent, setNewContent] = React.useState('');
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editContent, setEditContent] = React.useState('');

  // Reset textarea and edit state when slide changes
  React.useEffect(() => {
    setNewContent('');
    setEditingId(null);
    setEditContent('');
  }, [slideIndex]);

  // ---- Create ----
  function handleCreate() {
    const trimmed = newContent.trim();
    if (!trimmed) return;
    createAnnotation.mutate({ content: trimmed });
    setNewContent('');
  }

  function handleCreateKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleCreate();
    }
  }

  // ---- Edit ----
  function startEdit(id: string, content: string) {
    setEditingId(id);
    setEditContent(content);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditContent('');
  }

  function saveEdit() {
    if (!editingId) return;
    const trimmed = editContent.trim();
    if (!trimmed) return;
    updateAnnotation.mutate({ annotationId: editingId, content: trimmed });
    setEditingId(null);
    setEditContent('');
  }

  // ---- Delete ----
  function handleDelete(annotationId: string) {
    deleteAnnotation.mutate({ annotationId });
  }

  // ---- Collapsed strip ----
  if (isCollapsed) {
    const badgeText = total > 9 ? '9+' : String(total);
    return (
      <div className="flex flex-col items-center py-3 px-1 border-l bg-muted/10">
        <Button
          variant="ghost"
          size="icon"
          className="size-8 relative"
          onClick={onToggleCollapse}
          aria-label="Annotations"
        >
          <MessageSquarePlus className="size-4" />
          {total > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] rounded-full bg-primary text-primary-foreground text-[10px] font-semibold flex items-center justify-center px-1">
              {badgeText}
            </span>
          )}
        </Button>
      </div>
    );
  }

  // ---- Expanded panel ----
  return (
    <div
      className="w-80 shrink-0 border-l flex flex-col bg-background"
      data-testid="annotation-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
          Annotations
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="size-7"
          onClick={onToggleCollapse}
          aria-label="Collapse annotations"
        >
          <ChevronRight className="size-4" />
        </Button>
      </div>

      {/* Annotation list */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-3 space-y-3">
          {isLoading && annotations.length === 0 && (
            <div
              className="flex items-center justify-center py-8"
              role="status"
              aria-label="Loading annotations"
            >
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-border border-t-primary" />
            </div>
          )}

          {!isLoading && annotations.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
              <MessageSquarePlus className="size-8 opacity-40" />
              <p className="text-sm">No annotations on this slide yet.</p>
            </div>
          )}

          {annotations.map((annotation) => {
            const isOwner = annotation.user_id === currentUserId;
            const isTemp = annotation.id.startsWith('temp-');
            const isEditing = editingId === annotation.id;
            const isDeleting =
              deleteAnnotation.variables?.annotationId === annotation.id &&
              deleteAnnotation.isPending;

            return (
              <div
                key={annotation.id}
                className={cn(
                  'rounded-md border p-2.5 space-y-1.5 transition-opacity',
                  (isTemp || isDeleting) && 'opacity-50'
                )}
              >
                {isEditing ? (
                  <>
                    <Textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="min-h-[60px] text-sm resize-none"
                      aria-label="Edit annotation"
                      autoFocus
                    />
                    <div className="flex items-center gap-1 justify-end">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7"
                        onClick={saveEdit}
                        aria-label="Save edit"
                      >
                        <Check className="size-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7"
                        onClick={cancelEdit}
                        aria-label="Cancel edit"
                      >
                        <X className="size-3.5" />
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-sm whitespace-pre-wrap break-words">{annotation.content}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-muted-foreground">
                        {formatRelativeTime(annotation.created_at)}
                      </span>
                      {isOwner && !isTemp && (
                        <div className="flex items-center gap-0.5">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-7"
                            onClick={() => startEdit(annotation.id, annotation.content)}
                            aria-label="Edit annotation"
                          >
                            <Pencil className="size-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-7 hover:text-destructive"
                            onClick={() => handleDelete(annotation.id)}
                            aria-label="Delete annotation"
                          >
                            <Trash2 className="size-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {/* Create form */}
      <div className="border-t p-3 space-y-2">
        <Textarea
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          onKeyDown={handleCreateKeyDown}
          placeholder="Add a note..."
          className="min-h-[60px] text-sm resize-none"
          aria-label="Add annotation"
        />
        <div className="flex items-center justify-between">
          {newContent.trim() ? (
            <span className="text-[11px] text-muted-foreground">Cmd+Enter to submit</span>
          ) : (
            <span />
          )}
          <Button
            size="sm"
            onClick={handleCreate}
            disabled={!newContent.trim() || createAnnotation.isPending}
          >
            {createAnnotation.isPending ? 'Adding...' : 'Add Note'}
          </Button>
        </div>
      </div>
    </div>
  );
}
