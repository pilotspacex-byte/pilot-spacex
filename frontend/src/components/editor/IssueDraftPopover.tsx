'use client';

/**
 * IssueDraftPopover - Popover for creating an issue from selected text.
 *
 * Pre-fills title (first sentence, truncated 80 chars) and description
 * (full selected text) from the editor selection. User picks type and
 * priority, then submits — which sends a structured prompt to the AI
 * store's `create_issue_from_note` MCP tool.
 *
 * @module components/editor/IssueDraftPopover
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';

const ISSUE_TYPES = ['bug', 'task', 'feature', 'improvement'] as const;
const PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const;

type IssueType = (typeof ISSUE_TYPES)[number];
type Priority = (typeof PRIORITIES)[number];

export interface IssueDraftPayload {
  title: string;
  description: string;
  issueType: IssueType;
  priority: Priority;
  blockIds: string[];
  noteId: string;
}

export interface IssueDraftPopoverProps {
  /** Whether popover is visible */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Selected text from editor */
  selectedText: string;
  /** Block IDs covering the selection */
  blockIds: string[];
  /** Current note ID */
  noteId: string;
  /** Submit handler — called with the draft payload */
  onSubmit: (payload: IssueDraftPayload) => Promise<void>;
}

/**
 * Extract the first sentence from text, truncated to maxLen chars.
 */
function extractTitle(text: string, maxLen = 80): string {
  const firstSentence = text.split(/[.!?\n]/)[0]?.trim() ?? '';
  return firstSentence.length > maxLen ? `${firstSentence.slice(0, maxLen - 1)}…` : firstSentence;
}

export function IssueDraftPopover({
  isOpen,
  onClose,
  selectedText,
  blockIds,
  noteId,
  onSubmit,
}: IssueDraftPopoverProps) {
  const defaultTitle = useMemo(() => extractTitle(selectedText), [selectedText]);

  const [title, setTitle] = useState(defaultTitle);
  const [description, setDescription] = useState(selectedText);
  const [issueType, setIssueType] = useState<IssueType>('task');
  const [priority, setPriority] = useState<Priority>('medium');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialize form only when opening — not on every selectedText change while open
  useEffect(() => {
    if (isOpen) {
      setTitle(extractTitle(selectedText));
      setDescription(selectedText);
      setIssueType('task');
      setPriority('medium');
      setIsSubmitting(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]); // NOT selectedText — avoids wiping user edits mid-session

  // Escape key closes popover
  useEffect(() => {
    if (!isOpen) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  const handleSubmit = useCallback(async () => {
    if (!title.trim() || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await onSubmit({ title: title.trim(), description, issueType, priority, blockIds, noteId });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  }, [title, description, issueType, priority, blockIds, noteId, isSubmitting, onSubmit, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="absolute z-50 w-80 rounded-lg border bg-popover p-4 shadow-lg"
      data-testid="issue-draft-popover"
      role="dialog"
      aria-label="Create issue from selection"
    >
      <div className="space-y-3">
        <div>
          <Label htmlFor="issue-title" className="text-xs font-medium">
            Title
          </Label>
          <Input
            id="issue-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Issue title"
            className="mt-1 h-8 text-sm"
            maxLength={255}
            autoFocus
          />
        </div>

        <div>
          <Label htmlFor="issue-description" className="text-xs font-medium">
            Description
          </Label>
          <Textarea
            id="issue-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Issue description"
            className="mt-1 min-h-[60px] text-sm"
            rows={3}
            maxLength={2000}
          />
          <p className="mt-0.5 text-right text-xs text-muted-foreground">
            {description.length}/2000
          </p>
        </div>

        <div className="flex gap-2">
          <div className="flex-1">
            <Label htmlFor="issue-type" className="text-xs font-medium">
              Type
            </Label>
            <Select value={issueType} onValueChange={(v) => setIssueType(v as IssueType)}>
              <SelectTrigger id="issue-type" className="mt-1 h-8 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ISSUE_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1">
            <Label htmlFor="issue-priority" className="text-xs font-medium">
              Priority
            </Label>
            <Select value={priority} onValueChange={(v) => setPriority(v as Priority)}>
              <SelectTrigger id="issue-priority" className="mt-1 h-8 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRIORITIES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-1">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSubmit}
            disabled={!title.trim() || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                Creating…
              </>
            ) : (
              'Create Issue'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default IssueDraftPopover;
