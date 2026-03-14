/**
 * AI Settings Store for workspace configuration.
 *
 * Manages workspace-level AI settings with:
 * - Service-based provider config (embedding + llm)
 * - API key management (encrypted server-side)
 * - Feature toggles (ghost text, annotations, etc.)
 * - Validation and error handling
 * - Model listing
 */
import { makeAutoObservable, runInAction, computed } from 'mobx';
import {
  aiApi,
  type WorkspaceAISettings,
  type WorkspaceAISettingsFeatures,
  type WorkspaceAISettingsProvider,
  type WorkspaceAISettingsUpdateResponse,
} from '@/services/api/ai';
import { apiClient } from '@/services/api/client';
import type { AIStore } from './AIStore';

export interface ProviderModelItem {
  provider_config_id: string;
  provider: string;
  model_id: string;
  display_name: string;
  is_selectable: boolean;
}

interface ModelsListResponse {
  items: ProviderModelItem[];
  total: number;
}

export class AISettingsStore {
  settings: WorkspaceAISettings | null = null;
  isLoading = false;
  isSaving = false;
  error: string | null = null;
  validationErrors: Record<string, string> = {};
  currentWorkspaceId: string | null = null;

  availableModels: ProviderModelItem[] = [];
  isLoadingModels = false;

  constructor(_rootStore: AIStore) {
    makeAutoObservable(this, {
      anthropicKeySet: computed,
      embeddingConfigured: computed,
      ghostTextEnabled: computed,
      marginAnnotationsEnabled: computed,
      aiContextEnabled: computed,
    });
  }

  get anthropicKeySet(): boolean {
    return (
      this.settings?.providers?.some(
        (p) => p.provider === 'anthropic' && p.serviceType === 'llm' && p.isConfigured
      ) ?? false
    );
  }

  get embeddingConfigured(): boolean {
    return (
      this.settings?.providers?.some((p) => p.serviceType === 'embedding' && p.isConfigured) ??
      false
    );
  }

  get ghostTextEnabled(): boolean {
    return this.settings?.features?.ghostTextEnabled ?? false;
  }

  get marginAnnotationsEnabled(): boolean {
    return this.settings?.features?.marginAnnotationsEnabled ?? false;
  }

  get aiContextEnabled(): boolean {
    return this.settings?.features?.aiContextEnabled ?? false;
  }

  getProviderStatus(
    provider: string,
    serviceType: 'embedding' | 'llm'
  ): WorkspaceAISettingsProvider | undefined {
    return this.settings?.providers?.find(
      (p) => p.provider === provider && p.serviceType === serviceType
    );
  }

  /** Get all providers for a given service type. */
  getProvidersByService(serviceType: 'embedding' | 'llm'): WorkspaceAISettingsProvider[] {
    return this.settings?.providers?.filter((p) => p.serviceType === serviceType) ?? [];
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

  async saveSettings(data: {
    api_keys?: Array<{
      provider: string;
      service_type: 'embedding' | 'llm';
      api_key?: string;
      base_url?: string;
      model_name?: string;
    }>;
    features?: Partial<WorkspaceAISettingsFeatures>;
  }): Promise<void> {
    if (!this.currentWorkspaceId) return;

    runInAction(() => {
      this.isSaving = true;
      this.error = null;
      this.validationErrors = {};
    });

    try {
      const result: WorkspaceAISettingsUpdateResponse = await aiApi.updateWorkspaceSettings(
        this.currentWorkspaceId,
        data
      );

      if (!result.success && result.validationResults.length > 0) {
        const failed = result.validationResults.filter((r) => !r.isValid);
        const messages = failed.map((r) => `${r.provider}: ${r.errorMessage ?? 'invalid key'}`);
        const err = new Error(messages.join('; '));
        runInAction(() => {
          this.validationErrors = Object.fromEntries(
            failed.map((r) => [r.provider, r.errorMessage ?? 'API key validation failed'])
          );
          this.error = err.message;
          this.isSaving = false;
        });
        throw err;
      }

      const refreshed = await aiApi.getWorkspaceSettings(this.currentWorkspaceId);
      runInAction(() => {
        this.settings = refreshed;
        this.isSaving = false;
      });
    } catch (err) {
      runInAction(() => {
        if (!(err instanceof Error && this.error)) {
          this.error = err instanceof Error ? err.message : 'Failed to save settings';
        }
        this.isSaving = false;
      });
      throw err;
    }
  }

  async loadModels(workspaceId: string): Promise<void> {
    runInAction(() => {
      this.isLoadingModels = true;
    });

    try {
      const response = await apiClient.get<ModelsListResponse>('/ai/configurations/models', {
        params: { workspace_id: workspaceId },
      });
      runInAction(() => {
        this.availableModels = response.items;
        this.isLoadingModels = false;
      });
    } catch (err) {
      console.error('Failed to load AI models:', err);
      runInAction(() => {
        this.availableModels = [];
        this.isLoadingModels = false;
      });
    }
  }

  validateKey(provider: string, key: string): boolean {
    if (provider === 'ollama') return true; // No API key required
    if (key.length < 10) return false;

    switch (provider) {
      case 'anthropic':
        return key.startsWith('sk-ant-');
      case 'google':
        return key.startsWith('AIza');
      default:
        return true;
    }
  }

  reset(): void {
    this.settings = null;
    this.isLoading = false;
    this.isSaving = false;
    this.error = null;
    this.validationErrors = {};
    this.currentWorkspaceId = null;
    this.availableModels = [];
    this.isLoadingModels = false;
  }
}
