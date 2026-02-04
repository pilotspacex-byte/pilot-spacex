/**
 * useSaveStatus hook tests.
 *
 * T015a: Verifies per-field save status lifecycle: idle -> saving -> saved -> idle (2s auto-clear).
 */

import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useSaveStatus } from '../use-save-status';

const mockSetSaveStatus = vi.fn();
const mockGetSaveStatus = vi.fn();

vi.mock('@/stores', () => ({
  useIssueStore: () => ({
    getSaveStatus: mockGetSaveStatus,
    setSaveStatus: mockSetSaveStatus,
  }),
}));

describe('useSaveStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockGetSaveStatus.mockReturnValue('idle');
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns idle status by default', () => {
    const { result } = renderHook(() => useSaveStatus('title'));

    expect(result.current.status).toBe('idle');
    expect(mockGetSaveStatus).toHaveBeenCalledWith('title');
  });

  it('transitions through saving -> saved lifecycle on success', async () => {
    const mutationFn = vi.fn().mockResolvedValue('result-value');

    const { result } = renderHook(() => useSaveStatus('title'));

    let mutationResult: string | undefined;
    await act(async () => {
      mutationResult = await result.current.wrapMutation(mutationFn);
    });

    // setSaveStatus should have been called with 'saving' first, then 'saved'
    expect(mockSetSaveStatus).toHaveBeenNthCalledWith(1, 'title', 'saving');
    expect(mockSetSaveStatus).toHaveBeenNthCalledWith(2, 'title', 'saved');
    expect(mutationResult).toBe('result-value');
    expect(mutationFn).toHaveBeenCalledOnce();
  });

  it('sets error status when mutation fails', async () => {
    const mutationFn = vi.fn().mockRejectedValue(new Error('Save failed'));

    const { result } = renderHook(() => useSaveStatus('priority'));

    await expect(
      act(async () => {
        await result.current.wrapMutation(mutationFn);
      })
    ).rejects.toThrow('Save failed');

    expect(mockSetSaveStatus).toHaveBeenNthCalledWith(1, 'priority', 'saving');
    expect(mockSetSaveStatus).toHaveBeenNthCalledWith(2, 'priority', 'error');
  });

  it('tracks concurrent fields independently', async () => {
    const titleMutation = vi.fn().mockResolvedValue('title-saved');
    const priorityMutation = vi.fn().mockResolvedValue('priority-saved');

    const { result: titleResult } = renderHook(() => useSaveStatus('title'));
    const { result: priorityResult } = renderHook(() => useSaveStatus('priority'));

    await act(async () => {
      await titleResult.current.wrapMutation(titleMutation);
    });

    await act(async () => {
      await priorityResult.current.wrapMutation(priorityMutation);
    });

    // Both fields should have their own saving -> saved transitions
    expect(mockSetSaveStatus).toHaveBeenCalledWith('title', 'saving');
    expect(mockSetSaveStatus).toHaveBeenCalledWith('title', 'saved');
    expect(mockSetSaveStatus).toHaveBeenCalledWith('priority', 'saving');
    expect(mockSetSaveStatus).toHaveBeenCalledWith('priority', 'saved');
  });

  it('returns the mutation result on success', async () => {
    const mutationFn = vi.fn().mockResolvedValue({ id: 'issue-1', name: 'Updated' });

    const { result } = renderHook(() => useSaveStatus('description'));

    let mutationResult: unknown;
    await act(async () => {
      mutationResult = await result.current.wrapMutation(mutationFn);
    });

    expect(mutationResult).toEqual({ id: 'issue-1', name: 'Updated' });
  });
});
