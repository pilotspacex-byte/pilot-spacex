'use client';

import * as React from 'react';
import { Download, Maximize2, Minimize2, X, ZoomIn, ZoomOut } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import dynamic from 'next/dynamic';
import { resolveRenderer, getLanguageForFile } from '../utils/mime-type-router';
import { useFileContent } from '../hooks/useFileContent';
import { DownloadFallback } from './renderers/DownloadFallback';

// ---------------------------------------------------------------------------
// Skeleton loaders for dynamic renderers
// ---------------------------------------------------------------------------
const CODE_LINE_WIDTHS = [78, 92, 65, 88, 71, 95, 60, 83, 76, 90, 68, 85];

function CodeSkeleton() {
  return (
    <div className="p-6 space-y-2 animate-pulse">
      <div className="h-3 w-24 rounded bg-muted" />
      {CODE_LINE_WIDTHS.map((w, i) => (
        <div key={i} className="h-3 rounded bg-muted" style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="p-6 space-y-3 animate-pulse">
      <div className="flex gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-4 flex-1 rounded bg-muted" />
        ))}
      </div>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex gap-4">
          {Array.from({ length: 4 }).map((_, j) => (
            <div key={j} className="h-3 flex-1 rounded bg-muted/60" />
          ))}
        </div>
      ))}
    </div>
  );
}

function ProseSkeleton() {
  return (
    <div className="p-6 space-y-3 animate-pulse">
      <div className="h-5 w-48 rounded bg-muted" />
      <div className="h-3 w-full rounded bg-muted/60" />
      <div className="h-3 w-11/12 rounded bg-muted/60" />
      <div className="h-3 w-4/5 rounded bg-muted/60" />
      <div className="h-4 w-36 rounded bg-muted mt-4" />
      <div className="h-3 w-full rounded bg-muted/60" />
      <div className="h-3 w-3/4 rounded bg-muted/60" />
    </div>
  );
}

// Lazy-load heavy renderers — papaparse (~50KB), DOMPurify (~30KB), react-markdown
// are only loaded when the user actually opens a file preview of that type.
// Each has a loading skeleton that matches the expected content shape.
const MarkdownRenderer = dynamic(
  () => import('./renderers/MarkdownRenderer').then((m) => ({ default: m.MarkdownRenderer })),
  { loading: () => <ProseSkeleton /> }
);
const TextRenderer = dynamic(
  () => import('./renderers/TextRenderer').then((m) => ({ default: m.TextRenderer })),
  { loading: () => <CodeSkeleton /> }
);
const JsonRenderer = dynamic(
  () => import('./renderers/JsonRenderer').then((m) => ({ default: m.JsonRenderer })),
  { loading: () => <CodeSkeleton /> }
);
const CodeRenderer = dynamic(
  () => import('./renderers/CodeRenderer').then((m) => ({ default: m.CodeRenderer })),
  { loading: () => <CodeSkeleton /> }
);
const CsvRenderer = dynamic(
  () => import('./renderers/CsvRenderer').then((m) => ({ default: m.CsvRenderer })),
  { loading: () => <TableSkeleton /> }
);
const HtmlRenderer = dynamic(
  () => import('./renderers/HtmlRenderer').then((m) => ({ default: m.HtmlRenderer })),
  { loading: () => <CodeSkeleton /> }
);

export interface FilePreviewModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  artifactId: string;
  filename: string;
  mimeType: string;
  signedUrl: string;
}

// ---------------------------------------------------------------------------
// Image Lightbox — gallery-style fullscreen overlay for images
// ---------------------------------------------------------------------------
function ImageLightbox({
  open,
  onOpenChange,
  filename,
  signedUrl,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filename: string;
  signedUrl: string;
}) {
  const [isZoomed, setIsZoomed] = React.useState(false);
  const [imgError, setImgError] = React.useState(false);

  // Reset state when lightbox opens
  React.useEffect(() => {
    if (open) {
      setIsZoomed(false);
      setImgError(false);
    }
  }, [open]);

  // Close on Escape
  React.useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onOpenChange(false);
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onOpenChange]);

  // Prevent body scroll when open
  React.useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!open) return null;

  const isValidUrl = (() => {
    try {
      const parsed = new URL(signedUrl);
      return (
        parsed.protocol === 'https:' ||
        (parsed.protocol === 'http:' &&
          (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1'))
      );
    } catch {
      return false;
    }
  })();

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-label={`Image preview: ${filename}`}
    >
      {/* Backdrop — click to close */}
      <div
        className="absolute inset-0 bg-black/90 animate-in fade-in-0 duration-200"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />

      {/* Floating toolbar */}
      <div className="relative z-10 flex items-center justify-between px-4 py-3">
        <p className="text-sm font-medium text-white/80 truncate max-w-[50vw]">{filename}</p>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-white/70 hover:text-white hover:bg-white/10"
            onClick={() => setIsZoomed((z) => !z)}
            aria-label={isZoomed ? 'Zoom out' : 'Zoom in'}
          >
            {isZoomed ? <ZoomOut className="size-4" /> : <ZoomIn className="size-4" />}
          </Button>

          {isValidUrl && (
            <Button
              variant="ghost"
              size="icon"
              className="size-8 text-white/70 hover:text-white hover:bg-white/10"
              asChild
            >
              <a
                href={signedUrl}
                download={filename}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Download image"
              >
                <Download className="size-4" />
              </a>
            </Button>
          )}

          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-white/70 hover:text-white hover:bg-white/10"
            onClick={() => onOpenChange(false)}
            aria-label="Close"
          >
            <X className="size-4" />
          </Button>
        </div>
      </div>

      {/* Image area */}
      <div
        className={cn(
          'relative z-10 flex-1 flex items-center justify-center overflow-auto min-h-0 px-4 pb-4',
          isZoomed ? 'cursor-zoom-out' : 'cursor-zoom-in'
        )}
        onClick={(e) => {
          // Only toggle zoom when clicking directly on the container or image
          if (e.target === e.currentTarget || (e.target as HTMLElement).tagName === 'IMG') {
            setIsZoomed((z) => !z);
          }
        }}
      >
        {imgError ? (
          <div className="text-sm text-white/60">Failed to load image</div>
        ) : (
          <img
            src={signedUrl}
            alt={filename}
            onError={() => setImgError(true)}
            draggable={false}
            className={cn(
              'rounded-lg shadow-2xl transition-all duration-300 ease-out select-none',
              isZoomed ? 'max-w-none w-auto scale-100' : 'max-w-[90vw] max-h-[85vh] object-contain'
            )}
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// FilePreviewModal — unified entry point
// ---------------------------------------------------------------------------
export function FilePreviewModal({
  open,
  onOpenChange,
  artifactId: _artifactId,
  filename,
  mimeType,
  signedUrl,
}: FilePreviewModalProps) {
  const [isMaximized, setIsMaximized] = React.useState(false);
  // Track when the dialog opens to ignore the originating click's "pointer down outside"
  const openTimestampRef = React.useRef(0);

  // Reset maximize state whenever the modal re-opens
  React.useEffect(() => {
    if (open) {
      setIsMaximized(false);
      openTimestampRef.current = Date.now();
    }
  }, [open]);

  const rendererType = resolveRenderer(mimeType, filename);
  const { content, isLoading, isExpired } = useFileContent(signedUrl, rendererType, open);

  // Images use the lightbox overlay instead of a Dialog
  if (rendererType === 'image') {
    return (
      <ImageLightbox
        open={open}
        onOpenChange={onOpenChange}
        filename={filename}
        signedUrl={signedUrl}
      />
    );
  }

  function renderContent() {
    // Download fallback: no content fetch needed
    if (rendererType === 'download') {
      return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="unsupported" />;
    }

    // Content-based renderers: need fetch
    if (isExpired) {
      return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="expired" />;
    }

    if (isLoading) {
      return (
        <div
          className="flex items-center justify-center p-8"
          role="status"
          aria-label="Loading file content"
        >
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
        </div>
      );
    }

    if (!content) {
      return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="error" />;
    }

    switch (rendererType) {
      case 'markdown':
        return <MarkdownRenderer content={content} />;
      case 'text':
        return <TextRenderer content={content} />;
      case 'json':
        return <JsonRenderer content={content} />;
      case 'code':
        return <CodeRenderer content={content} language={getLanguageForFile(filename)} />;
      case 'html-preview':
        return <HtmlRenderer content={content} filename={filename} />;
      case 'csv':
        return <CsvRenderer content={content} />;
      default:
        return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="unsupported" />;
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          'flex flex-col p-0 gap-0 overflow-hidden',
          isMaximized ? 'w-[95vw] h-[95vh] max-w-none' : 'sm:max-w-3xl max-h-[85vh]'
        )}
        showCloseButton={false}
        onPointerDownOutside={(e) => {
          // Radix DismissableLayer sees the original FileCard click as "outside"
          // the dialog (it didn't exist yet). Ignore clicks within 300ms of open.
          if (Date.now() - openTimestampRef.current < 300) {
            e.preventDefault();
          }
        }}
        onInteractOutside={(e) => {
          if (Date.now() - openTimestampRef.current < 300) {
            e.preventDefault();
          }
        }}
      >
        {/* Header */}
        <DialogHeader className="flex-row items-center justify-between px-4 py-3 border-b shrink-0 gap-2">
          <DialogTitle className="text-sm font-medium truncate flex-1">{filename}</DialogTitle>
          <DialogDescription className="sr-only">Preview of {filename}</DialogDescription>
          <div className="flex items-center gap-1 shrink-0">
            {/* File type badge */}
            <span className="text-xs text-muted-foreground px-2 py-0.5 rounded bg-muted">
              {mimeType.split('/')[1]?.toUpperCase() ?? 'FILE'}
            </span>

            {/* Download button — validates URL scheme (https always, http for localhost) */}
            {(() => {
              try {
                const parsed = new URL(signedUrl);
                const isHttps = parsed.protocol === 'https:';
                const isLocalHttp =
                  parsed.protocol === 'http:' &&
                  (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1');
                return isHttps || isLocalHttp;
              } catch {
                return false;
              }
            })() && (
              <Button variant="ghost" size="icon" className="size-8" asChild>
                <a
                  href={signedUrl}
                  download={filename}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Download file"
                >
                  <Download className="size-4" />
                </a>
              </Button>
            )}

            {/* Maximize toggle */}
            <Button
              variant="ghost"
              size="icon"
              className="size-8"
              onClick={() => setIsMaximized((m) => !m)}
              aria-label={isMaximized ? 'Restore size' : 'Maximize'}
            >
              {isMaximized ? <Minimize2 className="size-4" /> : <Maximize2 className="size-4" />}
            </Button>

            {/* Close */}
            <DialogClose asChild>
              <Button variant="ghost" size="icon" className="size-8" aria-label="Close">
                <X className="size-4" />
              </Button>
            </DialogClose>
          </div>
        </DialogHeader>

        {/* Body — Suspense boundary prevents dynamic() imports from bubbling
            suspension through the Dialog portal to the Next.js route segment */}
        <div className="flex-1 overflow-auto min-h-0">
          <React.Suspense
            fallback={
              <div
                className="flex items-center justify-center p-8"
                role="status"
                aria-label="Loading file content"
              >
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
              </div>
            }
          >
            {renderContent()}
          </React.Suspense>
        </div>
      </DialogContent>
    </Dialog>
  );
}
