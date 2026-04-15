'use client';

/**
 * useTocHeadings - Extracts h1/h2/h3 headings from TipTap editor state
 * Phase 78: Living Specs sidebar — Table of Contents panel
 */
import { useEffect, useState } from 'react';
import type { Editor } from '@tiptap/react';

export interface TocHeading {
  id: string;
  text: string;
  level: 1 | 2 | 3;
  pos: number;
}

/**
 * Slugify heading text into a stable DOM id.
 * Keeps letters, digits, and hyphens. Collapses whitespace to hyphens.
 */
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/**
 * Extracts heading nodes from TipTap editor JSON and returns a flat list.
 * Recalculates on every editor `update` event.
 *
 * Returns empty list when editor is null or has < 3 headings (caller can decide to hide TOC).
 */
export function useTocHeadings(editor: Editor | null): { headings: TocHeading[] } {
  const [headings, setHeadings] = useState<TocHeading[]>([]);

  useEffect(() => {
    if (!editor) {
      setHeadings([]);
      return;
    }

    function extractHeadings() {
      if (!editor) return;
      const doc = editor.getJSON();
      const nodes = doc.content ?? [];
      const result: TocHeading[] = [];
      let pos = 0;

      for (const node of nodes) {
        // Approximate position for scroll targeting (1 char per node boundary)
        pos += 1;

        if (node.type === 'heading') {
          const level = (node.attrs as Record<string, unknown>)?.level as number;
          if (level === 1 || level === 2 || level === 3) {
            // Extract text from inline content nodes
            // node.content is JSONContent[] from TipTap getJSON()
            const inlines = (node.content ?? []) as Array<{ text?: string }>;
            const text = inlines.map((inline) => inline.text ?? '').join('');

            if (text.trim()) {
              result.push({
                id: `toc-${slugify(text) || `heading-${result.length}`}`,
                text: text.trim(),
                level: level as 1 | 2 | 3,
                pos,
              });
            }
          }
        }

        // Rough pos increment for content inside node
        if (Array.isArray(node.content)) {
          pos += (node.content as unknown[]).length;
        }
      }

      setHeadings(result);
    }

    // Extract immediately on mount
    extractHeadings();

    // Re-extract on every editor update
    editor.on('update', extractHeadings);
    return () => {
      editor.off('update', extractHeadings);
    };
  }, [editor]);

  return { headings };
}
