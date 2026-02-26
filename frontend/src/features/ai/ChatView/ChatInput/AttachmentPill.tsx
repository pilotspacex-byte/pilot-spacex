/**
 * AttachmentPill — badge pill for an in-progress or ready attachment.
 *
 * Shows upload state (spinner), ready state (remove button), and
 * error state (error text + remove button). Matches the ContextIndicator
 * Badge pill pattern.
 *
 * @module features/ai/ChatView/ChatInput/AttachmentPill
 */

import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, Image as ImageIcon, Code, Loader2, X } from 'lucide-react';
import type { AttachmentContext } from '@/types/attachments';

// ── Helpers ────────────────────────────────────────────────────────────────

function getFileIcon(mimeType: string) {
  if (mimeType.startsWith('image/')) {
    return <ImageIcon className="h-3 w-3" aria-hidden="true" />;
  }
  if (
    mimeType === 'text/x-python' ||
    mimeType === 'application/x-python' ||
    mimeType === 'text/typescript' ||
    mimeType === 'application/typescript' ||
    mimeType === 'text/javascript' ||
    mimeType === 'application/javascript' ||
    mimeType === 'application/json' ||
    mimeType === 'application/x-yaml' ||
    mimeType === 'text/yaml' ||
    mimeType === 'text/x-rust' ||
    mimeType === 'text/x-go' ||
    mimeType === 'text/x-java' ||
    mimeType === 'text/x-csrc' ||
    mimeType === 'text/x-c++src'
  ) {
    return <Code className="h-3 w-3" aria-hidden="true" />;
  }
  return <FileText className="h-3 w-3" aria-hidden="true" />;
}

function truncateFilename(name: string, maxLen = 20): string {
  if (name.length <= maxLen) return name;
  const ext = name.lastIndexOf('.');
  if (ext > 0 && name.length - ext <= 6) {
    const extPart = name.slice(ext);
    const namePart = name.slice(0, maxLen - extPart.length - 1);
    return `${namePart}…${extPart}`;
  }
  return `${name.slice(0, maxLen - 1)}…`;
}

// ── Component ──────────────────────────────────────────────────────────────

interface AttachmentPillProps {
  attachment: AttachmentContext;
  onRemove: () => void;
}

export const AttachmentPill = memo<AttachmentPillProps>(({ attachment, onRemove }) => {
  const { filename, mime_type, status, error } = attachment;

  return (
    <Badge variant="secondary" className="gap-1.5 max-w-[200px]" data-testid="attachment-pill">
      {status === 'uploading' ? (
        <Loader2 className="h-3 w-3 animate-spin" role="status" aria-label="Uploading" />
      ) : (
        getFileIcon(mime_type)
      )}

      <span className="truncate text-xs">{truncateFilename(filename)}</span>

      {status === 'error' && error && (
        <span className="text-destructive text-xs truncate max-w-[80px]">{error}</span>
      )}

      {status === 'ready' && (
        <Button
          variant="ghost"
          size="icon"
          className="h-3 w-3 p-0 hover:bg-transparent"
          onClick={onRemove}
          aria-label={`Remove ${filename}`}
        >
          <X className="h-2.5 w-2.5" />
          <span className="sr-only">Remove {filename}</span>
        </Button>
      )}

      {status === 'error' && (
        <Button
          variant="ghost"
          size="icon"
          className="h-3 w-3 p-0 hover:bg-transparent"
          onClick={onRemove}
          aria-label={`Dismiss ${filename}`}
        >
          <X className="h-2.5 w-2.5" />
          <span className="sr-only">Dismiss {filename}</span>
        </Button>
      )}
    </Badge>
  );
});

AttachmentPill.displayName = 'AttachmentPill';
