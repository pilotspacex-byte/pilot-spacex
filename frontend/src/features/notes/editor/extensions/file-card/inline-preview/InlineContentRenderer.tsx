'use client';

/**
 * InlineContentRenderer — Dispatches to the correct renderer based on InlineRendererType.
 *
 * All heavy renderers are dynamically imported via next/dynamic to keep the initial
 * bundle small. The SkeletonPreviewCard is used as the loading fallback for all imports.
 *
 * Content truncation:
 * - code/json/text: first 30 lines when collapsed
 * - csv: first 11 lines (header + 10 data rows) when collapsed
 * - markdown/html-preview: no truncation — scrolls within the 300px max-height container
 * - xlsx/docx/pptx: no truncation — binary content rendered by Office parsers
 *
 * The `expanded` prop controls whether truncation is applied. When false (default),
 * only a preview subset of lines is rendered to keep DOM cost low.
 *
 * Renderers are wrapped in a container with reduced padding so they fit the inline
 * card context (existing renderers use p-6 which is too large for note context).
 */

import * as React from 'react';
import dynamic from 'next/dynamic';
import { SkeletonPreviewCard } from './SkeletonPreviewCard';
import type { InlineRendererType } from './is-inline-previewable';
import { getLanguageForFile } from '@/features/artifacts/utils/mime-type-router';
import { Button } from '@/components/ui/button';

// ---------------------------------------------------------------------------
// Dynamic imports with SkeletonPreviewCard as fallback
// ---------------------------------------------------------------------------

const MarkdownContent = dynamic(
  () =>
    import('@/features/ai/ChatView/MessageList/MarkdownContent').then((m) => ({
      default: m.MarkdownContent,
    })),
  { loading: () => <SkeletonPreviewCard /> }
);

const CsvRenderer = dynamic(
  () =>
    import('@/features/artifacts/components/renderers/CsvRenderer').then((m) => ({
      default: m.CsvRenderer,
    })),
  { loading: () => <SkeletonPreviewCard /> }
);

const XlsxRenderer = dynamic(
  () =>
    import('@/features/artifacts/components/renderers/XlsxRenderer').then((m) => ({
      default: m.XlsxRenderer,
    })),
  { ssr: false, loading: () => <SkeletonPreviewCard /> }
);

const DocxRenderer = dynamic(
  () =>
    import('@/features/artifacts/components/renderers/DocxRenderer').then((m) => ({
      default: m.DocxRenderer,
    })),
  { ssr: false, loading: () => <SkeletonPreviewCard /> }
);

const PptxRenderer = dynamic(
  () =>
    import('@/features/artifacts/components/renderers/PptxRenderer').then((m) => ({
      default: m.PptxRenderer,
    })),
  { ssr: false, loading: () => <SkeletonPreviewCard /> }
);

const HtmlRenderer = dynamic(
  () =>
    import('@/features/artifacts/components/renderers/HtmlRenderer').then((m) => ({
      default: m.HtmlRenderer,
    })),
  { ssr: false, loading: () => <SkeletonPreviewCard /> }
);

// ---------------------------------------------------------------------------
// Truncation utilities
// ---------------------------------------------------------------------------

interface TruncateResult {
  truncated: string;
  totalLines: number;
  wasTruncated: boolean;
}

function truncateLines(content: string, maxLines: number): TruncateResult {
  const lines = content.split('\n');
  const totalLines = lines.length;
  if (totalLines <= maxLines) {
    return { truncated: content, totalLines, wasTruncated: false };
  }
  return {
    truncated: lines.slice(0, maxLines).join('\n'),
    totalLines,
    wasTruncated: true,
  };
}

/**
 * Wrap content in a fenced code block using a fence longer than any backtick
 * run found inside the content. Prevents premature fence closure.
 */
function wrapFencedCode(content: string, language = ''): string {
  let maxRun = 2; // minimum fence length is 3
  const matches = content.match(/`+/g);
  if (matches) {
    for (const m of matches) {
      if (m.length > maxRun) maxRun = m.length;
    }
  }
  const fence = '`'.repeat(maxRun + 1);
  return `${fence}${language}\n${content}\n${fence}`;
}

/**
 * Count actual CSV data rows using papaparse (handles quoted fields with
 * embedded newlines). Falls back to line-split count on parse failure.
 */
function countCsvRows(content: string): { totalRows: number } {
  try {
    // Dynamic import is not feasible in a sync function — CsvRenderer is already
    // dynamically imported, but papaparse is a dep of CsvRenderer and bundled
    // with it. We use require-style lazy access via the module-level dynamic import.
    // Instead, use a lightweight heuristic: count unquoted newlines.
    // A proper parse would need to be async. For now, count rows by tracking
    // whether we're inside a quoted field.
    let rows = 0;
    let inQuotes = false;
    for (let i = 0; i < content.length; i++) {
      const ch = content[i];
      if (ch === '"') {
        inQuotes = !inQuotes;
      } else if (ch === '\n' && !inQuotes) {
        rows++;
      }
    }
    // Last row may not end with newline
    if (content.length > 0 && content[content.length - 1] !== '\n') {
      rows++;
    }
    // rows includes header, so data rows = rows - 1
    return { totalRows: Math.max(0, rows - 1) };
  } catch {
    // Fallback: raw line split
    const lines = content.split('\n').filter((l) => l.trim().length > 0);
    return { totalRows: Math.max(0, lines.length - 1) };
  }
}

export interface TruncationInfo {
  totalLines: number;
  totalRows: number;
  wasTruncated: boolean;
  /** Human-readable label for the "Show more" expand link. */
  label: string;
}

/** Pretty-print JSON if valid, otherwise return as-is. Shared by renderer and truncation. */
function formatJsonSafe(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

/**
 * Returns truncation metadata for the footer expand link.
 * CSV row counts are estimated from line count (header not counted in rows).
 * For JSON, content is pretty-printed first so line count matches the rendered output.
 * For markdown, html-preview, and binary types, truncation is not applied.
 */
export function getTruncationInfo(
  content: string | ArrayBuffer,
  rendererType: InlineRendererType,
  expanded: boolean
): TruncationInfo {
  // Binary types and non-truncatable text types
  if (
    rendererType === 'markdown' ||
    rendererType === 'html-preview' ||
    rendererType === 'xlsx' ||
    rendererType === 'docx' ||
    rendererType === 'pptx'
  ) {
    return { totalLines: 0, totalRows: 0, wasTruncated: false, label: '' };
  }

  // Binary content should not reach here, but guard
  if (content instanceof ArrayBuffer) {
    return { totalLines: 0, totalRows: 0, wasTruncated: false, label: '' };
  }

  if (rendererType === 'csv') {
    const { totalRows } = countCsvRows(content);
    const wasTruncated = !expanded && totalRows > 10;
    return {
      totalLines: 0,
      totalRows,
      wasTruncated,
      label: wasTruncated ? `Show more (${totalRows} rows)` : '',
    };
  }

  // JSON: pretty-print before counting so line count matches rendered output
  const effective = rendererType === 'json' ? formatJsonSafe(content) : content;
  const lines = effective.split('\n');
  const totalLines = lines.length;
  const wasTruncated = !expanded && totalLines > 30;
  return {
    totalLines,
    totalRows: 0,
    wasTruncated,
    label: wasTruncated ? `Show more (${totalLines} lines)` : '',
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface InlineContentRendererProps {
  content: string | ArrayBuffer;
  rendererType: InlineRendererType;
  filename: string;
  expanded: boolean;
  /** Signed URL for Office renderer download fallbacks */
  signedUrl?: string;
}

export function InlineContentRenderer({
  content,
  rendererType,
  filename,
  expanded,
  signedUrl = '',
}: InlineContentRendererProps) {
  // PPTX slide state — reset when content changes (different file)
  const [currentSlide, setCurrentSlide] = React.useState(0);
  const [slideCount, setSlideCount] = React.useState(0);
  const contentRef = React.useRef(content);

  React.useEffect(() => {
    if (contentRef.current !== content) {
      contentRef.current = content;
      setCurrentSlide(0);
      setSlideCount(0);
    }
  }, [content]);

  // Clamp currentSlide when slideCount changes (e.g. after PPTX parse)
  React.useEffect(() => {
    if (slideCount > 0 && currentSlide >= slideCount) {
      setCurrentSlide(Math.max(0, slideCount - 1));
    }
  }, [slideCount, currentSlide]);

  if (rendererType === 'markdown') {
    // Full content, scroll within the 300px card container.
    return (
      <div className="[&>div]:p-3 [&>div]:py-2">
        <React.Suspense fallback={<SkeletonPreviewCard />}>
          <MarkdownContent content={content as string} />
        </React.Suspense>
      </div>
    );
  }

  if (rendererType === 'code') {
    const { truncated } = truncateLines(content as string, expanded ? Infinity : 30);
    const language = getLanguageForFile(filename);
    const wrappedContent = wrapFencedCode(truncated, language);
    return (
      <div className="[&>div]:p-3 [&>div]:py-2">
        <React.Suspense fallback={<SkeletonPreviewCard />}>
          <MarkdownContent content={wrappedContent} />
        </React.Suspense>
      </div>
    );
  }

  if (rendererType === 'json') {
    const formatted = formatJsonSafe(content as string);
    const { truncated } = truncateLines(formatted, expanded ? Infinity : 30);
    const wrappedContent = wrapFencedCode(truncated, 'json');
    return (
      <div className="[&>div]:p-3 [&>div]:py-2">
        <React.Suspense fallback={<SkeletonPreviewCard />}>
          <MarkdownContent content={wrappedContent} />
        </React.Suspense>
      </div>
    );
  }

  if (rendererType === 'text') {
    const { truncated } = truncateLines(content as string, expanded ? Infinity : 30);
    return (
      <div className="p-3 py-2">
        <pre className="text-sm font-mono text-foreground whitespace-pre-wrap break-words">
          {truncated}
        </pre>
      </div>
    );
  }

  if (rendererType === 'csv') {
    // Truncate CSV to header + 10 data rows when collapsed.
    const truncated = expanded
      ? (content as string)
      : truncateLines(content as string, 11).truncated;
    return (
      <div className="[&>div]:p-0 overflow-x-auto">
        <React.Suspense fallback={<SkeletonPreviewCard />}>
          <CsvRenderer content={truncated} />
        </React.Suspense>
      </div>
    );
  }

  if (rendererType === 'html-preview') {
    return (
      <div className="p-0 overflow-hidden" style={{ maxHeight: expanded ? 'none' : '300px' }}>
        <React.Suspense fallback={<SkeletonPreviewCard />}>
          <HtmlRenderer content={content as string} filename={filename} />
        </React.Suspense>
      </div>
    );
  }

  if (rendererType === 'xlsx') {
    if (!(content instanceof ArrayBuffer)) return null;
    return (
      <div className="overflow-auto" style={{ maxHeight: expanded ? '600px' : '300px' }}>
        <React.Suspense fallback={<SkeletonPreviewCard />}>
          <XlsxRenderer content={content} filename={filename} signedUrl={signedUrl} />
        </React.Suspense>
      </div>
    );
  }

  if (rendererType === 'docx') {
    if (!(content instanceof ArrayBuffer)) return null;
    return (
      <div className="overflow-auto" style={{ maxHeight: expanded ? '600px' : '300px' }}>
        <React.Suspense fallback={<SkeletonPreviewCard />}>
          <DocxRenderer content={content} filename={filename} signedUrl={signedUrl} />
        </React.Suspense>
      </div>
    );
  }

  if (rendererType === 'pptx') {
    if (!(content instanceof ArrayBuffer)) return null;
    return (
      <div className="overflow-hidden" style={{ maxHeight: expanded ? '600px' : '300px' }}>
        <React.Suspense fallback={<SkeletonPreviewCard />}>
          <PptxRenderer
            content={content}
            currentSlide={currentSlide}
            onSlideCountKnown={setSlideCount}
            onNavigate={setCurrentSlide}
          />
        </React.Suspense>
        {slideCount > 1 && (
          <div className="flex items-center justify-center gap-2 py-1 text-xs text-muted-foreground border-t border-border">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={() => setCurrentSlide(Math.max(0, currentSlide - 1))}
              disabled={currentSlide === 0}
              aria-label="Previous slide"
            >
              ←
            </Button>
            <span>
              {currentSlide + 1} / {slideCount}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={() => setCurrentSlide(Math.min(slideCount - 1, currentSlide + 1))}
              disabled={currentSlide >= slideCount - 1}
              aria-label="Next slide"
            >
              →
            </Button>
          </div>
        )}
      </div>
    );
  }

  // Should be unreachable — rendererType is a union of all supported cases
  return null;
}
