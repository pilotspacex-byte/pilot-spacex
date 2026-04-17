'use client';

/**
 * NoteBody — read-only preview of a note inside the PeekDrawer.
 *
 * The peek-drawer preview is intentionally light:
 *   - title, updated timestamp
 *   - flattened plain-text body (first ~2000 chars) from TipTap JSON
 *
 * For full editing the user should click "Full view" in the drawer header
 * (navigates to /{slug}/notes/{id}) — the heavy TipTap editor is NOT mounted
 * in the drawer to avoid the React 19 + MobX + TipTap flushSync collision
 * documented in `.claude/rules/tiptap.md`.
 *
 * NOT observer() — this body is a plain TanStack-Query consumer.
 */

import { AlertTriangle } from 'lucide-react';
import { useNote } from '@/features/notes/hooks/useNote';
import { Skeleton } from '@/components/ui/skeleton';
import type { JSONContent } from '@/types';

interface NoteBodyProps {
  workspaceId: string;
  noteId: string;
  /** NOTE | SPEC | DECISION — drives header label but not body rendering. */
  variant: 'NOTE' | 'SPEC' | 'DECISION';
}

const MAX_PREVIEW_CHARS = 2000;

/**
 * Flatten a TipTap ProseMirror JSON doc into a plain-text string.
 *
 * Intentionally simple — preserves paragraph breaks but drops marks, tables,
 * and node attrs. The goal is a glanceable preview, not a fidelity render.
 */
function flattenJsonContent(doc: JSONContent | undefined, limit = MAX_PREVIEW_CHARS): string {
  if (!doc) return '';
  const buffer: string[] = [];
  let remaining = limit;

  const walk = (node: JSONContent): void => {
    if (remaining <= 0) return;
    if (node.text) {
      const slice = node.text.slice(0, remaining);
      buffer.push(slice);
      remaining -= slice.length;
      return;
    }
    for (const child of node.content ?? []) {
      walk(child);
      if (remaining <= 0) return;
    }
    // Insert paragraph breaks between block-level nodes
    if (
      node.type === 'paragraph' ||
      node.type === 'heading' ||
      node.type === 'listItem' ||
      node.type === 'blockquote'
    ) {
      buffer.push('\n\n');
    }
  };

  walk(doc);
  return buffer.join('').trim();
}

export function NoteBody({ workspaceId, noteId, variant }: NoteBodyProps) {
  const { data: note, isLoading, isError, error } = useNote({ workspaceId, noteId });

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
        <div className="pt-4 space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    );
  }

  if (isError || !note) {
    const status = (error as { status?: number } | null)?.status;
    const message =
      status === 404
        ? `This ${variant.toLowerCase()} no longer exists or you do not have access.`
        : 'Failed to load preview. Try refreshing or open the full view.';
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center px-6">
        <AlertTriangle className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    );
  }

  const preview = flattenJsonContent(note.content);
  const isTruncated = preview.length >= MAX_PREVIEW_CHARS;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="space-y-2 mb-5">
          {note.iconEmoji ? (
            <div className="text-3xl leading-none" aria-hidden="true">
              {note.iconEmoji}
            </div>
          ) : null}
          <h1 className="text-xl font-semibold leading-tight text-foreground">{note.title}</h1>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="font-mono tabular-nums">
              Updated {new Date(note.updatedAt).toLocaleDateString()}
            </span>
            {note.wordCount ? (
              <span>
                {note.wordCount} word{note.wordCount === 1 ? '' : 's'}
              </span>
            ) : null}
          </div>
        </div>

        {note.summary ? (
          <div className="mb-5 rounded-[12px] border border-border/60 bg-muted/40 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground mb-1.5">
              Summary
            </p>
            <p className="text-sm text-foreground leading-relaxed">{note.summary}</p>
          </div>
        ) : null}

        {preview ? (
          <div className="prose prose-sm max-w-none text-foreground">
            {preview.split(/\n\n+/).map((paragraph, idx) => (
              <p key={idx} className="whitespace-pre-wrap leading-relaxed text-[14px]">
                {paragraph}
              </p>
            ))}
            {isTruncated ? (
              <p className="text-xs text-muted-foreground italic">
                Preview truncated — open the full view to see the rest.
              </p>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            This {variant.toLowerCase()} has no content yet.
          </p>
        )}
      </div>
    </div>
  );
}
