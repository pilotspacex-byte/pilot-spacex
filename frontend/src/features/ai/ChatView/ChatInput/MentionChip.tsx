/**
 * MentionChip - Atomic inline pill badge for @-referenced entities.
 *
 * Used inside contenteditable input (with onRemove) and in chat history
 * messages (without onRemove, read-only mode).
 *
 * DOM attributes `data-entity-type` and `data-entity-id` are the serialization
 * contract — getSerializedValue() reads these to emit @[Type:uuid] tokens.
 *
 * @module features/ai/ChatView/ChatInput/MentionChip
 */

import { memo } from 'react';
import { FileText, CircleDot, FolderOpen } from 'lucide-react';

interface MentionChipProps {
  entityType: 'Note' | 'Issue' | 'Project';
  entityId: string;
  title: string;
  onRemove?: () => void;
}

const ENTITY_ICONS = {
  Note: FileText,
  Issue: CircleDot,
  Project: FolderOpen,
} as const;

export const MentionChip = memo<MentionChipProps>(
  ({ entityType, entityId, title, onRemove }) => {
    const Icon = ENTITY_ICONS[entityType];
    return (
      <span
        contentEditable={false}
        data-entity-type={entityType}
        data-entity-id={entityId}
        aria-label={onRemove ? `${entityType}: ${title}. Press Backspace to remove.` : `${entityType}: ${title}`}
        className="inline-flex items-center gap-1 mx-0.5 px-1.5 py-0.5 rounded-md bg-primary/10 text-primary text-xs font-medium select-none cursor-default"
      >
        <Icon className="h-3 w-3 shrink-0" aria-hidden="true" />
        @{title}
        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="ml-0.5 text-primary/60 hover:text-primary"
            aria-label={`Remove ${title}`}
          >
            ×
          </button>
        )}
      </span>
    );
  }
);

MentionChip.displayName = 'MentionChip';
