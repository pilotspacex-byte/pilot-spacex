/**
 * Issue Extraction Store - MobX store for issue extraction from notes.
 *
 * Manages:
 * - SSE streaming for issue extraction
 * - Extracted issues with confidence tags (DD-048)
 * - Issue selection and approval flow
 * - Creation of approved issues
 *
 * @module stores/ai/IssueExtractionStore
 * @see specs/004-mvp-agents-build/tasks/P20-T154-T164.md#T158
 */

import { makeAutoObservable, runInAction } from 'mobx';
import { SSEClient, type SSEEvent } from '@/lib/sse-client';
import { aiApi } from '@/services/api/ai';
import { parseAIError, type AIError } from '@/types/ai-errors';
import type { AIStore } from './AIStore';

export interface ExtractedIssue {
  title: string;
  description: string;
  confidence_tag: 'recommended' | 'default' | 'current' | 'alternative';
  confidence_score: number;
  labels?: string[];
  priority?: number;
  source_block_ids?: string[];
  rationale?: string;
}

export class IssueExtractionStore {
  isLoading = false;
  isCreating = false;
  error: AIError | null = null;
  extractedIssues: ExtractedIssue[] = [];
  currentNoteId: string | null = null;
  approvalId: string | null = null;

  private client: SSEClient | null = null;

  constructor(_rootStore: AIStore) {
    makeAutoObservable(this);
  }

  /**
   * Extract issues from a note using SSE streaming.
   *
   * @param noteId - Note UUID
   * @param maxIssues - Maximum number of issues to extract (default: 10)
   */
  async extractIssues(noteId: string, maxIssues = 10): Promise<void> {
    // Abort any existing extraction
    this.abort();

    runInAction(() => {
      this.isLoading = true;
      this.error = null;
      this.extractedIssues = [];
      this.currentNoteId = noteId;
      this.approvalId = null;
    });

    this.client = new SSEClient({
      url: aiApi.getIssueExtractionUrl(noteId),
      body: { max_issues: maxIssues },
      onMessage: (event: SSEEvent) => this.handleEvent(event),
      onComplete: () => {
        runInAction(() => {
          this.isLoading = false;
        });
      },
      onError: (err) => {
        runInAction(() => {
          this.isLoading = false;
          this.error = parseAIError(err);
        });
      },
    });

    await this.client.connect();
  }

  /**
   * Handle SSE events from issue extraction stream.
   */
  private handleEvent(event: SSEEvent): void {
    runInAction(() => {
      const data = event.data as Record<string, unknown>;

      switch (event.type) {
        case 'issue':
          // Add extracted issue to list (with type validation)
          if (this.isValidExtractedIssue(data)) {
            this.extractedIssues.push(data as unknown as ExtractedIssue);
          }
          break;

        case 'complete':
          // Store approval ID for later approval
          this.approvalId = data.approval_id as string;
          break;

        case 'error':
          // Handle error event
          this.error = parseAIError(new Error(data.message as string));
          this.isLoading = false;
          break;
      }
    });
  }

  /**
   * Type guard to validate extracted issue shape.
   */
  private isValidExtractedIssue(data: Record<string, unknown>): boolean {
    return (
      typeof data.title === 'string' &&
      typeof data.description === 'string' &&
      typeof data.confidence_tag === 'string' &&
      typeof data.confidence_score === 'number'
    );
  }

  /**
   * Create approved issues from selected indices.
   *
   * @param selectedIndices - Array of issue indices to create
   */
  async createApprovedIssues(selectedIndices: number[]): Promise<void> {
    if (!this.approvalId) {
      throw new Error('No approval ID available');
    }

    runInAction(() => {
      this.isCreating = true;
      this.error = null;
    });

    try {
      await aiApi.resolveApproval(this.approvalId, {
        approved: true,
        selected_issues: selectedIndices,
      });

      runInAction(() => {
        this.isCreating = false;
        this.extractedIssues = [];
        this.approvalId = null;
      });
    } catch (err) {
      runInAction(() => {
        this.isCreating = false;
        this.error = parseAIError(err);
      });
      throw err;
    }
  }

  /**
   * Abort current extraction stream.
   */
  abort(): void {
    this.client?.abort();
    this.client = null;
    this.isLoading = false;
  }

  /**
   * Clear extracted issues and reset state.
   */
  clear(): void {
    this.extractedIssues = [];
    this.approvalId = null;
    this.error = null;
  }

  /**
   * Get count of recommended issues (confidence > 0.8).
   */
  get recommendedCount(): number {
    return this.extractedIssues.filter((issue) => issue.confidence_score > 0.8).length;
  }

  /**
   * Get count of all extracted issues.
   */
  get totalCount(): number {
    return this.extractedIssues.length;
  }

  /**
   * Check if there are any recommended issues.
   */
  get hasRecommendedIssues(): boolean {
    return this.recommendedCount > 0;
  }
}
