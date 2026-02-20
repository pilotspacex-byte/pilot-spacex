/**
 * Unit tests for PilotSpaceStore homepage context management (T031).
 *
 * Tests homepage context injection, mutual exclusion with note context,
 * and inclusion in conversationContext computed property.
 *
 * @module stores/ai/__tests__/PilotSpaceStore.homepage-context.test
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock supabase before any store imports (avoids missing env error)
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
import type { HomepageContextData, NoteContext } from '../types/store-types';
import type { AIStore } from '../AIStore';

const MOCK_HOMEPAGE_CONTEXT: HomepageContextData = {
  digestSummary: 'Workspace has 3 stale issues, 2 cycle risks, 1 blocked items.',
  totalSuggestionCount: 12,
  staleIssueCount: 3,
  cycleRiskCount: 2,
  recentNotes: [
    { id: 'note-1', title: 'Sprint Planning' },
    { id: 'note-2', title: 'Architecture Review' },
  ],
};

const MOCK_NOTE_CONTEXT: NoteContext = {
  noteId: 'note-abc',
  noteTitle: 'Test Note',
  selectedText: undefined,
  selectedBlockIds: undefined,
};

describe('PilotSpaceStore homepage context', () => {
  let store: PilotSpaceStore;

  beforeEach(() => {
    const mockRootStore = {} as AIStore;
    store = new PilotSpaceStore(mockRootStore);
    store.setWorkspaceId('workspace-123');
  });

  it('setHomepageContext stores data correctly', () => {
    store.setHomepageContext(MOCK_HOMEPAGE_CONTEXT);

    expect(store.homepageContext).toEqual(MOCK_HOMEPAGE_CONTEXT);
    expect(store.homepageContext?.digestSummary).toBe(
      'Workspace has 3 stale issues, 2 cycle risks, 1 blocked items.'
    );
    expect(store.homepageContext?.staleIssueCount).toBe(3);
    expect(store.homepageContext?.recentNotes).toHaveLength(2);
  });

  it('clearHomepageContext nullifies data', () => {
    store.setHomepageContext(MOCK_HOMEPAGE_CONTEXT);
    expect(store.homepageContext).not.toBeNull();

    store.clearHomepageContext();
    expect(store.homepageContext).toBeNull();
  });

  it('homepageContext included in conversationContext when set', () => {
    store.setHomepageContext(MOCK_HOMEPAGE_CONTEXT);

    const ctx = store.conversationContext;
    expect(ctx).not.toBeNull();
    expect(ctx!.homepageDigestSummary).toBe(
      'Workspace has 3 stale issues, 2 cycle risks, 1 blocked items.'
    );
  });

  it('conversationContext omits homepageDigestSummary when no homepage context', () => {
    const ctx = store.conversationContext;
    expect(ctx).not.toBeNull();
    expect(ctx!.homepageDigestSummary).toBeUndefined();
  });

  it('setting note context auto-clears homepage context', () => {
    store.setHomepageContext(MOCK_HOMEPAGE_CONTEXT);
    expect(store.homepageContext).not.toBeNull();

    store.setNoteContext(MOCK_NOTE_CONTEXT);

    expect(store.homepageContext).toBeNull();
    expect(store.noteContext).toEqual(MOCK_NOTE_CONTEXT);
  });

  it('setting homepage context auto-clears note context', () => {
    store.setNoteContext(MOCK_NOTE_CONTEXT);
    expect(store.noteContext).not.toBeNull();

    store.setHomepageContext(MOCK_HOMEPAGE_CONTEXT);

    expect(store.noteContext).toBeNull();
    expect(store.homepageContext).toEqual(MOCK_HOMEPAGE_CONTEXT);
  });

  it('clearContext clears homepage context along with other contexts', () => {
    store.setHomepageContext(MOCK_HOMEPAGE_CONTEXT);
    store.setIssueContext({ issueId: 'issue-1' });

    store.clearContext();

    expect(store.homepageContext).toBeNull();
    expect(store.issueContext).toBeNull();
    expect(store.noteContext).toBeNull();
  });

  it('setNoteContext with null does not clear homepage context', () => {
    store.setHomepageContext(MOCK_HOMEPAGE_CONTEXT);

    store.setNoteContext(null);

    expect(store.homepageContext).toEqual(MOCK_HOMEPAGE_CONTEXT);
  });
});
