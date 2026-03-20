'use client';

import * as React from 'react';
import { Download, Maximize2, Minimize2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { resolveRenderer, getLanguageForFile } from '../utils/mime-type-router';
import { useFileContent } from '../hooks/useFileContent';
import { ImageRenderer } from './renderers/ImageRenderer';
import { MarkdownRenderer } from './renderers/MarkdownRenderer';
import { TextRenderer } from './renderers/TextRenderer';
import { JsonRenderer } from './renderers/JsonRenderer';
import { CodeRenderer } from './renderers/CodeRenderer';
import { CsvRenderer } from './renderers/CsvRenderer';
import { HtmlRenderer } from './renderers/HtmlRenderer';
import { DownloadFallback } from './renderers/DownloadFallback';

export interface FilePreviewModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  artifactId: string;
  filename: string;
  mimeType: string;
  signedUrl: string;
}

export function FilePreviewModal({
  open,
  onOpenChange,
  artifactId: _artifactId,
  filename,
  mimeType,
  signedUrl,
}: FilePreviewModalProps) {
  const [isMaximized, setIsMaximized] = React.useState(false);

  // Reset maximize state whenever the modal re-opens
  React.useEffect(() => {
    if (open) setIsMaximized(false);
  }, [open]);

  const rendererType = resolveRenderer(mimeType, filename);
  const { content, isLoading, isExpired } = useFileContent(signedUrl, rendererType, open);

  function renderContent() {
    // Image: use signedUrl directly — no text fetch needed
    if (rendererType === 'image') {
      return <ImageRenderer signedUrl={signedUrl} filename={filename} />;
    }

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
      >
        {/* Header */}
        <DialogHeader className="flex-row items-center justify-between px-4 py-3 border-b shrink-0 gap-2">
          <DialogTitle className="text-sm font-medium truncate flex-1">{filename}</DialogTitle>
          <div className="flex items-center gap-1 shrink-0">
            {/* File type badge */}
            <span className="text-xs text-muted-foreground px-2 py-0.5 rounded bg-muted">
              {mimeType.split('/')[1]?.toUpperCase() ?? 'FILE'}
            </span>

            {/* Download button — always available */}
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

        {/* Body — scrollable renderer area */}
        <div className="flex-1 overflow-auto min-h-0">{renderContent()}</div>
      </DialogContent>
    </Dialog>
  );
}
