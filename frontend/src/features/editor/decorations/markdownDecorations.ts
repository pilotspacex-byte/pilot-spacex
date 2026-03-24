import type * as monacoNs from 'monaco-editor';
import './markdownDecorations.css';

/* ── Exported regex patterns ──────────────────────────────────────── */

/** Matches heading lines: # H1, ## H2, ### H3 (requires space after #) */
export const HEADING_REGEX = /^(#{1,3})\s+/;

/** Matches **bold** text (greedy between double asterisks) */
export const BOLD_REGEX = /\*\*(.+?)\*\*/;

/**
 * Matches *italic* or _italic_ text.
 * Requires word boundary or whitespace around underscores to avoid
 * matching snake_case_identifiers.
 */
export const ITALIC_REGEX = /(?<!\w)(?:\*([^*]+?)\*|_([^_]+?)_)(?!\w)/;

/** Matches `inline code` */
export const INLINE_CODE_REGEX = /`([^`]+?)`/;

/** Matches list items: - item, * item, 1. item (with optional leading spaces) */
export const LIST_REGEX = /^(\s*)([-*]|\d+\.)\s/;

/** Matches blockquote lines: > quote (must start at beginning of line) */
export const BLOCKQUOTE_REGEX = /^>\s/;

/* ── Decoration types ─────────────────────────────────────────────── */

export interface MarkdownDecoration {
  type: 'heading' | 'bold' | 'italic' | 'code' | 'list' | 'blockquote';
  /** 1-based column start (inclusive) */
  startCol: number;
  /** 1-based column end (exclusive) */
  endCol: number;
  /** Heading level (1-3), only for heading type */
  level?: number;
  /** CSS class name to apply */
  className: string;
  /** Whether this is a glyph margin decoration */
  isGlyphMargin?: boolean;
}

/* ── Hoisted global-flag regexes (reused per line, reset lastIndex) ── */

const BOLD_REGEX_G = /\*\*(.+?)\*\*/g;
const ITALIC_REGEX_G = /(?<!\w)(?:\*([^*]+?)\*|_([^_]+?)_)(?!\w)/g;
const INLINE_CODE_REGEX_G = /`([^`]+?)`/g;

/* ── CSS class mapping ─────────────────────────────────────────────── */

const HEADING_CLASSES: Record<number, string> = {
  1: 'md-h1',
  2: 'md-h2',
  3: 'md-h3',
};

/* ── Pure parse function (testable without Monaco) ────────────────── */

/**
 * Parse a single line of text for markdown formatting.
 * Returns an array of MarkdownDecoration objects.
 *
 * Column numbers are 1-based (Monaco convention).
 */
export function parseMarkdownLine(line: string): MarkdownDecoration[] {
  const decorations: MarkdownDecoration[] = [];

  // Heading detection (whole line)
  const headingMatch = HEADING_REGEX.exec(line);
  if (headingMatch) {
    const level = headingMatch[1]!.length;
    decorations.push({
      type: 'heading',
      startCol: 1,
      endCol: line.length + 1,
      level,
      className: HEADING_CLASSES[level] ?? 'md-h3',
    });
  }

  // Bold: **text**
  {
    const regex = BOLD_REGEX_G;
    regex.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(line)) !== null) {
      decorations.push({
        type: 'bold',
        startCol: match.index + 1, // 1-based
        endCol: match.index + match[0].length + 1,
        className: 'md-bold',
      });
    }
  }

  // Italic: *text* or _text_ (not within words)
  // Skip italic matches that overlap with bold ranges (e.g., *bold* inside **bold**)
  {
    const boldRanges = decorations
      .filter((d) => d.type === 'bold')
      .map((d) => [d.startCol, d.endCol] as const);

    const regex = ITALIC_REGEX_G;
    regex.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(line)) !== null) {
      const startCol = match.index + 1;
      const endCol = match.index + match[0].length + 1;
      // Skip if this italic range is contained within a bold range
      const isInsideBold = boldRanges.some(([bs, be]) => startCol >= bs && endCol <= be);
      if (!isInsideBold) {
        decorations.push({
          type: 'italic',
          startCol,
          endCol,
          className: 'md-italic',
        });
      }
    }
  }

  // Inline code: `text`
  {
    const regex = INLINE_CODE_REGEX_G;
    regex.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(line)) !== null) {
      decorations.push({
        type: 'code',
        startCol: match.index + 1,
        endCol: match.index + match[0].length + 1,
        className: 'md-inline-code',
      });
    }
  }

  // List items
  {
    const listMatch = LIST_REGEX.exec(line);
    if (listMatch) {
      const bulletStart = listMatch[1]!.length;
      const bulletEnd = bulletStart + listMatch[2]!.length;
      decorations.push({
        type: 'list',
        startCol: bulletStart + 1,
        endCol: bulletEnd + 1,
        className: 'md-list-bullet',
      });
    }
  }

  // Blockquote
  if (BLOCKQUOTE_REGEX.exec(line)) {
    decorations.push({
      type: 'blockquote',
      startCol: 1,
      endCol: line.length + 1,
      className: 'md-blockquote-glyph',
      isGlyphMargin: true,
    });
  }

  return decorations;
}

/* ── Monaco integration ───────────────────────────────────────────── */

/**
 * Apply live markdown decorations to a Monaco editor.
 *
 * Scans lines on each content change and applies inline decorations
 * (className-based) for headings, bold, italic, code, lists, and blockquotes.
 *
 * Returns an IDisposable that cleans up the content change listener.
 */
export function applyMarkdownDecorations(
  editor: monacoNs.editor.IStandaloneCodeEditor,
  monacoInstance: typeof monacoNs
): monacoNs.IDisposable {
  let decorationIds: string[] = [];

  function updateDecorations() {
    const model = editor.getModel();
    if (!model) return;

    const lineCount = model.getLineCount();
    const newDecorations: monacoNs.editor.IModelDeltaDecoration[] = [];

    for (let lineNumber = 1; lineNumber <= lineCount; lineNumber++) {
      const lineContent = model.getLineContent(lineNumber);
      const parsed = parseMarkdownLine(lineContent);

      for (const dec of parsed) {
        if (dec.isGlyphMargin) {
          newDecorations.push({
            range: new monacoInstance.Range(lineNumber, 1, lineNumber, 1),
            options: {
              glyphMarginClassName: dec.className,
            },
          });
        } else {
          newDecorations.push({
            range: new monacoInstance.Range(lineNumber, dec.startCol, lineNumber, dec.endCol),
            options: {
              inlineClassName: dec.className,
            },
          });
        }
      }
    }

    decorationIds = editor.deltaDecorations(decorationIds, newDecorations);
  }

  // Apply immediately
  updateDecorations();

  // Re-apply on content changes (debounced via rAF to avoid per-keystroke full scans)
  let rafId: number | null = null;
  const disposable = editor.onDidChangeModelContent(() => {
    if (rafId !== null) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => {
      rafId = null;
      updateDecorations();
    });
  });

  return {
    dispose() {
      if (rafId !== null) cancelAnimationFrame(rafId);
      disposable.dispose();
      decorationIds = editor.deltaDecorations(decorationIds, []);
    },
  };
}
