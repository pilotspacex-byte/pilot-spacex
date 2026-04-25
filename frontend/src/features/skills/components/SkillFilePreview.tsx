/**
 * SkillFilePreview — drawer body for `?peek=skill-file:<slug>/<path>`.
 *
 * Phase 91 Plan 04, Task 2. Fetches the reference file via
 * `useSkillFileBlob`, then dispatches to a Phase 86 renderer based on the
 * MIME type returned by the backend (`blob.type`). For text-based renderers
 * (Markdown / Code / Csv / Json / Html / Text) we read the blob as text via
 * an effect and pass `content` into the renderer; for binary renderers
 * (Image, ultimately PDF / Office in the future) we pass the object URL as
 * `signedUrl`.
 *
 * Renderer prop shapes verified against
 * `frontend/src/features/artifacts/components/renderers/`:
 *   - MarkdownRenderer / CsvRenderer / JsonRenderer / TextRenderer → `{ content }`
 *   - CodeRenderer → `{ content, language }`
 *   - HtmlRenderer → `{ content, filename }`
 *   - ImageRenderer → `{ signedUrl, filename }`
 *   - DownloadFallback → `{ filename, signedUrl, reason }`
 *
 * No PdfRenderer exists in the renderer directory (Phase 86 omitted PDFs
 * for files); PDFs and unknown MIME types fall through to DownloadFallback.
 */
'use client';

import * as React from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { useSkillFileBlob } from '../hooks';
import { MarkdownRenderer } from '@/features/artifacts/components/renderers/MarkdownRenderer';
import { CodeRenderer } from '@/features/artifacts/components/renderers/CodeRenderer';
import { ImageRenderer } from '@/features/artifacts/components/renderers/ImageRenderer';
import { CsvRenderer } from '@/features/artifacts/components/renderers/CsvRenderer';
import { HtmlRenderer } from '@/features/artifacts/components/renderers/HtmlRenderer';
import { JsonRenderer } from '@/features/artifacts/components/renderers/JsonRenderer';
import { TextRenderer } from '@/features/artifacts/components/renderers/TextRenderer';
import { DownloadFallback } from '@/features/artifacts/components/renderers/DownloadFallback';

export interface SkillFilePreviewProps {
  slug: string;
  path: string;
}

/**
 * Map a filename extension to a syntax-highlight language tag understood by
 * `rehype-highlight` (which the chat MarkdownContent uses under the hood).
 * Conservative defaults — unknown extensions render as `text`.
 */
function languageFromName(name: string): string {
  const ext = name.toLowerCase().match(/\.([a-z0-9]+)$/)?.[1];
  switch (ext) {
    case 'py':
      return 'python';
    case 'ts':
    case 'tsx':
      return 'typescript';
    case 'js':
    case 'jsx':
    case 'mjs':
    case 'cjs':
      return 'javascript';
    case 'sql':
      return 'sql';
    case 'sh':
    case 'bash':
      return 'bash';
    case 'rb':
      return 'ruby';
    case 'go':
      return 'go';
    case 'rs':
      return 'rust';
    case 'css':
      return 'css';
    case 'scss':
      return 'scss';
    case 'yml':
    case 'yaml':
      return 'yaml';
    case 'toml':
      return 'toml';
    case 'json':
      return 'json';
    default:
      return 'text';
  }
}

const CODE_EXT_RE = /\.(py|ts|tsx|js|jsx|mjs|cjs|sql|sh|bash|rb|go|rs|css|scss|yaml|yml|toml)$/i;

/**
 * Read a blob URL as text — used by renderers that take `content: string`
 * rather than a URL. We own the lifecycle here: cancel-on-unmount and on
 * URL change to avoid dangling promises updating state after unmount.
 */
function useBlobText(url: string | undefined): {
  text: string | null;
  loading: boolean;
  error: boolean;
} {
  const [state, setState] = React.useState<{
    text: string | null;
    loading: boolean;
    error: boolean;
  }>({ text: null, loading: false, error: false });

  React.useEffect(() => {
    if (!url) {
      setState({ text: null, loading: false, error: false });
      return;
    }
    let cancelled = false;
    setState({ text: null, loading: true, error: false });
    fetch(url)
      .then((r) => r.text())
      .then((t) => {
        if (!cancelled) setState({ text: t, loading: false, error: false });
      })
      .catch(() => {
        if (!cancelled)
          setState({ text: null, loading: false, error: true });
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  return state;
}

function CenteredSpinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div
      role="status"
      aria-label={label}
      className="flex items-center justify-center p-12 text-muted-foreground"
    >
      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
      <span className="text-[13px] font-medium">{label}…</span>
    </div>
  );
}

function ErrorBlock({
  onRetry,
  message = "Couldn't load this file.",
}: {
  onRetry: () => void;
  message?: string;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-2 p-12 text-center"
    >
      <AlertTriangle className="h-5 w-5 text-destructive" aria-hidden />
      <p className="text-[13px] font-semibold">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="text-[13px] font-medium text-[#29a386] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
      >
        Retry
      </button>
    </div>
  );
}

export function SkillFilePreview({ slug, path }: SkillFilePreviewProps) {
  const { data, isPending, isError, refetch } = useSkillFileBlob(slug, path);
  const mime = data?.mimeType ?? '';
  const filename = path.split('/').pop() || path;

  // Decide UP-FRONT whether we'll need text content. This drives the blob-read
  // effect; if we don't need text (image/binary), the effect short-circuits
  // and the renderer reads `data.url` directly.
  const wantsText =
    !!data &&
    (mime.startsWith('text/') ||
      mime === 'application/json' ||
      mime === 'application/ld+json' ||
      // Code-ish files often arrive as application/octet-stream; gate on
      // extension when the backend mime is generic.
      (mime === 'application/octet-stream' && CODE_EXT_RE.test(filename)));

  const {
    text,
    loading: textLoading,
    error: textError,
  } = useBlobText(wantsText ? data?.url : undefined);

  if (isPending) return <CenteredSpinner label="Loading" />;
  if (isError || !data) {
    return <ErrorBlock onRetry={() => refetch()} />;
  }
  if (wantsText && (textLoading || (text === null && !textError))) {
    return <CenteredSpinner label="Reading" />;
  }
  if (wantsText && textError) {
    return <ErrorBlock onRetry={() => refetch()} />;
  }

  // -- Mime / extension dispatch ------------------------------------------
  // Markdown FIRST (it's the most common skill ref-file format).
  if (mime.startsWith('text/markdown') || /\.(md|mdx)$/i.test(filename)) {
    return <MarkdownRenderer content={text ?? ''} />;
  }
  if (
    mime === 'application/json' ||
    mime === 'application/ld+json' ||
    /\.json$/i.test(filename)
  ) {
    return <JsonRenderer content={text ?? ''} />;
  }
  if (mime === 'text/csv' || /\.csv$/i.test(filename)) {
    return <CsvRenderer content={text ?? ''} />;
  }
  if (mime === 'text/html' || /\.html?$/i.test(filename)) {
    return <HtmlRenderer content={text ?? ''} filename={filename} />;
  }
  if (mime.startsWith('image/')) {
    return <ImageRenderer signedUrl={data.url} filename={filename} />;
  }
  // Code-ish files: dispatch to CodeRenderer with a derived language tag.
  if (CODE_EXT_RE.test(filename) || mime.startsWith('text/x-')) {
    return (
      <CodeRenderer
        content={text ?? ''}
        language={languageFromName(filename)}
      />
    );
  }
  if (mime.startsWith('text/')) {
    return <TextRenderer content={text ?? ''} />;
  }
  // Binary / unknown — PDF, Office formats, etc.
  return (
    <DownloadFallback
      filename={filename}
      signedUrl={data.url}
      reason="unsupported"
    />
  );
}
