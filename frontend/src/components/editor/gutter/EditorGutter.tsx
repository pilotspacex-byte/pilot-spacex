'use client';

/**
 * EditorGutter - Container for the left gutter TOC and issue indicators.
 *
 * Positioned absolutely inside the scroll container so dots scroll with
 * the document. Two tracks: TOC (left 28px) and Issues (right 28px).
 *
 * @see tmp/note-editor-plan.md Section 2a
 */
import type { Editor } from '@tiptap/react';

import { cn } from '@/lib/utils';
import { GutterTOC } from './GutterTOC';
import { GutterIssueIndicators } from './GutterIssueIndicators';
import type { LinkedIssueBrief } from '@/types';

export interface EditorGutterProps {
  editor: Editor;
  linkedIssues: LinkedIssueBrief[];
  className?: string;
  onIssueClick?: (issueId: string) => void;
}

export function EditorGutter({ editor, linkedIssues, className, onIssueClick }: EditorGutterProps) {
  return (
    <div className={cn('absolute left-0 top-0 bottom-0 w-14 flex', className)}>
      {/* TOC track (left 28px) */}
      <GutterTOC editor={editor} />

      {/* Issue track (right 28px) */}
      <GutterIssueIndicators
        editor={editor}
        linkedIssues={linkedIssues}
        onIssueClick={onIssueClick}
      />
    </div>
  );
}
