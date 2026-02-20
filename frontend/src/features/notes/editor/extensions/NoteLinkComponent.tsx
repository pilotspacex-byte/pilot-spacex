'use client';

/**
 * NoteLinkComponent - React NodeView for inline note link chips.
 *
 * Renders a pill/chip with FileText icon + note title.
 * Title is resolved at render time via the extension's editor storage
 * (R-4 fix: no stale titles stored in ProseMirror attrs).
 *
 * @see tmp/note-editor-ui-design.md Section 4a - Inline Chip
 */
import { useCallback, useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { FileText } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

/**
 * NoteLinkComponent renders an inline note reference chip.
 * Title is resolved from editor storage (populated by suggestion command + mount fetch).
 */
export function NoteLinkComponent({ node, extension, editor }: NodeViewProps) {
  const params = useParams<{ workspaceSlug: string }>();
  const router = useRouter();
  const workspaceSlug = params.workspaceSlug ?? extension.options.workspaceSlug ?? '';
  const noteId = (node.attrs.noteId as string) || '';

  // Read title directly from storage on each render
  const storage = extension.storage as { noteTitles?: Map<string, string> } | undefined;
  const storedTitle = storage?.noteTitles?.get(noteId);
  const title = storedTitle || null;
  const isBroken = storedTitle === '';

  // Track a render counter to force re-render when this component's title changes
  // (extension.storage is a mutable ref; its identity never changes)
  const [, setTick] = useState(0);

  useEffect(() => {
    // Only re-render when this specific note's title changes in storage
    let currentTitle = storage?.noteTitles?.get(noteId);
    const onTransaction = () => {
      const newTitle = storage?.noteTitles?.get(noteId);
      if (newTitle !== currentTitle) {
        currentTitle = newTitle;
        setTick((t) => t + 1);
      }
    };
    editor.on('transaction', onTransaction);
    return () => {
      editor.off('transaction', onTransaction);
    };
  }, [editor, noteId, storage]);

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (isBroken) return;

      const onClick = extension.options.onClick as ((noteId: string) => void) | undefined;
      if (onClick) {
        onClick(noteId);
      } else if (workspaceSlug) {
        router.push(`/${workspaceSlug}/notes/${noteId}`);
      }
    },
    [noteId, workspaceSlug, isBroken, extension.options.onClick, router]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        handleClick(e as unknown as React.MouseEvent);
      }
    },
    [handleClick]
  );

  const displayTitle = isBroken ? 'Note not found' : (title ?? '');

  return (
    <NodeViewWrapper as="span" className="inline align-middle">
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            role="link"
            tabIndex={0}
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            aria-label={
              title === null && !isBroken ? 'Loading linked note' : `Linked note: ${displayTitle}`
            }
            className={cn(
              'note-link-node',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30',
              isBroken && 'broken-link'
            )}
            data-note-id={noteId}
          >
            <FileText
              className={cn(
                'h-3 w-3 flex-shrink-0',
                isBroken ? 'text-destructive' : 'text-muted-foreground'
              )}
            />
            {title === null && !isBroken ? (
              <span className="inline-block animate-pulse bg-muted rounded w-16 h-3" />
            ) : (
              <span className="truncate max-w-[180px]">{displayTitle}</span>
            )}
          </span>
        </TooltipTrigger>
        {isBroken && <TooltipContent>This note has been deleted or is unavailable.</TooltipContent>}
      </Tooltip>
    </NodeViewWrapper>
  );
}

export default NoteLinkComponent;
