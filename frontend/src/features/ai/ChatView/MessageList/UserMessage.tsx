/**
 * UserMessage — Phase 87 Plan 03 v3 row anatomy.
 *
 * 32x32 violet-to-emerald gradient avatar (initial), header with name + timestamp,
 * Inter 14/1.55 body. Markdown/mention/attachment pipelines preserved.
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

  MENTION_RE.lastIndex = 0;

  let match: RegExpExecArray | null;
  while ((match = MENTION_RE.exec(content)) !== null) {
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

  const initial = (userName || '?').charAt(0).toUpperCase() || '?';

  return (
    <div
      className={cn('flex gap-4 px-6 py-3', className)}
      data-message-role="user"
      data-testid="message-user"
    >
      <div
        aria-hidden="true"
        data-message-avatar=""
        className="h-8 w-8 rounded-full bg-gradient-to-br from-violet-400 to-emerald-400 text-white flex items-center justify-center text-[13px] font-semibold flex-shrink-0"
      >
        {initial}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span data-message-name="" className="text-[13px] font-semibold text-foreground">
            {userName}
          </span>
          <time className="font-mono text-[10px] text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </time>
        </div>

        <div
          data-message-body=""
          className="mt-1 text-[14px] leading-[1.55] font-normal text-foreground"
        >
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
    </div>
  );
});

UserMessage.displayName = 'UserMessage';
