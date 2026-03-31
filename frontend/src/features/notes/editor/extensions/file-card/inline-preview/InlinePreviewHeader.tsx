'use client';

/**
 * InlinePreviewHeader — Fixed 40px header bar for the inline file preview card.
 *
 * Left side: file type icon + filename (truncated)
 * Right side: 4 ghost icon buttons — Copy, Download, Edit in IDE, Expand to modal
 *
 * All buttons call e.stopPropagation() to prevent the content click-to-modal handler
 * from firing when the user clicks an action button.
 */

import * as React from 'react';
import {
  File,
  FileText,
  FileCode,
  FileSpreadsheet,
  Image,
  Copy,
  Check,
  Download,
  Code,
  Maximize2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { resolveRenderer } from '@/features/artifacts/utils/mime-type-router';

/** Returns a rendered Lucide icon element for the given MIME type. */
function renderFileIcon(mimeType: string) {
  const className = 'h-4 w-4 shrink-0 text-muted-foreground';
  if (mimeType.startsWith('image/')) return <Image className={className} />;
  if (mimeType === 'text/csv' || mimeType.includes('spreadsheet') || mimeType.includes('excel'))
    return <FileSpreadsheet className={className} />;
  if (
    mimeType.includes('javascript') ||
    mimeType.includes('typescript') ||
    mimeType.includes('html') ||
    mimeType.includes('css')
  )
    return <FileCode className={className} />;
  if (mimeType === 'application/pdf' || mimeType.startsWith('text/'))
    return <FileText className={className} />;
  return <File className={className} />;
}

export interface InlinePreviewHeaderProps {
  filename: string;
  mimeType: string;
  artifactId: string;
  signedUrl: string;
  onCopy: () => void;
  onExpandToModal: () => void;
}

export function InlinePreviewHeader({
  filename,
  mimeType,
  artifactId,
  signedUrl,
  onCopy,
  onExpandToModal,
}: InlinePreviewHeaderProps) {
  const [copied, setCopied] = React.useState(false);
  const copyTimeoutRef = React.useRef<ReturnType<typeof setTimeout>>(null);

  React.useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    };
  }, []);

  // Only show the IDE button for code files
  const showIdeButton = resolveRenderer(mimeType, filename) === 'code';

  function handleCopy(e: React.MouseEvent) {
    e.stopPropagation();
    onCopy();
    setCopied(true);
    if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    copyTimeoutRef.current = setTimeout(() => setCopied(false), 2000);
  }

  function handleDownload(e: React.MouseEvent) {
    e.stopPropagation();
    if (!signedUrl) return;
    const link = document.createElement('a');
    link.href = signedUrl;
    link.download = filename;
    link.click();
  }

  function handleOpenInIde(e: React.MouseEvent) {
    e.stopPropagation();
    queueMicrotask(() => {
      window.dispatchEvent(
        new CustomEvent('pilot:open-in-editor', { detail: { artifactId } })
      );
    });
  }

  function handleExpandToModal(e: React.MouseEvent) {
    e.stopPropagation();
    onExpandToModal();
  }

  return (
    <div className="flex items-center h-10 bg-muted border-b border-border px-4 rounded-t-lg">
      {/* Left: icon + filename */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {renderFileIcon(mimeType)}
        <span className="text-sm font-medium text-foreground truncate">{filename}</span>
      </div>

      {/* Right: action buttons */}
      <div className="flex items-center gap-1 shrink-0">
        {/* Copy */}
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label="Copy content"
          onClick={handleCopy}
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-emerald-600" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </Button>

        {/* Download */}
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label="Download file"
          onClick={handleDownload}
          disabled={!signedUrl}
        >
          <Download className="h-3.5 w-3.5" />
        </Button>

        {/* Edit in IDE — only shown for code files */}
        {showIdeButton && (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="Open in code editor"
            onClick={handleOpenInIde}
          >
            <Code className="h-3.5 w-3.5" />
          </Button>
        )}

        {/* Expand to modal */}
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label="Open full preview"
          onClick={handleExpandToModal}
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </Button>
      </div>
      <span className="sr-only" aria-live="polite" role="status">
        {copied ? 'Copied' : ''}
      </span>
    </div>
  );
}
