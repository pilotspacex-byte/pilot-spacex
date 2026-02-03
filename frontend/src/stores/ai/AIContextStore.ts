/**
 * AI Context Store with session management.
 *
 * Manages AI-generated context for issues with:
 * - Multi-phase progress tracking
 * - SSE streaming for real-time updates
 * - Result caching
 * - Structured context sections (summary, related issues, docs, tasks, prompts)
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

export interface ContextStats {
  relatedCount: number;
  docsCount: number;
  filesCount: number;
  tasksCount: number;
}

export interface ContextSummary {
  issueIdentifier: string;
  title: string;
  summaryText: string;
  stats: ContextStats;
}

export interface ContextRelatedIssue {
  relationType: 'blocks' | 'relates' | 'blocked_by';
  issueId: string;
  identifier: string;
  title: string;
  summary: string;
  status: string;
  stateGroup: string;
}

export interface ContextRelatedDoc {
  docType: string;
  title: string;
  summary?: string;
  url?: string;
}

export interface ContextTask {
  id: number;
  title: string;
  estimate: string;
  dependencies: number[];
  completed: boolean;
}

export interface ContextPrompt {
  taskId: number;
  title: string;
  content: string;
}

export type ContextSectionKey = 'summary' | 'related_issues' | 'related_docs' | 'tasks' | 'prompts';

export interface AIContextResult {
  /** @deprecated Legacy field — not populated by structured SSE path */
  phases: AIContextPhase[];
  /** @deprecated Legacy field — not populated by structured SSE path */
  claudeCodePrompt: string;
  /** @deprecated Legacy field — not populated by structured SSE path */
  relatedDocs_legacy: string[];
  /** @deprecated Legacy field — not populated by structured SSE path */
  relatedCode: string[];
  /** @deprecated Legacy field — not populated by structured SSE path */
  similarIssues: string[];
  summary: ContextSummary | null;
  relatedIssues: ContextRelatedIssue[];
  relatedDocs: ContextRelatedDoc[];
  tasks: ContextTask[];
  prompts: ContextPrompt[];
}

export class AIContextStore {
  isLoading = false;
  isEnabled = true;
  error: string | null = null;
  currentIssueId: string | null = null;
  phases: AIContextPhase[] = [];
  result: AIContextResult | null = null;
  sectionErrors: Map<string, string> = new Map();

  private client: SSEClient | null = null;
  private cache = new Map<string, AIContextResult>();

  constructor(private rootStore: AIStore) {
    makeAutoObservable(this);
  }

  get hasStructuredData(): boolean {
    return this.result?.summary !== null && this.result?.summary !== undefined;
  }

  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
  }

  async generateContext(issueId: string): Promise<void> {
    if (!this.isEnabled || !this.rootStore.isGloballyEnabled) return;

    // Always abort any in-flight stream before checking cache to prevent
    // events from a previous issue corrupting the cached result.
    this.abort();

    // Check cache — must clear stale error/sectionErrors from previous issue
    const cached = this.cache.get(issueId);
    if (cached) {
      runInAction(() => {
        this.currentIssueId = issueId;
        this.error = null;
        this.sectionErrors = new Map();
        this.result = cached;
      });
      return;
    }

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
      this.sectionErrors = new Map();
    });

    // Capture issueId in closure to guard against stale stream events
    // arriving after the user navigates to a different issue.
    const streamIssueId = issueId;

    this.client = new SSEClient({
      url: aiApi.getAIContextUrl(issueId),
      method: 'POST',
      retryable: true,
      onMessage: (event: SSEEvent) => {
        if (this.currentIssueId !== streamIssueId) return;
        this.handleEvent(event);
      },
      onComplete: () => {
        if (this.currentIssueId !== streamIssueId) return;
        runInAction(() => {
          this.isLoading = false;
        });
      },
      onError: (err) => {
        if (this.currentIssueId !== streamIssueId) return;
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
        case 'context_summary':
          this.result = {
            ...(this.result ?? this.createEmptyResult()),
            summary: data as unknown as ContextSummary,
          };
          break;
        case 'related_issues':
          this.result = {
            ...(this.result ?? this.createEmptyResult()),
            relatedIssues: (data as { items: ContextRelatedIssue[] }).items,
          };
          break;
        case 'related_docs':
          this.result = {
            ...(this.result ?? this.createEmptyResult()),
            relatedDocs: (data as { items: ContextRelatedDoc[] }).items,
          };
          break;
        case 'ai_tasks':
          this.result = {
            ...(this.result ?? this.createEmptyResult()),
            tasks: (data as { items: ContextTask[] }).items,
          };
          break;
        case 'ai_prompts':
          this.result = {
            ...(this.result ?? this.createEmptyResult()),
            prompts: (data as { items: ContextPrompt[] }).items,
          };
          break;
        case 'context_error':
          this.sectionErrors.set(
            (data as { section: string; message: string }).section,
            (data as { section: string; message: string }).message
          );
          break;
        case 'error':
          this.error = (data as { message: string }).message ?? 'Unknown error';
          this.isLoading = false;
          break;
        case 'context_complete':
          this.isLoading = false;
          if (!this.result) {
            this.result = this.createEmptyResult();
          }
          if (this.currentIssueId) {
            this.cache.set(this.currentIssueId, this.result);
          }
          break;
      }
    });
  }

  private createEmptyResult(): AIContextResult {
    return {
      summary: null,
      relatedIssues: [],
      relatedDocs: [],
      tasks: [],
      prompts: [],
      phases: [],
      claudeCodePrompt: '',
      relatedDocs_legacy: [],
      relatedCode: [],
      similarIssues: [],
    };
  }

  abort(): void {
    this.client?.abort();
    this.client = null;
    runInAction(() => {
      this.isLoading = false;
      this.error = null;
      this.sectionErrors = new Map();
    });
  }

  clearCache(issueId?: string): void {
    if (issueId) {
      this.cache.delete(issueId);
    } else {
      this.cache.clear();
    }
  }
}
