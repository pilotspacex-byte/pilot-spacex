/**
 * AttachmentButton — paperclip button that opens a file picker
 * and accepts drag-and-drop file attachments.
 *
 * Matches the h-6 w-6 ghost icon button pattern used in ChatInput toolbar.
 *
 * @module features/ai/ChatView/ChatInput/AttachmentButton
 */

import { useRef, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Paperclip, HardDrive } from 'lucide-react';
import { ACCEPTED_MIME_TYPES } from '@/types/attachments';
import { cn } from '@/lib/utils';

// ── Component ──────────────────────────────────────────────────────────────

interface AttachmentButtonProps {
  onAddFile: (file: File) => void;
  disabled?: boolean;
  /** Whether Google Drive is connected for this workspace */
  driveConnected?: boolean;
  /** Called when the user clicks the Drive icon and Drive is NOT connected */
  onConnectDrive?: () => void;
  /** Called when the user clicks the Drive icon and Drive IS connected */
  onOpenDrivePicker?: () => void;
}

export function AttachmentButton({
  onAddFile,
  disabled = false,
  driveConnected,
  onConnectDrive,
  onOpenDrivePicker,
}: AttachmentButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleButtonClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files) return;
      for (const file of Array.from(files)) {
        onAddFile(file);
      }
      // Reset so the same file can be selected again
      e.target.value = '';
    },
    [onAddFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);

      const files = e.dataTransfer.files;
      for (const file of Array.from(files)) {
        if (!(ACCEPTED_MIME_TYPES as readonly string[]).includes(file.type)) {
          toast.error(`Unsupported file type: ${file.name}`);
          continue;
        }
        onAddFile(file);
      }
    },
    [onAddFile]
  );

  const hasDriveHandlers = onConnectDrive !== undefined || onOpenDrivePicker !== undefined;

  const handleDriveClick = useCallback(() => {
    if (driveConnected) {
      onOpenDrivePicker?.();
    } else {
      onConnectDrive?.();
    }
  }, [driveConnected, onConnectDrive, onOpenDrivePicker]);

  return (
    <div
      className={cn(
        'relative flex items-center gap-0.5',
        isDragOver && 'ring-2 ring-primary rounded'
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-6 w-6 text-muted-foreground/60 hover:text-foreground"
        onClick={handleButtonClick}
        disabled={disabled}
        data-testid="attachment-button"
        aria-label="Attach file"
      >
        <Paperclip className="h-3.5 w-3.5" />
        <span className="sr-only">Attach file</span>
      </Button>

      {hasDriveHandlers && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={cn(
            'h-6 w-6 hover:text-foreground',
            driveConnected ? 'text-teal-600 dark:text-teal-400' : 'text-muted-foreground/40'
          )}
          onClick={handleDriveClick}
          disabled={disabled}
          data-testid="drive-button"
          aria-label={driveConnected ? 'Browse Google Drive files' : 'Connect Google Drive'}
          title={driveConnected ? 'Browse Google Drive files' : 'Connect Google Drive'}
        >
          <HardDrive className="h-3.5 w-3.5" />
          <span className="sr-only">
            {driveConnected ? 'Browse Google Drive files' : 'Connect Google Drive'}
          </span>
        </Button>
      )}

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={ACCEPTED_MIME_TYPES.join(',')}
        onChange={handleFileChange}
        className="hidden"
        aria-hidden="true"
        tabIndex={-1}
      />

      {isDragOver && (
        <div
          className="absolute inset-0 flex items-center justify-center bg-background/80 rounded text-xs font-medium text-primary pointer-events-none z-10"
          data-testid="drop-overlay"
        >
          Drop to attach
        </div>
      )}
    </div>
  );
}

AttachmentButton.displayName = 'AttachmentButton';
