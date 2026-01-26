/**
 * AI Context Store with session management.
 *
 * Manages AI-generated context for issues with:
 * - Multi-phase progress tracking
 * - SSE streaming for real-time updates
 * - Result caching
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { SSEClient, type SSEEvent } from '@/lib/sse-client';
import { aiApi } from '@/services/api/ai';
import type { AIStore } from './AIStore';

export interface AIContextPhase {
  name: string;
  status: 'pending' | 'in_progress' | 'complete';
  content?: string;
}

export interface AIContextResult {
  phases: AIContextPhase[];
  claudeCodePrompt: string;
  relatedDocs: string[];
  relatedCode: string[];
  similarIssues: string[];
}

export class AIContextStore {
  isLoading = false;
  isEnabled = true;
  error: string | null = null;
  currentIssueId: string | null = null;
  phases: AIContextPhase[] = [];
  result: AIContextResult | null = null;

  private client: SSEClient | null = null;
  private cache = new Map<string, AIContextResult>();

  constructor(private rootStore: AIStore) {
    makeAutoObservable(this);
  }

  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
  }

  async generateContext(issueId: string): Promise<void> {
    if (!this.isEnabled || !this.rootStore.isGloballyEnabled) return;

    // Check cache
    const cached = this.cache.get(issueId);
    if (cached) {
      this.result = cached;
      return;
    }

    this.abort();

    runInAction(() => {
      this.isLoading = true;
      this.error = null;
      this.currentIssueId = issueId;
      this.phases = [
        { name: 'Analyzing issue', status: 'pending' },
        { name: 'Finding related docs', status: 'pending' },
        { name: 'Searching codebase', status: 'pending' },
        { name: 'Finding similar issues', status: 'pending' },
        { name: 'Generating implementation guide', status: 'pending' },
      ];
      this.result = null;
    });

    this.client = new SSEClient({
      url: aiApi.getAIContextUrl(issueId),
      onMessage: (event: SSEEvent) => this.handleEvent(event),
      onComplete: () => {
        runInAction(() => {
          this.isLoading = false;
          if (this.result) {
            this.cache.set(issueId, this.result);
          }
        });
      },
      onError: (err) => {
        runInAction(() => {
          this.isLoading = false;
          this.error = err.message;
        });
      },
    });

    await this.client.connect();
  }

  private handleEvent(event: SSEEvent): void {
    runInAction(() => {
      const data = event.data as Record<string, unknown>;

      switch (event.type) {
        case 'phase': {
          const phaseIndex = this.phases.findIndex((p) => p.name === data.name);
          if (phaseIndex >= 0) {
            const phase = this.phases[phaseIndex];
            if (phase) {
              phase.status = data.status as 'pending' | 'in_progress' | 'complete';
              if (data.content) {
                phase.content = data.content as string;
              }
            }
          }
          break;
        }
        case 'complete':
          this.result = data as unknown as AIContextResult;
          break;
      }
    });
  }

  abort(): void {
    this.client?.abort();
    this.client = null;
    this.isLoading = false;
  }

  clearCache(issueId?: string): void {
    if (issueId) {
      this.cache.delete(issueId);
    } else {
      this.cache.clear();
    }
  }
}
