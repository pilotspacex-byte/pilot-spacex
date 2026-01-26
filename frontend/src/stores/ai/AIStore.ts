/**
 * AI Store - Root store for AI agent state management.
 *
 * Aggregates all AI-related stores and provides:
 * - Centralized initialization
 * - Cross-store coordination
 * - Global AI state (enabled, error state)
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { GhostTextStore } from './GhostTextStore';
import { AIContextStore } from './AIContextStore';
import { ApprovalStore } from './ApprovalStore';
import { AISettingsStore } from './AISettingsStore';

export class AIStore {
  ghostText: GhostTextStore;
  aiContext: AIContextStore;
  approval: ApprovalStore;
  settings: AISettingsStore;

  isGloballyEnabled = true;
  globalError: string | null = null;

  constructor() {
    makeAutoObservable(this);

    this.ghostText = new GhostTextStore(this);
    this.aiContext = new AIContextStore(this);
    this.approval = new ApprovalStore(this);
    this.settings = new AISettingsStore(this);
  }

  setGloballyEnabled(enabled: boolean): void {
    this.isGloballyEnabled = enabled;
  }

  setGlobalError(error: string | null): void {
    this.globalError = error;
  }

  abortAllStreams(): void {
    this.ghostText.abort();
    this.aiContext.abort();
  }

  async loadWorkspaceSettings(workspaceId: string): Promise<void> {
    await this.settings.loadSettings(workspaceId);

    runInAction(() => {
      // Update feature availability based on settings
      this.ghostText.setEnabled(this.settings.ghostTextEnabled);
      this.aiContext.setEnabled(this.settings.aiContextEnabled);
    });
  }

  reset(): void {
    this.ghostText.abort();
    this.aiContext.abort();
    this.approval.reset();
    this.settings.reset();
    this.globalError = null;
  }
}

// Singleton instance
let aiStoreInstance: AIStore | null = null;

export function getAIStore(): AIStore {
  if (!aiStoreInstance) {
    aiStoreInstance = new AIStore();
  }
  return aiStoreInstance;
}

export const aiStore = getAIStore();
