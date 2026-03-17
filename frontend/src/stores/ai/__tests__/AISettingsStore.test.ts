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
      defaultLlmProvider: 'anthropic',
      defaultEmbeddingProvider: 'google',
      costLimitUsd: null,
    }),
    updateWorkspaceSettings: vi.fn(),
  },
}));

import { AISettingsStore } from '../AISettingsStore';
import type { AIStore } from '../AIStore';

const mockRootStore = {} as AIStore;

describe('AISettingsStore - validateKey', () => {
  let store: AISettingsStore;

  beforeEach(() => {
    store = new AISettingsStore(mockRootStore);
  });

  it('rejects keys shorter than 10 characters for any provider', () => {
    expect(store.validateKey('anthropic', 'short')).toBe(false);
    expect(store.validateKey('openai', 'sk-12345')).toBe(false);
    expect(store.validateKey('google', 'AIza1234')).toBe(false);
    expect(store.validateKey('kimi', '123456789')).toBe(false);
    expect(store.validateKey('glm', 'abcdefghi')).toBe(false);
    expect(store.validateKey('custom', 'x')).toBe(false);
  });

  it('validates anthropic keys must start with sk-ant-', () => {
    expect(store.validateKey('anthropic', 'sk-ant-api3xxxxxxxx')).toBe(true);
    expect(store.validateKey('anthropic', 'sk-wrongprefix12')).toBe(false);
  });

  it('validates openai keys must start with sk-', () => {
    expect(store.validateKey('openai', 'sk-proj-xxxxxxxx')).toBe(true);
    expect(store.validateKey('openai', 'wrong-prefix-key')).toBe(false);
  });

  it('validates google keys must start with AIza', () => {
    expect(store.validateKey('google', 'AIzaSyBxxxxxxxxxxxxxxx')).toBe(true);
    expect(store.validateKey('google', 'wrong-prefix-key')).toBe(false);
  });

  it('validates kimi keys with length check only', () => {
    expect(store.validateKey('kimi', 'any-valid-key-longer-than-10')).toBe(true);
  });

  it('validates glm keys with length check only', () => {
    expect(store.validateKey('glm', 'any-valid-key-longer-than-10')).toBe(true);
  });

  it('validates custom keys with length check only', () => {
    expect(store.validateKey('custom', 'any-valid-key-longer-than-10')).toBe(true);
  });

  it('accepts unknown provider types with length check only', () => {
    expect(store.validateKey('some-future-provider', 'any-valid-key-longer-than-10')).toBe(true);
  });
});

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
