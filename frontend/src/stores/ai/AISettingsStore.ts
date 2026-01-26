/**
 * AI Settings Store for workspace configuration.
 *
 * Manages workspace-level AI settings with:
 * - API key management (encrypted server-side)
 * - Feature toggles (ghost text, annotations, etc.)
 * - Validation and error handling
 */
import { makeAutoObservable, runInAction, computed } from 'mobx';
import { aiApi, type WorkspaceAISettings } from '@/services/api/ai';
import type { AIStore } from './AIStore';

export class AISettingsStore {
  settings: WorkspaceAISettings | null = null;
  isLoading = false;
  isSaving = false;
  error: string | null = null;
  validationErrors: Record<string, string> = {};
  currentWorkspaceId: string | null = null;

  constructor(_rootStore: AIStore) {
    makeAutoObservable(this, {
      anthropicKeySet: computed,
      openaiKeySet: computed,
      ghostTextEnabled: computed,
      marginAnnotationsEnabled: computed,
      aiContextEnabled: computed,
    });
  }

  get anthropicKeySet(): boolean {
    return this.settings?.anthropic_key_set ?? false;
  }

  get openaiKeySet(): boolean {
    return this.settings?.openai_key_set ?? false;
  }

  get ghostTextEnabled(): boolean {
    return this.settings?.ghost_text_enabled ?? false;
  }

  get marginAnnotationsEnabled(): boolean {
    return this.settings?.margin_annotations_enabled ?? false;
  }

  get aiContextEnabled(): boolean {
    return this.settings?.ai_context_enabled ?? false;
  }

  async loadSettings(workspaceId: string): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.error = null;
      this.currentWorkspaceId = workspaceId;
    });

    try {
      const response = await aiApi.getWorkspaceSettings(workspaceId);
      runInAction(() => {
        this.settings = response;
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load settings';
        this.isLoading = false;
      });
    }
  }

  async saveSettings(
    updates: Partial<WorkspaceAISettings> & {
      anthropic_api_key?: string;
      openai_api_key?: string;
    }
  ): Promise<void> {
    if (!this.currentWorkspaceId) return;

    runInAction(() => {
      this.isSaving = true;
      this.error = null;
      this.validationErrors = {};
    });

    try {
      const response = await aiApi.updateWorkspaceSettings(this.currentWorkspaceId, updates);
      runInAction(() => {
        this.settings = response;
        this.isSaving = false;
      });
    } catch (err) {
      runInAction(() => {
        if (err instanceof Error && err.message.includes('validation')) {
          this.validationErrors = { api_key: 'Invalid API key' };
        }
        this.error = err instanceof Error ? err.message : 'Failed to save settings';
        this.isSaving = false;
      });
      throw err;
    }
  }

  /**
   * Validate API key format (client-side basic check)
   */
  validateKey(provider: 'anthropic' | 'openai', key: string): boolean {
    if (key.length < 10) return false;

    switch (provider) {
      case 'anthropic':
        return key.startsWith('sk-ant-');
      case 'openai':
        return key.startsWith('sk-');
      default:
        return false;
    }
  }

  /**
   * Reset store to initial state
   */
  reset(): void {
    this.settings = null;
    this.isLoading = false;
    this.isSaving = false;
    this.error = null;
    this.validationErrors = {};
    this.currentWorkspaceId = null;
  }
}
