/**
 * Unit tests for useAutoSave hook.
 * Validates debounced auto-save, status transitions, retry logic,
 * manual save, reset, and the ref-based version sentinel pattern
 * used to avoid re-renders on every keystroke.
 *
 * @module features/notes/hooks/__tests__/useAutoSave.test
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAutoSave } from '../useAutoSave';

describe('useAutoSave', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const defaultOptions = {
    data: 'initial',
    onSave: vi.fn().mockResolvedValue(undefined),
    debounceMs: 2000,
    enabled: true,
  };

  it('should start with idle status', () => {
    const { result } = renderHook(() => useAutoSave(defaultOptions));

    expect(result.current.status).toBe('idle');
    expect(result.current.isDirty).toBe(false);
    expect(result.current.isSaving).toBe(false);
    expect(result.current.lastSavedAt).toBeNull();
  });

  it('should mark as dirty when data changes', () => {
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ ...defaultOptions, data }),
      { initialProps: { data: 'initial' } }
    );

    rerender({ data: 'changed' });

    expect(result.current.status).toBe('dirty');
    expect(result.current.isDirty).toBe(true);
  });

  it('should debounce save by configured delay', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ ...defaultOptions, data, onSave }),
      { initialProps: { data: 'initial' } }
    );

    rerender({ data: 'changed' });

    // Before debounce expires
    await act(async () => {
      vi.advanceTimersByTime(1999);
    });
    expect(onSave).not.toHaveBeenCalled();

    // After debounce expires
    await act(async () => {
      vi.advanceTimersByTime(1);
    });
    expect(onSave).toHaveBeenCalledWith('changed');
  });

  it('should transition to saving then saved status', async () => {
    let resolvePromise: () => void;
    const onSave = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolvePromise = resolve;
        })
    );

    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ ...defaultOptions, data, onSave }),
      { initialProps: { data: 'initial' } }
    );

    rerender({ data: 'changed' });

    // Trigger debounced save
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    expect(result.current.status).toBe('saving');
    expect(result.current.isSaving).toBe(true);

    // Resolve the save
    await act(async () => {
      resolvePromise!();
    });

    expect(result.current.status).toBe('saved');
    expect(result.current.lastSavedAt).toBeInstanceOf(Date);

    // After 2s, reverts to idle
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current.status).toBe('idle');
  });

  it('should not save when disabled', () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(
      ({ data, enabled }) => useAutoSave({ ...defaultOptions, data, onSave, enabled }),
      { initialProps: { data: 'initial', enabled: false } }
    );

    rerender({ data: 'changed', enabled: false });

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(onSave).not.toHaveBeenCalled();
  });

  it('should not trigger save when data has not changed', () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ ...defaultOptions, data, onSave }),
      { initialProps: { data: 'initial' } }
    );

    // Re-render with same data
    rerender({ data: 'initial' });

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(onSave).not.toHaveBeenCalled();
  });

  it('should perform manual save immediately', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useAutoSave({ ...defaultOptions, data: 'content', onSave })
    );

    await act(async () => {
      await result.current.save();
    });

    expect(onSave).toHaveBeenCalledWith('content');
  });

  it('should reset dirty state and cancel pending timer', () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ ...defaultOptions, data, onSave }),
      { initialProps: { data: 'initial' } }
    );

    rerender({ data: 'changed' });
    expect(result.current.status).toBe('dirty');

    act(() => {
      result.current.reset();
    });

    expect(result.current.status).toBe('idle');

    // Advancing time should not trigger save since timer was cleared
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(onSave).not.toHaveBeenCalled();
  });

  it('should retry on save failure up to maxRetries', async () => {
    const onSave = vi.fn().mockRejectedValue(new Error('Network error'));
    const { rerender } = renderHook(
      ({ data }) =>
        useAutoSave({
          ...defaultOptions,
          data,
          onSave,
          maxRetries: 3,
          retryDelayMs: 1000,
        }),
      { initialProps: { data: 'initial' } }
    );

    rerender({ data: 'changed' });

    // Trigger debounced save (attempt 1)
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    // Retry 1 (after 1s delay)
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });

    // Retry 2 (after 2s delay)
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    // 3 total calls: initial + 2 retries, then error
    expect(onSave).toHaveBeenCalledTimes(3);
  });

  describe('version sentinel pattern (ref-based optimization)', () => {
    it('should work with numeric saveVersion as data', async () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      // Simulates the page pattern: saveVersion (number) as data,
      // onSave reads from a ref instead of using the data param
      const contentRef = { current: { type: 'doc', content: [] as Record<string, unknown>[] } };

      const { result, rerender } = renderHook(
        ({ version }) =>
          useAutoSave({
            data: version,
            onSave: async () => {
              const content = contentRef.current;
              if (content) {
                await onSave(content);
              }
            },
            debounceMs: 2000,
            enabled: true,
          }),
        { initialProps: { version: 0 } }
      );

      // Simulate keystroke: update ref, bump version
      contentRef.current = { type: 'doc', content: [{ type: 'paragraph' }] };
      rerender({ version: 1 });

      expect(result.current.status).toBe('dirty');

      // Wait for debounce
      await act(async () => {
        vi.advanceTimersByTime(2000);
      });

      // onSave should have received the ref content, not the version number
      expect(onSave).toHaveBeenCalledWith({
        type: 'doc',
        content: [{ type: 'paragraph' }],
      });
    });

    it('should debounce rapid version increments', async () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      const contentRef = { current: 'v0' };

      const { rerender } = renderHook(
        ({ version }) =>
          useAutoSave({
            data: version,
            onSave: async () => {
              await onSave(contentRef.current);
            },
            debounceMs: 2000,
            enabled: true,
          }),
        { initialProps: { version: 0 } }
      );

      // Rapid keystrokes: bump version multiple times within debounce window
      contentRef.current = 'v1';
      rerender({ version: 1 });

      act(() => {
        vi.advanceTimersByTime(500);
      });

      contentRef.current = 'v2';
      rerender({ version: 2 });

      act(() => {
        vi.advanceTimersByTime(500);
      });

      contentRef.current = 'v3';
      rerender({ version: 3 });

      // Only 1s has passed since last keystroke, should not have saved yet
      expect(onSave).not.toHaveBeenCalled();

      // Wait for full debounce from last change
      await act(async () => {
        vi.advanceTimersByTime(2000);
      });

      // Should save only once with the latest content
      expect(onSave).toHaveBeenCalledTimes(1);
      expect(onSave).toHaveBeenCalledWith('v3');
    });

    it('should support reset with version sentinel to prevent initial save', () => {
      const onSave = vi.fn().mockResolvedValue(undefined);

      const { result, rerender } = renderHook(
        ({ version, enabled }) =>
          useAutoSave({
            data: version,
            onSave: async () => {
              await onSave();
            },
            debounceMs: 2000,
            enabled,
          }),
        { initialProps: { version: 0, enabled: false } }
      );

      // Reset baseline (like the page does on content init)
      act(() => {
        result.current.reset();
      });

      // Enable auto-save (simulates isAutosaveReady = true)
      rerender({ version: 0, enabled: true });

      // No save should trigger since version hasn't changed from baseline
      act(() => {
        vi.advanceTimersByTime(5000);
      });
      expect(onSave).not.toHaveBeenCalled();

      // Now bump version (user edits)
      rerender({ version: 1, enabled: true });

      act(() => {
        vi.advanceTimersByTime(2000);
      });
      expect(onSave).toHaveBeenCalledTimes(1);
    });
  });

  describe('beforeunload protection', () => {
    it('should set beforeunload handler when dirty', () => {
      const addSpy = vi.spyOn(window, 'addEventListener');
      const { rerender } = renderHook(({ data }) => useAutoSave({ ...defaultOptions, data }), {
        initialProps: { data: 'initial' },
      });

      rerender({ data: 'changed' });

      expect(addSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function));
      addSpy.mockRestore();
    });
  });

  describe('getStatusIndicator', () => {
    it('should be importable and return correct variants', async () => {
      const { getStatusIndicator } = await import('../useAutoSave');

      expect(getStatusIndicator('saving')).toEqual({
        text: 'Saving...',
        variant: 'secondary',
        icon: 'saving',
      });
      expect(getStatusIndicator('saved')).toEqual({
        text: 'Saved',
        variant: 'default',
        icon: 'saved',
      });
      expect(getStatusIndicator('error')).toEqual({
        text: 'Error saving',
        variant: 'destructive',
        icon: 'error',
      });
      expect(getStatusIndicator('idle')).toEqual({
        text: '',
        variant: 'default',
        icon: 'none',
      });
    });
  });
});
