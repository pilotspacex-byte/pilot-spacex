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

  it('handles leading/trailing whitespace by trimming', () => {
    expect(stateNameToKey(' In Progress ')).toBe('in_progress');
    expect(stateNameToKey('  Done  ')).toBe('done');
  });

  it('returns backlog for unrecognized state names', () => {
    expect(stateNameToKey('Unknown')).toBe('backlog');
    expect(stateNameToKey('custom_state')).toBe('backlog');
    expect(stateNameToKey('')).toBe('backlog');
    expect(stateNameToKey('INVALID')).toBe('backlog');
  });

  it('returns valid state for mixed-case input', () => {
    expect(stateNameToKey('IN PROGRESS')).toBe('in_progress');
    expect(stateNameToKey('DONE')).toBe('done');
    expect(stateNameToKey('in_review')).toBe('in_review');
  });

  it('returns backlog for undefined or null input', () => {
    expect(stateNameToKey(undefined)).toBe('backlog');
    expect(stateNameToKey(null)).toBe('backlog');
  });
});
