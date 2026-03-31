'use client';

/**
 * useAutoSaveEditor — 2-second debounced auto-save hook for Monaco IDE.
 *
 * Tracks dirty state via FileStore and saves after a 2000ms idle period.
 * Supports Cmd+S / Ctrl+S for immediate flush, dispatching a
 * 'file-editor:request-save' custom DOM event (mirrors existing 'issue-force-save'
 * pattern from the issue-note feature).
 *
 * On unmount, flushes any pending save to prevent data loss.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useFileStore } from '@/stores/RootStore';

interface AutoSaveState {
  isSaving: boolean;
  lastSaved: Date | null;
}

export function useAutoSaveEditor(
  fileId: string | null,
  content: string,
  saveFn: (id: string, content: string) => Promise<void>
): AutoSaveState {
  const fileStore = useFileStore();
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const contentRef = useRef(content);
  const fileIdRef = useRef(fileId);
  const saveFnRef = useRef(saveFn);
  const isDirtyRef = useRef(false);
  const isFirstRenderRef = useRef(true);

  // Keep refs current for stable callbacks
  useEffect(() => {
    contentRef.current = content;
    fileIdRef.current = fileId;
    saveFnRef.current = saveFn;
  });

  const doSave = useCallback(async () => {
    const id = fileIdRef.current;
    const value = contentRef.current;
    if (!id || !isDirtyRef.current) return;

    setIsSaving(true);
    try {
      await saveFnRef.current(id, value);
      fileStore.markClean(id);
      isDirtyRef.current = false;
      setLastSaved(new Date());
    } finally {
      setIsSaving(false);
    }
  }, [fileStore]);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const scheduleAutoSave = useCallback(() => {
    clearTimer();
    timerRef.current = setTimeout(() => {
      void doSave();
    }, 2000);
  }, [clearTimer, doSave]);

  // Reset first-render flag when fileId changes so we skip the initial content load
  useEffect(() => {
    isFirstRenderRef.current = true;
  }, [fileId]);

  // Watch content changes (debounce auto-save, skip initial mount)
  useEffect(() => {
    if (!fileId) return;
    if (isFirstRenderRef.current) {
      isFirstRenderRef.current = false;
      return;
    }
    isDirtyRef.current = true;
    scheduleAutoSave();
  }, [content, fileId, scheduleAutoSave]);

  // Listen for file-editor:request-save DOM event (dispatched by StatusBar, Cmd+S binding)
  useEffect(() => {
    const handleRequestSave = () => {
      clearTimer();
      void doSave();
    };
    window.addEventListener('file-editor:request-save', handleRequestSave);
    return () => window.removeEventListener('file-editor:request-save', handleRequestSave);
  }, [clearTimer, doSave]);

  // Cleanup: flush on unmount if dirty
  useEffect(() => {
    return () => {
      clearTimer();
      if (isDirtyRef.current && fileIdRef.current) {
        // Fire-and-forget save on unmount to prevent data loss
        void saveFnRef.current(fileIdRef.current, contentRef.current);
      }
    };
  }, [clearTimer]);

  return { isSaving, lastSaved };
}
