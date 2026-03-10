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
import { PRReviewStore } from './PRReviewStore';
import { ConversationStore } from './ConversationStore';
import { CostStore } from './CostStore';
import { MarginAnnotationStore } from './MarginAnnotationStore';
import { PilotSpaceStore } from './PilotSpaceStore';
import { MCPServersStore } from './MCPServersStore';
import { PluginsStore } from './PluginsStore';

export class AIStore {
  ghostText: GhostTextStore;
  aiContext: AIContextStore;
  approval: ApprovalStore;
  settings: AISettingsStore;
  prReview: PRReviewStore;
  conversation: ConversationStore;
  cost: CostStore;
  marginAnnotation: MarginAnnotationStore;
  pilotSpace: PilotSpaceStore;
  mcpServers: MCPServersStore;
  plugins: PluginsStore;

  isGloballyEnabled = true;
  globalError: string | null = null;

  constructor() {
    makeAutoObservable(this);

    this.ghostText = new GhostTextStore(this);
    this.aiContext = new AIContextStore(this);
    this.approval = new ApprovalStore(this);
    this.settings = new AISettingsStore(this);
    this.prReview = new PRReviewStore(this);
    this.conversation = new ConversationStore(this);
    this.cost = new CostStore(this);
    this.marginAnnotation = new MarginAnnotationStore(this);
    this.pilotSpace = new PilotSpaceStore(this);
    this.mcpServers = new MCPServersStore();
    this.plugins = new PluginsStore();
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
    this.prReview.abort();
    this.conversation.abort();
    this.marginAnnotation.abort();
    this.pilotSpace.abort();
  }

  async loadWorkspaceSettings(workspaceId: string): Promise<void> {
    await this.settings.loadSettings(workspaceId);

    runInAction(() => {
      // Update feature availability based on settings
      this.ghostText.setEnabled(this.settings.ghostTextEnabled);
      this.aiContext.setEnabled(this.settings.aiContextEnabled);
      this.marginAnnotation.setEnabled(this.settings.marginAnnotationsEnabled ?? true);
    });
  }

  reset(): void {
    this.ghostText.abort();
    this.aiContext.abort();
    this.prReview.abort();
    this.marginAnnotation.abort();
    this.conversation.clearSession();
    this.pilotSpace.reset();
    this.approval.reset();
    this.settings.reset();
    this.cost.reset();
    this.mcpServers.reset();
    this.plugins.reset();
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
