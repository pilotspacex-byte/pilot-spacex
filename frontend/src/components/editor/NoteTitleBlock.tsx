'use client';

/**
 * NoteTitleBlock - Editable title as first block of note content (Notion-style)
 *
 * The title is part of the document content, not a separate header.
 * This follows the Notion pattern where the title is essentially the first block.
 *
 * @see DD-013 Note-First Collaborative Workspace
 */
import { useCallback, useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

export interface NoteTitleBlockProps {
  /** Note title */
  title: string;
  /** Placeholder text when empty */
  placeholder?: string;
  /** Callback when title changes */
  onTitleChange?: (title: string) => void;
  /** Whether editing is disabled */
  disabled?: boolean;
  /** Additional className */
  className?: string;
}

/**
 * NoteTitleBlock - Editable title block for note content
 */
export function NoteTitleBlock({
  title,
  placeholder = 'Untitled',
  onTitleChange,
  disabled = false,
  className,
}: NoteTitleBlockProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(title);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Focus and select when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
      // Auto-resize textarea
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
    }
  }, [isEditing]);

  const startEditing = useCallback(() => {
    if (disabled || !onTitleChange) return;
    setEditValue(title);
    setIsEditing(true);
  }, [title, disabled, onTitleChange]);

  const handleSave = useCallback(() => {
    const trimmed = editValue.trim();
    if (trimmed !== title && onTitleChange) {
      onTitleChange(trimmed || placeholder);
    } else {
      setEditValue(title);
    }
    setIsEditing(false);
  }, [editValue, title, onTitleChange, placeholder]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSave();
      }
      if (e.key === 'Escape') {
        setEditValue(title);
        setIsEditing(false);
      }
    },
    [handleSave, title]
  );

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditValue(e.target.value);
    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
  }, []);

  if (isEditing) {
    return (
      <div className={cn('mb-6 sm:mb-8 lg:mb-10', className)}>
        <textarea
          ref={inputRef}
          data-testid="note-title-input"
          value={editValue}
          onChange={handleInput}
          onBlur={handleSave}
          onKeyDown={handleKeyDown}
          rows={1}
          className={cn(
            'w-full bg-transparent resize-none overflow-hidden',
            // Responsive font size - larger on ultra-wide screens
            'font-display text-3xl sm:text-4xl lg:text-5xl 2xl:text-6xl font-bold text-foreground',
            'border-none outline-none ring-0 focus:ring-0',
            'py-0 px-0 leading-tight tracking-tight',
            'placeholder:text-muted-foreground/40'
          )}
          placeholder={placeholder}
          disabled={disabled}
        />
      </div>
    );
  }

  return (
    <div className={cn('mb-6 sm:mb-8 lg:mb-10', className)}>
      <h1
        data-testid="note-title"
        className={cn(
          // Responsive font size - larger on ultra-wide screens
          'font-display text-2xl sm:text-3xl lg:text-4xl 2xl:text-5xl font-bold text-foreground',
          'leading-tight tracking-tight',
          'break-words',
          // Interactive states
          onTitleChange &&
            !disabled && [
              'cursor-text',
              'hover:bg-accent/20 rounded-lg px-2 -mx-2 py-1 -my-1',
              'transition-colors duration-150',
            ],
          // Empty state
          !title && 'text-muted-foreground/40'
        )}
        onClick={startEditing}
      >
        {title || placeholder}
      </h1>
    </div>
  );
}

export default NoteTitleBlock;
