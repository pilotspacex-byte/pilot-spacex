/**
 * Unit tests for PilotSpaceStore model selection extension.
 *
 * RED phase: Tests are written first, before implementation.
 * Tests cover:
 * - selectedModel observable is null by default
 * - setSelectedModel updates the observable
 * - setSelectedModel persists to localStorage key chat_model_{workspaceId}
 * - loadSelectedModel restores from localStorage
 * - loadSelectedModel handles invalid JSON gracefully
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock supabase before any store imports
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token' } },
      }),
    },
  },
}));

vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn().mockImplementation(() => ({
    connect: vi.fn().mockResolvedValue(undefined),
    abort: vi.fn(),
  })),
}));

import { PilotSpaceStore } from '../PilotSpaceStore';
import type { AIStore } from '../AIStore';

const mockAIStore = {} as AIStore;

describe('PilotSpaceStore - model selection', () => {
  let store: PilotSpaceStore;

  beforeEach(() => {
    // Clear localStorage between tests to avoid state leakage
    localStorage.clear();

    store = new PilotSpaceStore(mockAIStore);
    store.setWorkspaceId('ws-test');
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('selectedModel is null by default', () => {
    const freshStore = new PilotSpaceStore(mockAIStore);
    expect(freshStore.selectedModel).toBeNull();
  });

  it('setSelectedModel updates observable', () => {
    store.setSelectedModel('anthropic', 'claude-sonnet-4', 'cfg-1');

    expect(store.selectedModel).toEqual({
      provider: 'anthropic',
      modelId: 'claude-sonnet-4',
      configId: 'cfg-1',
    });
  });

  it('setSelectedModel persists to localStorage with chat_model_{workspaceId} key', () => {
    store.setSelectedModel('anthropic', 'claude-sonnet-4', 'cfg-1');

    const stored = localStorage.getItem('chat_model_ws-test');
    expect(stored).toBe(
      JSON.stringify({ provider: 'anthropic', modelId: 'claude-sonnet-4', configId: 'cfg-1' })
    );
  });

  it('setSelectedModel does not persist when workspaceId is null', () => {
    const freshStore = new PilotSpaceStore(mockAIStore);
    // workspaceId is null by default
    freshStore.setSelectedModel('anthropic', 'claude-sonnet-4', 'cfg-1');

    // No key should be set in localStorage
    expect(localStorage.getItem('chat_model_null')).toBeNull();
    expect(localStorage.length).toBe(0);
  });

  it('loadSelectedModel restores selectedModel from localStorage', () => {
    const stored = JSON.stringify({
      provider: 'openai',
      modelId: 'gpt-4o',
      configId: 'cfg-openai-1',
    });
    localStorage.setItem('chat_model_ws-restore', stored);

    store.loadSelectedModel('ws-restore');

    expect(store.selectedModel).toEqual({
      provider: 'openai',
      modelId: 'gpt-4o',
      configId: 'cfg-openai-1',
    });
  });

  it('loadSelectedModel leaves selectedModel null when key is not in localStorage', () => {
    // localStorageMock is empty, no key for ws-missing
    store.loadSelectedModel('ws-missing');

    expect(store.selectedModel).toBeNull();
  });

  it('loadSelectedModel handles invalid JSON gracefully — selectedModel remains null', () => {
    localStorage.setItem('chat_model_ws-bad', 'not-valid-json{{{');

    expect(() => {
      store.loadSelectedModel('ws-bad');
    }).not.toThrow();

    expect(store.selectedModel).toBeNull();
  });

  it('loadSelectedModel ignores partial data — requires provider + modelId + configId', () => {
    // Missing configId
    localStorage.setItem(
      'chat_model_ws-partial',
      JSON.stringify({
        provider: 'anthropic',
        modelId: 'claude-sonnet-4',
        // configId missing
      })
    );

    store.loadSelectedModel('ws-partial');

    expect(store.selectedModel).toBeNull();
  });

  it('setWorkspaceId calls loadSelectedModel when workspaceId changes', () => {
    // Pre-populate localStorage for ws-2
    localStorage.setItem(
      'chat_model_ws-2',
      JSON.stringify({
        provider: 'anthropic',
        modelId: 'claude-opus-4-5',
        configId: 'cfg-ant-1',
      })
    );

    store.setWorkspaceId('ws-2');

    expect(store.selectedModel).toEqual({
      provider: 'anthropic',
      modelId: 'claude-opus-4-5',
      configId: 'cfg-ant-1',
    });
  });

  it('selectedModel is per-workspace — switching workspaces restores correct selection', () => {
    // Workspace 1 selection
    localStorage.setItem(
      'chat_model_ws-A',
      JSON.stringify({ provider: 'anthropic', modelId: 'claude-sonnet-4', configId: 'cfg-A' })
    );
    // Workspace 2 selection
    localStorage.setItem(
      'chat_model_ws-B',
      JSON.stringify({ provider: 'openai', modelId: 'gpt-4o', configId: 'cfg-B' })
    );

    store.setWorkspaceId('ws-A');
    expect(store.selectedModel?.modelId).toBe('claude-sonnet-4');

    store.setWorkspaceId('ws-B');
    expect(store.selectedModel?.modelId).toBe('gpt-4o');
  });
});
