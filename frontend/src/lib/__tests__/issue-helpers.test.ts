import { describe, it, expect } from 'vitest';
import { stateNameToKey } from '../issue-helpers';

describe('stateNameToKey', () => {
  it('converts single-word state names', () => {
    expect(stateNameToKey('Backlog')).toBe('backlog');
    expect(stateNameToKey('Todo')).toBe('todo');
    expect(stateNameToKey('Done')).toBe('done');
    expect(stateNameToKey('Cancelled')).toBe('cancelled');
  });

  it('converts multi-word state names with spaces', () => {
    expect(stateNameToKey('In Progress')).toBe('in_progress');
    expect(stateNameToKey('In Review')).toBe('in_review');
  });

  it('handles already-lowercase input', () => {
    expect(stateNameToKey('backlog')).toBe('backlog');
    expect(stateNameToKey('in_progress')).toBe('in_progress');
  });

  it('handles multiple consecutive spaces', () => {
    expect(stateNameToKey('In  Progress')).toBe('in_progress');
  });

  it('handles leading/trailing whitespace', () => {
    expect(stateNameToKey(' In Progress ')).toBe('_in_progress_');
  });
});
