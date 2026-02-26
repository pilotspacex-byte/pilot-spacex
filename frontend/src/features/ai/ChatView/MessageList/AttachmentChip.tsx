/**
 * AttachmentChip — read-only chip for attachment metadata in message history.
 *
 * No remove affordance — used purely to display what files were attached
 * to a past message.
 *
 * @module features/ai/ChatView/MessageList/AttachmentChip
 */

import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { FileText, Image as ImageIcon, Code } from 'lucide-react';
import type { AttachmentMetadata } from '@/types/attachments';

// ── Helpers ────────────────────────────────────────────────────────────────

type FileType = 'image' | 'code' | 'document';

function getFileType(mimeType: string): FileType {
  if (mimeType.startsWith('image/')) return 'image';
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
    return 'code';
  }
  return 'document';
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

interface AttachmentChipProps {
  attachment: AttachmentMetadata;
}

export const AttachmentChip = memo<AttachmentChipProps>(({ attachment }) => {
  const { filename, mime_type } = attachment;
  const fileType = getFileType(mime_type);

  const iconMap: Record<FileType, React.ReactNode> = {
    image: <ImageIcon className="h-3 w-3" aria-hidden="true" />,
    code: <Code className="h-3 w-3" aria-hidden="true" />,
    document: <FileText className="h-3 w-3" aria-hidden="true" />,
  };

  return (
    <Badge variant="outline" className="gap-1.5 max-w-[200px]" data-file-type={fileType}>
      {iconMap[fileType]}
      <span className="truncate text-xs">{truncateFilename(filename)}</span>
    </Badge>
  );
});

AttachmentChip.displayName = 'AttachmentChip';
