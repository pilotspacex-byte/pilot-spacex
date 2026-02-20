/**
 * useNoteHealth - Client-side note health computation hook.
 *
 * Computes:
 * - extractableCount: Paragraphs containing 2+ actionable verb patterns
 * - clarityIssueCount: Annotations of type 'question' or 'warning' from MarginAnnotationStore
 * - linkedIssues: Passthrough from props
 * - suggestedPrompts: Context-derived prompts for ChatView
 *
 * Runs on noteId change and debounced 5s after content changes.
 *
 * @see T023 Note Health Indicator
 */
import { useState, useEffect, useRef, useMemo } from 'react';
import type { Editor } from '@tiptap/core';
import type { LinkedIssueBrief } from '@/types';
import { getAIStore } from '@/stores/ai/AIStore';

/** Actionable verb patterns for extractable issue detection */
const ACTIONABLE_VERBS = [
  'implement',
  'fix',
  'add',
  'create',
  'update',
  'remove',
  'build',
  'design',
  'refactor',
  'test',
  'deploy',
  'migrate',
] as const;

/** Pre-compiled regex matching any actionable verb (word boundary, case-insensitive) */
const VERB_PATTERN = new RegExp(`\\b(${ACTIONABLE_VERBS.join('|')})\\b`, 'gi');

/** Annotation types that indicate clarity issues */
const CLARITY_ANNOTATION_TYPES = new Set(['question', 'warning']);

export interface NoteHealthData {
  /** Number of paragraphs with 2+ actionable verb patterns */
  extractableCount: number;
  /** Number of clarity-related annotations (question/warning) */
  clarityIssueCount: number;
  /** Linked issues passthrough */
  linkedIssues: LinkedIssueBrief[];
  /** Context-derived suggested prompts for ChatView */
  suggestedPrompts: string[];
  /** Whether health data is being computed */
  isComputing: boolean;
}

/** Simple hash for content change detection */
function hashContent(text: string): number {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    const chr = text.charCodeAt(i);
    hash = ((hash << 5) - hash + chr) | 0;
  }
  return hash;
}

/** Count actionable verb matches in a text string */
export function countActionableVerbs(text: string): number {
  const matches = text.match(VERB_PATTERN);
  return matches ? matches.length : 0;
}

/**
 * Scan editor document for paragraphs containing 2+ actionable verbs.
 * Returns the count of such paragraphs.
 */
function computeExtractableCount(editor: Editor): number {
  let count = 0;
  editor.state.doc.forEach((node) => {
    if (node.type.name === 'paragraph' || node.type.name === 'listItem') {
      const text = node.textContent;
      if (countActionableVerbs(text) >= 2) {
        count++;
      }
    }
  });
  return count;
}

/**
 * Count clarity-related annotations from MarginAnnotationStore.
 * Types considered: 'question', 'warning'
 */
function computeClarityIssueCount(noteId: string): number {
  const aiStore = getAIStore();
  const annotations = aiStore.marginAnnotation.getAnnotationsForNote(noteId);
  return annotations.filter((a) => CLARITY_ANNOTATION_TYPES.has(a.type) && a.status === 'pending')
    .length;
}

/** Build suggested prompts based on health data */
function buildSuggestedPrompts(
  extractableCount: number,
  clarityIssueCount: number,
  linkedIssueCount: number
): string[] {
  const prompts: string[] = [];

  if (extractableCount > 0) {
    prompts.push(
      `Extract ${extractableCount} actionable item${extractableCount > 1 ? 's' : ''} as issues`
    );
  }

  if (clarityIssueCount > 0) {
    prompts.push(
      `Improve clarity in ${clarityIssueCount} section${clarityIssueCount > 1 ? 's' : ''}`
    );
  }

  if (linkedIssueCount > 0) {
    prompts.push(
      `Summarize progress on ${linkedIssueCount} linked issue${linkedIssueCount > 1 ? 's' : ''}`
    );
  }

  if (extractableCount === 0 && clarityIssueCount === 0) {
    prompts.push('Analyze this note for improvements');
  }

  return prompts;
}

const DEBOUNCE_MS = 5000;

export function useNoteHealth(
  noteId: string,
  editor: Editor | null,
  linkedIssues: LinkedIssueBrief[]
): NoteHealthData {
  // Revision counter triggers recomputation; incremented by debounced editor updates
  const [revision, setRevision] = useState(0);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Content hash for deduplicating editor updates — accessed only in event callback, not render
  const contentHashRef = useRef<number>(0);

  /** Compute health synchronously from current state */
  const { extractableCount, clarityIssueCount } = useMemo(() => {
    // revision is read to establish dependency for debounced updates
    void revision;
    if (!editor || editor.isDestroyed) {
      return { extractableCount: 0, clarityIssueCount: 0 };
    }
    return {
      extractableCount: computeExtractableCount(editor),
      clarityIssueCount: computeClarityIssueCount(noteId),
    };
  }, [editor, noteId, revision]);

  /** Subscribe to editor updates; debounce recomputation by 5s.
   *  noteId in deps ensures content hash resets when switching notes. */
  useEffect(() => {
    if (!editor || editor.isDestroyed) return;

    // Reset content hash for new note
    contentHashRef.current = 0;

    const handleUpdate = () => {
      const text = editor.state.doc.textContent;
      const newHash = hashContent(text);

      if (newHash === contentHashRef.current) return;
      contentHashRef.current = newHash;

      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      debounceTimerRef.current = setTimeout(() => {
        setRevision((r) => r + 1);
      }, DEBOUNCE_MS);
    };

    editor.on('update', handleUpdate);

    return () => {
      editor.off('update', handleUpdate);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
    };
  }, [editor, noteId]);

  const suggestedPrompts = useMemo(
    () => buildSuggestedPrompts(extractableCount, clarityIssueCount, linkedIssues.length),
    [extractableCount, clarityIssueCount, linkedIssues.length]
  );

  return {
    extractableCount,
    clarityIssueCount,
    linkedIssues,
    suggestedPrompts,
    isComputing: false,
  };
}
