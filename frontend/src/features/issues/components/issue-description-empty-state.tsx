'use client';

/**
 * IssueDescriptionEmptyState - Quick-start card shown when the issue
 * description editor is empty. Offers clickable writing prompts that insert
 * H3 headings and an AI CTA that asks Pilot Space to generate a description.
 *
 * Auto-hides once the editor contains real content (anything beyond
 * the propertyBlock node + empty paragraphs).
 */

import { useCallback, useEffect, useState } from 'react';
import type { Editor } from '@tiptap/core';
import { FileText, Sparkles, Target, Wrench } from 'lucide-react';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Writing prompt definitions
// ---------------------------------------------------------------------------
const WRITING_PROMPTS = [
  { icon: Target, label: 'What problem does this solve?' },
  { icon: FileText, label: 'Acceptance criteria' },
  { icon: Wrench, label: 'Technical approach' },
] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Returns true when the editor doc has only propertyBlock + empty paragraphs. */
function isEditorEmpty(editor: Editor): boolean {
  const { doc } = editor.state;
  for (let i = 0; i < doc.childCount; i++) {
    const child = doc.child(i);
    if (child.type.name === 'propertyBlock') continue;
    if (child.type.name === 'paragraph' && child.textContent.trim() === '') continue;
    return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export interface IssueDescriptionEmptyStateProps {
  editor: Editor | null;
  onChatOpen: () => void;
  /** When provided, called instead of onChatOpen — opens chat AND sends the generate prompt. */
  onAiGenerate?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function IssueDescriptionEmptyState({
  editor,
  onChatOpen,
  onAiGenerate,
}: IssueDescriptionEmptyStateProps) {
  const [isEmpty, setIsEmpty] = useState(() => (editor ? isEditorEmpty(editor) : true));

  // Subscribe to editor updates to track emptiness
  useEffect(() => {
    if (!editor) return;

    const handleUpdate = () => setIsEmpty(isEditorEmpty(editor));
    editor.on('update', handleUpdate);
    return () => {
      editor.off('update', handleUpdate);
    };
  }, [editor]);

  // Insert a writing prompt as H3 heading + empty paragraph for continuation
  const handlePromptClick = useCallback(
    (label: string) => {
      if (!editor) return;

      const endPos = editor.state.doc.content.size;
      editor
        .chain()
        .insertContentAt(endPos, [
          {
            type: 'heading',
            attrs: { level: 3 },
            content: [{ type: 'text', text: label }],
          },
          { type: 'paragraph' },
        ])
        .focus('end')
        .run();
    },
    [editor]
  );

  if (!editor || !isEmpty) return null;

  return (
    <div
      className={cn(
        'mt-3 rounded-lg border border-dashed border-border/60',
        'bg-muted/30 px-5 py-5',
        'animate-in fade-in-0 duration-300'
      )}
    >
      {/* Header */}
      <p className="text-sm font-medium text-muted-foreground mb-3">Describe this issue</p>

      {/* Writing prompts */}
      <div className="flex flex-wrap gap-2 mb-4">
        {WRITING_PROMPTS.map(({ icon: Icon, label }) => (
          <button
            key={label}
            type="button"
            onClick={() => handlePromptClick(label)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full',
              'border border-border/50 bg-background',
              'px-3 py-1.5 text-xs text-muted-foreground',
              'hover:text-foreground hover:border-primary/40 hover:bg-primary/5',
              'transition-colors min-h-[32px]'
            )}
          >
            <Icon className="size-3.5" aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>

      {/* AI CTA */}
      <button
        type="button"
        onClick={onAiGenerate ?? onChatOpen}
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full',
          'border border-ai/30 bg-background',
          'px-3 py-1.5 text-xs text-ai',
          'hover:border-ai/50 hover:bg-ai/5 transition-colors min-h-[32px]'
        )}
      >
        <Sparkles className="size-3.5" aria-hidden="true" />
        Generate with AI Chat
      </button>

      {/* Hint */}
      <p className="mt-3 text-xs text-muted-foreground/60">
        Start typing, click a prompt, or use AI Chat for help
      </p>
    </div>
  );
}
