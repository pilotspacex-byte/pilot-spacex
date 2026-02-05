/**
 * Tests for setProjectContext (T8), setActiveSkill (T9), addMentionedAgent (T9),
 * and clearContext() interactions with each field.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}));

vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn(),
}));

import { PilotSpaceStore } from '../PilotSpaceStore';
import type { AIStore } from '../AIStore';

describe('PilotSpaceStore.setProjectContext (T8)', () => {
  let store: PilotSpaceStore;

  beforeEach(() => {
    store = new PilotSpaceStore({} as AIStore);
    store.setWorkspaceId('ws-001');
  });

  it('stores project context with projectId, name, and slug', () => {
    const ctx = { projectId: 'proj-1', name: 'Alpha', slug: 'alpha' };
    store.setProjectContext(ctx);

    expect(store.projectContext).toEqual(ctx);
    expect(store.projectContext?.projectId).toBe('proj-1');
  });

  it('conversationContext.projectId reflects stored value', () => {
    store.setProjectContext({ projectId: 'proj-2' });

    expect(store.conversationContext!.projectId).toBe('proj-2');
  });

  it('conversationContext.projectId is null when no project set', () => {
    expect(store.conversationContext!.projectId).toBeNull();
  });
  it('clearContext() resets projectContext to null', () => {
    store.setProjectContext({ projectId: 'proj-3', name: 'Beta' });
    store.clearContext();

    expect(store.projectContext).toBeNull();
  });
});

describe('PilotSpaceStore.setActiveSkill (T9)', () => {
  let store: PilotSpaceStore;

  beforeEach(() => {
    store = new PilotSpaceStore({} as AIStore);
    store.setWorkspaceId('ws-002');
  });

  it('stores skill name and args', () => {
    store.setActiveSkill('extract-issues', '--format=json');

    expect(store.activeSkill).toEqual({ name: 'extract-issues', args: '--format=json' });
  });

  it('stores skill with undefined args when none provided', () => {
    store.setActiveSkill('summarize');

    expect(store.activeSkill).toEqual({ name: 'summarize', args: undefined });
  });

  it('clearContext() resets activeSkill to null', () => {
    store.setActiveSkill('enhance-issue');
    store.clearContext();

    expect(store.activeSkill).toBeNull();
  });
});

describe('PilotSpaceStore.addMentionedAgent (T9)', () => {
  let store: PilotSpaceStore;

  beforeEach(() => {
    store = new PilotSpaceStore({} as AIStore);
    store.setWorkspaceId('ws-003');
  });

  it('adds agent to mentionedAgents array', () => {
    store.addMentionedAgent('pr-review');

    expect(store.mentionedAgents).toEqual(['pr-review']);
  });

  it('does not add duplicate agents', () => {
    store.addMentionedAgent('doc-gen');
    store.addMentionedAgent('doc-gen');

    expect(store.mentionedAgents).toEqual(['doc-gen']);
  });

  it('stores multiple distinct agents', () => {
    store.addMentionedAgent('pr-review');
    store.addMentionedAgent('doc-gen');
    store.addMentionedAgent('ai-context');

    expect(store.mentionedAgents).toHaveLength(3);
    expect(store.mentionedAgents).toEqual(['pr-review', 'doc-gen', 'ai-context']);
  });

  it('clearContext() resets mentionedAgents to empty array', () => {
    store.addMentionedAgent('pr-review');
    store.addMentionedAgent('doc-gen');
    store.clearContext();

    expect(store.mentionedAgents).toEqual([]);
  });
});
