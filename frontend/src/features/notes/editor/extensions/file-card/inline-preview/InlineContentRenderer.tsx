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

export interface TruncationInfo {
  totalLines: number;
  totalRows: number;
  wasTruncated: boolean;
  /** Human-readable label for the "Show more" expand link. */
  label: string;
}

/**
 * Returns truncation metadata for the footer expand link.
 * CSV row counts are estimated from line count (header not counted in rows).
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
    const lines = content.split('\n').filter((l) => l.trim().length > 0);
    // lines[0] is the header; data rows start at index 1
    const totalRows = Math.max(0, lines.length - 1);
    const wasTruncated = !expanded && totalRows > 10;
    return {
      totalLines: lines.length,
      totalRows,
      wasTruncated,
      label: wasTruncated ? `Show more (${totalRows} rows)` : '',
    };
  }

  // code / json / text
  const lines = content.split('\n');
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
  // PPTX slide state
  const [currentSlide, setCurrentSlide] = React.useState(0);
  const [slideCount, setSlideCount] = React.useState(0);

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
    const wrappedContent = '```' + language + '\n' + truncated + '\n```';
    return (
      <div className="[&>div]:p-3 [&>div]:py-2">
        <React.Suspense fallback={<SkeletonPreviewCard />}>
          <MarkdownContent content={wrappedContent} />
        </React.Suspense>
      </div>
    );
  }

  if (rendererType === 'json') {
    // Format JSON then truncate
    let formatted = content as string;
    try {
      formatted = JSON.stringify(JSON.parse(formatted), null, 2);
    } catch {
      // Malformed JSON — render as-is
    }
    const { truncated } = truncateLines(formatted, expanded ? Infinity : 30);
    const wrappedContent = '```json\n' + truncated + '\n```';
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
            <button
              onClick={() => setCurrentSlide(Math.max(0, currentSlide - 1))}
              disabled={currentSlide === 0}
              className="px-2 py-0.5 rounded hover:bg-muted disabled:opacity-40"
            >
              ←
            </button>
            <span>
              {currentSlide + 1} / {slideCount}
            </span>
            <button
              onClick={() => setCurrentSlide(Math.min(slideCount - 1, currentSlide + 1))}
              disabled={currentSlide >= slideCount - 1}
              className="px-2 py-0.5 rounded hover:bg-muted disabled:opacity-40"
            >
              →
            </button>
          </div>
        )}
      </div>
    );
  }

  // Should be unreachable — rendererType is a union of all supported cases
  return null;
}
