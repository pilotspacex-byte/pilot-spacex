import { describe, it, expect } from 'vitest';
import { stateNameToKey, getIssueStateKey } from '../issue-helpers';

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

describe('getIssueStateKey', () => {
  it('handles plain string state keys from API', () => {
    expect(getIssueStateKey('backlog')).toBe('backlog');
    expect(getIssueStateKey('in_progress')).toBe('in_progress');
    expect(getIssueStateKey('todo')).toBe('todo');
    expect(getIssueStateKey('done')).toBe('done');
    expect(getIssueStateKey('in_review')).toBe('in_review');
    expect(getIssueStateKey('cancelled')).toBe('cancelled');
  });

  it('handles StateBrief objects', () => {
    expect(
      getIssueStateKey({ id: '1', name: 'In Progress', color: '#000', group: 'started' } as never)
    ).toBe('in_progress');
    expect(
      getIssueStateKey({ id: '2', name: 'Done', color: '#000', group: 'completed' } as never)
    ).toBe('done');
    expect(
      getIssueStateKey({ id: '3', name: 'Backlog', color: '#000', group: 'backlog' } as never)
    ).toBe('backlog');
  });

  it('returns backlog for undefined or null', () => {
    expect(getIssueStateKey(undefined)).toBe('backlog');
    expect(getIssueStateKey(null)).toBe('backlog');
  });
});
