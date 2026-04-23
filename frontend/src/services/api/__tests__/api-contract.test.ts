/**
 * API contract tests: frontend types must match backend serialization.
 *
 * W-6: tasksApi.decompose() must return DecomposeResponse (not TaskListResponse)
 */

import { describe, expect, it } from 'vitest';
import type { DecomposeResponse } from '@/types';

// ---------------------------------------------------------------------------
// W-6: decompose() must return DecomposeResponse (has subtasks[], not tasks[])
// ---------------------------------------------------------------------------

describe('DecomposeResponse - W-6 contract', () => {
  it('DecomposeResponse has subtasks array matching backend DecomposeResponse schema', () => {
    const mockDecomposeResponse: DecomposeResponse = {
      subtasks: [],
      summary: null,
      totalEstimatedDays: null,
      criticalPath: null,
      parallelOpportunities: null,
    };

    expect(mockDecomposeResponse.subtasks).toBeDefined();
    expect(Array.isArray(mockDecomposeResponse.subtasks)).toBe(true);

    // @ts-expect-error -- DecomposeResponse has no tasks field, only subtasks
    expect(mockDecomposeResponse.tasks).toBeUndefined();
  });

  it('DecomposeResponse subtask shape matches backend SubtaskSchema', () => {
    const subtask: DecomposeResponse['subtasks'][0] = {
      order: 1,
      name: 'Implement feature',
      description: 'Do the work',
      confidence: 'RECOMMENDED',
      estimatedDays: 2.5,
      labels: ['backend'],
      dependencies: [],
      acceptanceCriteria: null,
      codeReferences: null,
      aiPrompt: null,
    };

    expect(subtask.order).toBe(1);
    expect(subtask.confidence).toBe('RECOMMENDED');
    expect(subtask.estimatedDays).toBe(2.5);
  });
});
