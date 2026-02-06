/**
 * SkillEditor - Inline markdown editor for skill content.
 *
 * T037: Textarea-based markdown editor with toolbar, word count, and save/cancel.
 * Source: FR-009, FR-010, US6
 */

'use client';

import * as React from 'react';
import { Bold, Code, Heading1, Heading2, Heading3, Italic, List } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { WordCountBar } from './word-count-bar';

interface SkillEditorProps {
  initialContent: string;
  maxWords?: number;
  onSave: (content: string) => void;
  onCancel: () => void;
  isSaving?: boolean;
}

interface ToolbarAction {
  icon: React.ElementType;
  label: string;
  prefix: string;
  suffix?: string;
}

const TOOLBAR_ACTIONS: ToolbarAction[] = [
  { icon: Bold, label: 'Bold', prefix: '**', suffix: '**' },
  { icon: Italic, label: 'Italic', prefix: '_', suffix: '_' },
  { icon: Heading1, label: 'Heading 1', prefix: '# ' },
  { icon: Heading2, label: 'Heading 2', prefix: '## ' },
  { icon: Heading3, label: 'Heading 3', prefix: '### ' },
  { icon: List, label: 'Bullet List', prefix: '- ' },
  { icon: Code, label: 'Code Block', prefix: '```\n', suffix: '\n```' },
];

function countWords(text: string): number {
  return text
    .replace(/[#*_`\->\[\]()]/g, '')
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
}

function ToolbarButton({
  action,
  onClick,
}: {
  action: ToolbarAction;
  onClick: (action: ToolbarAction) => void;
}) {
  const Icon = action.icon;
  return (
    <button
      type="button"
      onClick={() => onClick(action)}
      className={cn(
        'inline-flex h-8 w-8 items-center justify-center rounded border',
        'bg-background text-muted-foreground',
        'hover:bg-muted hover:text-foreground',
        'focus-visible:ring-[3px] focus-visible:ring-primary/30 focus-visible:outline-none'
      )}
      aria-label={action.label}
      title={action.label}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}

export function SkillEditor({
  initialContent,
  maxWords = 2000,
  onSave,
  onCancel,
  isSaving = false,
}: SkillEditorProps) {
  const [content, setContent] = React.useState(initialContent);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const wordCount = countWords(content);
  const isOverLimit = wordCount > maxWords;

  const handleToolbarAction = React.useCallback(
    (action: ToolbarAction) => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const selected = content.slice(start, end);
      const prefix = action.prefix;
      const suffix = action.suffix ?? '';

      const newContent = content.slice(0, start) + prefix + selected + suffix + content.slice(end);

      setContent(newContent);

      requestAnimationFrame(() => {
        textarea.focus();
        const cursorPos = start + prefix.length + selected.length;
        textarea.setSelectionRange(cursorPos, cursorPos);
      });
    },
    [content]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
    }
  };

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center gap-1 rounded-t-lg border border-b-0 bg-background p-1.5">
        {TOOLBAR_ACTIONS.map((action) => (
          <ToolbarButton key={action.label} action={action} onClick={handleToolbarAction} />
        ))}
      </div>

      {/* Editor area */}
      <textarea
        ref={textareaRef}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onKeyDown={handleKeyDown}
        className={cn(
          'w-full min-h-[300px] rounded-b-lg border bg-background p-4',
          'font-mono text-sm leading-relaxed',
          'resize-y',
          'focus-visible:ring-[3px] focus-visible:ring-primary/30 focus-visible:outline-none',
          'focus-visible:border-primary'
        )}
        aria-label="Skill content editor"
      />

      {/* Word count */}
      <WordCountBar wordCount={wordCount} maxWords={maxWords} />

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          onClick={() => onSave(content)}
          disabled={isSaving || isOverLimit || content.trim().length === 0}
        >
          {isSaving ? 'Saving...' : 'Save'}
        </Button>
        <Button variant="ghost" onClick={onCancel} disabled={isSaving}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
