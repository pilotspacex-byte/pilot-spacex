'use client';

/**
 * IssueTitle - Inline editable title with auto-save.
 *
 * T028: Click-to-edit title that auto-saves after 2s debounce.
 * Uses useSaveStatus for per-field save feedback and useUpdateIssue
 * for optimistic mutation. Validates 1-255 characters.
 *
 * Keyboard: Enter confirms + exits edit, Escape reverts + exits.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { SaveStatus } from '@/components/ui/save-status';
import { useSaveStatus } from '@/features/issues/hooks/use-save-status';
import { useUpdateIssue } from '@/features/issues/hooks/use-update-issue';

// ============================================================================
// Types
// ============================================================================

export interface IssueTitleProps {
  /** Current issue title */
  title: string;
  /** Issue ID for mutations */
  issueId: string;
  /** Workspace ID for mutations */
  workspaceId: string;
  /** Disable editing */
  disabled?: boolean;
}

// ============================================================================
// Constants
// ============================================================================

const TITLE_MIN_LENGTH = 1;
const TITLE_MAX_LENGTH = 255;
const DEBOUNCE_MS = 2000;

// ============================================================================
// Component
// ============================================================================

export function IssueTitle({ title, issueId, workspaceId, disabled = false }: IssueTitleProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(title);
  const [validationError, setValidationError] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedRef = useRef(title);

  const { status, wrapMutation } = useSaveStatus('title');
  const updateIssue = useUpdateIssue(workspaceId, issueId);

  // Sync external title prop into local edit buffer when not actively editing.
  useEffect(() => {
    if (!isEditing) {
      setEditValue(title);
      lastSavedRef.current = title;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally sync only when title prop changes
  }, [title]);

  const clearDebounce = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
  }, []);

  const validate = useCallback((value: string): string | null => {
    const trimmed = value.trim();
    if (trimmed.length < TITLE_MIN_LENGTH) return 'Title cannot be empty';
    if (trimmed.length > TITLE_MAX_LENGTH)
      return `Title must be ${TITLE_MAX_LENGTH} characters or fewer`;
    return null;
  }, []);

  const saveTitle = useCallback(
    async (value: string) => {
      const trimmed = value.trim();
      if (trimmed === lastSavedRef.current) return;

      const error = validate(trimmed);
      if (error) {
        setValidationError(error);
        return;
      }

      setValidationError(null);
      lastSavedRef.current = trimmed;

      await wrapMutation(() => updateIssue.mutateAsync({ name: trimmed }));
    },
    [validate, wrapMutation, updateIssue]
  );

  const scheduleSave = useCallback(
    (value: string) => {
      clearDebounce();
      debounceTimerRef.current = setTimeout(() => {
        void saveTitle(value);
      }, DEBOUNCE_MS);
    },
    [clearDebounce, saveTitle]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setEditValue(value);
      setValidationError(validate(value.trim()));
      scheduleSave(value);
    },
    [validate, scheduleSave]
  );

  const enterEditMode = useCallback(() => {
    if (disabled) return;
    setIsEditing(true);
    // Focus input after render
    requestAnimationFrame(() => inputRef.current?.focus());
  }, [disabled]);

  const confirmAndExit = useCallback(() => {
    clearDebounce();
    const trimmed = editValue.trim();
    if (!validate(trimmed)) {
      void saveTitle(trimmed);
      setEditValue(trimmed);
    }
    setIsEditing(false);
  }, [clearDebounce, editValue, validate, saveTitle]);

  const cancelAndExit = useCallback(() => {
    clearDebounce();
    setEditValue(lastSavedRef.current);
    setValidationError(null);
    setIsEditing(false);
  }, [clearDebounce]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        confirmAndExit();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        cancelAndExit();
      }
    },
    [confirmAndExit, cancelAndExit]
  );

  // Listen for force-save event (Cmd/Ctrl+S)
  useEffect(() => {
    const handleForceSave = () => {
      clearDebounce();
      const trimmed = editValue.trim();
      if (!validate(trimmed) && trimmed !== lastSavedRef.current) {
        void saveTitle(trimmed);
      }
    };
    document.addEventListener('issue-force-save', handleForceSave);
    return () => document.removeEventListener('issue-force-save', handleForceSave);
  }, [clearDebounce, editValue, validate, saveTitle]);

  // Cleanup debounce on unmount
  useEffect(() => clearDebounce, [clearDebounce]);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        {isEditing ? (
          <input
            ref={inputRef}
            type="text"
            value={editValue}
            onChange={handleChange}
            onBlur={confirmAndExit}
            onKeyDown={handleKeyDown}
            maxLength={TITLE_MAX_LENGTH}
            aria-label="Issue title"
            aria-invalid={validationError ? 'true' : undefined}
            aria-describedby={validationError ? 'issue-title-error' : undefined}
            className={cn(
              'flex-1 bg-transparent font-display text-4xl font-semibold leading-tight',
              'outline-none border-b-2 border-transparent',
              'focus:border-primary transition-colors duration-150',
              'placeholder:text-foreground-muted',
              validationError && 'border-destructive focus:border-destructive'
            )}
            placeholder="Issue title"
          />
        ) : (
          <button
            type="button"
            onClick={enterEditMode}
            disabled={disabled}
            className={cn(
              'flex-1 text-left font-display text-4xl font-semibold leading-tight',
              'rounded-[10px] px-1 -mx-1 py-0.5',
              'hover:bg-background-subtle focus-visible:outline-none',
              'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
              'transition-colors duration-150 cursor-text',
              disabled && 'cursor-default opacity-70'
            )}
            aria-label={`Edit issue title: ${editValue}`}
          >
            {editValue || 'Untitled'}
          </button>
        )}
        <SaveStatus status={status} className="shrink-0" />
      </div>
      {validationError && (
        <p id="issue-title-error" role="alert" className="text-xs text-destructive">
          {validationError}
        </p>
      )}
    </div>
  );
}

export default IssueTitle;
