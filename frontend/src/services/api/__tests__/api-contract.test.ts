/**
 * API contract tests: frontend types must match backend serialization.
 *
 * C-3: ConfirmAllResponse uses camelCase (backend uses BaseSchema → to_camel)
 * W-6: tasksApi.decompose() must return DecomposeResponse (not TaskListResponse)
 */

import { describe, expect, it } from 'vitest';
import type { ConfirmAllResponse } from '../ai';
import type { DecomposeResponse } from '@/types';

// ---------------------------------------------------------------------------
// C-3: ConfirmAllResponse must use camelCase field names
// ---------------------------------------------------------------------------

describe('ConfirmAllResponse - C-3 contract', () => {
  it('reads confirmedCount (camelCase) from backend JSON', () => {
    // Backend sends camelCase because intent.py uses BaseSchema (to_camel)
    const backendJson = {
      confirmed: [],
      confirmedCount: 5,
      remainingCount: 3,
      deduplicatingCount: 2,
    };

    const response = backendJson as ConfirmAllResponse;

    expect(response.confirmedCount).toBe(5);
    expect(response.remainingCount).toBe(3);
    expect(response.deduplicatingCount).toBe(2);

    // snake_case variants must not exist as typed properties
    // @ts-expect-error -- snake_case must not be a valid property on ConfirmAllResponse
    expect(response.confirmed_count).toBeUndefined();
    // @ts-expect-error -- snake_case must not be a valid property
    expect(response.remaining_count).toBeUndefined();
    // @ts-expect-error -- snake_case must not be a valid property
    expect(response.deduplicating_count).toBeUndefined();
  });

  it('ConfirmAllResponse interface matches backend BaseSchema camelCase output', () => {
    // Type-level validation: constructing a ConfirmAllResponse with camelCase fields
    // If the interface still uses snake_case, TypeScript will error on these assignments
    const valid: ConfirmAllResponse = {
      confirmed: [],
      confirmedCount: 0,
      remainingCount: 0,
      deduplicatingCount: 0,
    };

    expect(valid.confirmedCount).toBe(0);
    expect(valid.remainingCount).toBe(0);
    expect(valid.deduplicatingCount).toBe(0);
  });
});

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
