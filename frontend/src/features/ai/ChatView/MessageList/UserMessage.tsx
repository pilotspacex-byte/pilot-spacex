/**
 * UserMessage - Display user messages in chat
 * Minimal design: light-gray background, no avatar
 */

import React, { memo } from 'react';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '@/stores/ai/types/conversation';
import { AttachmentChip } from './AttachmentChip';
import { AudioPlaybackPill } from '../ChatInput/AudioPlaybackPill';
import { MentionChip } from '../ChatInput/MentionChip';

/**
 * Regex matching @[Type:uuid] mention tokens in message content.
 * Groups: [1] = entity type (Note|Issue|Project), [2] = UUID.
 */
const MENTION_RE = /@\[(Note|Issue|Project):([0-9a-f-]+)\]/g;

/**
 * Parses message content, replacing @[Type:uuid] tokens with read-only MentionChip pills.
 * Plain text segments and /command tokens pass through as-is.
 */
function renderMessageContent(content: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;

  // Reset lastIndex to ensure consistent matching across calls
  MENTION_RE.lastIndex = 0;

  let match: RegExpExecArray | null;
  while ((match = MENTION_RE.exec(content)) !== null) {
    // Push text before this match
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }
    const entityType = match[1] as 'Note' | 'Issue' | 'Project';
    const entityId = match[2] ?? '';
    if (!entityId) {
      lastIndex = match.index + match[0].length;
      continue;
    }
    parts.push(
      <MentionChip
        key={`mention-${match.index}`}
        entityType={entityType}
        entityId={entityId}
        title={`${entityType}:${entityId.slice(0, 8)}`}
      />
    );
    lastIndex = match.index + match[0].length;
  }

  // Push remaining text after last match
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts.length > 0 ? <>{parts}</> : content;
}

interface UserMessageProps {
  message: ChatMessage;
  userName?: string;
  userAvatar?: string;
  className?: string;
}

export const UserMessage = memo<UserMessageProps>(({ message, userName = 'You', className }) => {
  // Hide answer protocol messages — Q&A is shown inline in the assistant message
  if (message.metadata?.isAnswerMessage) {
    return null;
  }

  return (
    <div
      className={cn('px-4 py-3 bg-muted/100 text-primary', className)}
      data-testid="message-user"
    >
      <div className="flex items-baseline gap-2 mb-1.5">
        <span className="text-[15px] font-semibold text-foreground">{userName}</span>
        <time className="text-[11px] text-muted-foreground/70">
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </time>
      </div>

      <div className="prose prose-sm max-w-none text-foreground dark:prose-invert leading-relaxed">
        {renderMessageContent(message.content)}
      </div>

      {message.metadata?.voiceAudioUrl && (
        <div className="mt-1.5">
          <AudioPlaybackPill audioUrl={message.metadata.voiceAudioUrl} />
        </div>
      )}

      {(message.metadata?.attachments ?? []).length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2" data-testid="attachment-chips">
          {(message.metadata?.attachments ?? []).map((att) => (
            <AttachmentChip key={att.attachmentId} attachment={att} />
          ))}
        </div>
      )}
    </div>
  );
});

UserMessage.displayName = 'UserMessage';
