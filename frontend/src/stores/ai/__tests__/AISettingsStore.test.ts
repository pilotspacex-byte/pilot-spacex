/**
 * Tests for AISettingsStore - model listing extension.
 *
 * 13-03: availableModels observable + loadModels() action.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Use vi.hoisted to ensure mockGet is available before vi.mock hoisting
const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock('@/services/api/client', () => ({
  apiClient: {
    get: mockGet,
  },
}));

vi.mock('@/services/api/ai', () => ({
  aiApi: {
    getWorkspaceSettings: vi.fn().mockResolvedValue({
      workspaceId: 'ws-1',
      providers: [],
      features: {
        ghostTextEnabled: false,
        marginAnnotationsEnabled: false,
        aiContextEnabled: false,
        issueExtractionEnabled: false,
        prReviewEnabled: false,
        autoApproveNonDestructive: false,
      },
      defaultProvider: 'anthropic',
      costLimitUsd: null,
    }),
    updateWorkspaceSettings: vi.fn(),
  },
}));

import { AISettingsStore } from '../AISettingsStore';
import type { AIStore } from '../AIStore';

const mockRootStore = {} as AIStore;

describe('AISettingsStore - model listing', () => {
  let store: AISettingsStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = new AISettingsStore(mockRootStore);
  });

  it('has availableModels observable initialized to empty array', () => {
    expect(store.availableModels).toEqual([]);
  });

  it('has isLoadingModels initialized to false', () => {
    expect(store.isLoadingModels).toBe(false);
  });

  it('loadModels fetches from /ai/configurations/models with workspace_id param', async () => {
    const mockModels = [
      {
        provider_config_id: 'cfg-1',
        provider: 'anthropic',
        model_id: 'claude-opus-4-5',
        display_name: 'Claude Opus 4.5',
        is_selectable: true,
      },
    ];
    mockGet.mockResolvedValueOnce({ items: mockModels, total: 1 });

    await store.loadModels('ws-1');

    expect(mockGet).toHaveBeenCalledWith('/ai/configurations/models', {
      params: { workspace_id: 'ws-1' },
    });
    expect(store.availableModels).toEqual(mockModels);
  });

  it('sets isLoadingModels to true during fetch and false after', async () => {
    let resolveGet!: (value: unknown) => void;
    mockGet.mockReturnValueOnce(
      new Promise((res) => {
        resolveGet = res;
      })
    );

    const promise = store.loadModels('ws-1');
    expect(store.isLoadingModels).toBe(true);

    resolveGet({ items: [], total: 0 });
    await promise;

    expect(store.isLoadingModels).toBe(false);
  });

  it('sets availableModels to [] and isLoadingModels to false on error', async () => {
    mockGet.mockRejectedValueOnce(new Error('Network error'));

    await store.loadModels('ws-1');

    expect(store.availableModels).toEqual([]);
    expect(store.isLoadingModels).toBe(false);
  });
});
