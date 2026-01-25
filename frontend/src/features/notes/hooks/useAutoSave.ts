'use client';

/**
 * useAutoSave - Auto-save hook with debouncing and dirty state tracking
 * 2s debounce, visual indicator, retry on failure, beforeunload protection
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

export type AutoSaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

export interface UseAutoSaveOptions<T> {
  /** Data to auto-save */
  data: T;
  /** Save function */
  onSave: (data: T) => Promise<void>;
  /** Debounce delay in ms (default: 2000) */
  debounceMs?: number;
  /** Max retry attempts (default: 3) */
  maxRetries?: number;
  /** Retry delay in ms (default: 1000) */
  retryDelayMs?: number;
  /** Enable auto-save (default: true) */
  enabled?: boolean;
  /** Compare function to detect changes */
  isEqual?: (a: T, b: T) => boolean;
}

export interface UseAutoSaveReturn {
  /** Current save status */
  status: AutoSaveStatus;
  /** Whether there are unsaved changes */
  isDirty: boolean;
  /** Whether currently saving */
  isSaving: boolean;
  /** Last saved timestamp */
  lastSavedAt: Date | null;
  /** Trigger manual save */
  save: () => Promise<void>;
  /** Reset dirty state */
  reset: () => void;
}

/**
 * Default equality check using JSON stringify
 */
function defaultIsEqual<T>(a: T, b: T): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

/**
 * Auto-save hook with debouncing and dirty state
 */
export function useAutoSave<T>({
  data,
  onSave,
  debounceMs = 2000,
  maxRetries = 3,
  retryDelayMs = 1000,
  enabled = true,
  isEqual = defaultIsEqual,
}: UseAutoSaveOptions<T>): UseAutoSaveReturn {
  const [status, setStatus] = useState<AutoSaveStatus>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  // Refs for tracking state
  const savedDataRef = useRef<T>(data);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);
  const isMountedRef = useRef(true);
  const performSaveRef = useRef<((data: T) => Promise<void>) | undefined>(undefined);

  // Computed states
  const isDirty = status === 'dirty' || status === 'error';
  const isSaving = status === 'saving';

  /**
   * Perform the save operation with retry logic
   */
  const performSave = useCallback(
    async (dataToSave: T) => {
      if (!isMountedRef.current) return;

      setStatus('saving');

      try {
        await onSave(dataToSave);

        if (!isMountedRef.current) return;

        savedDataRef.current = dataToSave;
        retryCountRef.current = 0;
        setStatus('saved');
        setLastSavedAt(new Date());

        // Reset to idle after showing "Saved"
        setTimeout(() => {
          if (isMountedRef.current) {
            setStatus((current) => (current === 'saved' ? 'idle' : current));
          }
        }, 2000);
      } catch (_error) {
        if (!isMountedRef.current) return;

        retryCountRef.current += 1;

        if (retryCountRef.current < maxRetries) {
          // Retry after delay
          setTimeout(() => {
            if (isMountedRef.current && performSaveRef.current) {
              performSaveRef.current(dataToSave);
            }
          }, retryDelayMs * retryCountRef.current);
        } else {
          setStatus('error');
          toast.error('Failed to save', {
            description: 'Your changes could not be saved. Please try again.',
            action: {
              label: 'Retry',
              onClick: () => {
                if (performSaveRef.current) {
                  performSaveRef.current(dataToSave);
                }
              },
            },
          });
        }
      }
    },
    [onSave, maxRetries, retryDelayMs]
  );

  // Keep ref updated in effect
  useEffect(() => {
    performSaveRef.current = performSave;
  }, [performSave]);

  /**
   * Manual save trigger
   */
  const save = useCallback(async () => {
    // Clear debounce timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }

    await performSave(data);
  }, [data, performSave]);

  /**
   * Reset dirty state
   */
  const reset = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    savedDataRef.current = data;
    retryCountRef.current = 0;
    setStatus('idle');
  }, [data]);

  // Watch for data changes - schedule debounced save
  useEffect(() => {
    if (!enabled) return;

    // Check if data has changed from last saved
    if (!isEqual(data, savedDataRef.current)) {
      // Clear existing timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Mark as dirty and schedule save
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Auto-save pattern requires state update on data change
      setStatus('dirty');

      debounceTimerRef.current = setTimeout(() => {
        if (performSaveRef.current) {
          performSaveRef.current(data);
        }
      }, debounceMs);
    }

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [data, enabled, isEqual, debounceMs]);

  // Prevent navigation with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty || isSaving) {
        e.preventDefault();
        e.returnValue = '';
        return '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty, isSaving]);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  return {
    status,
    isDirty,
    isSaving,
    lastSavedAt,
    save,
    reset,
  };
}

/**
 * Status indicator component props helper
 */
export function getStatusIndicator(status: AutoSaveStatus): {
  text: string;
  variant: 'default' | 'secondary' | 'destructive';
  icon: 'saving' | 'saved' | 'error' | 'none';
} {
  switch (status) {
    case 'saving':
      return { text: 'Saving...', variant: 'secondary', icon: 'saving' };
    case 'saved':
      return { text: 'Saved', variant: 'default', icon: 'saved' };
    case 'error':
      return { text: 'Error saving', variant: 'destructive', icon: 'error' };
    case 'dirty':
      return { text: 'Unsaved changes', variant: 'secondary', icon: 'none' };
    default:
      return { text: '', variant: 'default', icon: 'none' };
  }
}
