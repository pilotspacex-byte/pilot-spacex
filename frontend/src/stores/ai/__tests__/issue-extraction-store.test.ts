/**
 * IssueExtractionStore Tests
 *
 * Unit tests for issue extraction store (T162-T164).
 *
 * @see specs/004-mvp-agents-build/tasks/P20-T154-T164.md#T162-T164
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { IssueExtractionStore } from '../IssueExtractionStore';
import { AIErrorCode } from '@/types/ai-errors';
import type { AIStore } from '../AIStore';

// Mock SSE client
vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn(),
}));

// Mock AI API
vi.mock('@/services/api/ai', () => ({
  aiApi: {
    getIssueExtractionUrl: vi.fn((noteId: string) => `/api/v1/ai/notes/${noteId}/extract-issues`),
    resolveApproval: vi.fn(),
  },
}));

describe('IssueExtractionStore', () => {
  let store: IssueExtractionStore;
  let mockAIStore: AIStore;

  beforeEach(() => {
    mockAIStore = {} as AIStore;
    store = new IssueExtractionStore(mockAIStore);
  });

  describe('initialization', () => {
    it('should initialize with empty state', () => {
      expect(store.isLoading).toBe(false);
      expect(store.isCreating).toBe(false);
      expect(store.error).toBeNull();
      expect(store.extractedIssues).toEqual([]);
      expect(store.currentNoteId).toBeNull();
      expect(store.approvalId).toBeNull();
    });
  });

  describe('computed properties', () => {
    it('should calculate recommendedCount correctly', () => {
      store.extractedIssues = [
        {
          title: 'Issue 1',
          description: 'Desc 1',
          confidence_tag: 'recommended',
          confidence_score: 0.9,
        },
        {
          title: 'Issue 2',
          description: 'Desc 2',
          confidence_tag: 'default',
          confidence_score: 0.7,
        },
        {
          title: 'Issue 3',
          description: 'Desc 3',
          confidence_tag: 'recommended',
          confidence_score: 0.85,
        },
      ];

      expect(store.recommendedCount).toBe(2);
    });

    it('should calculate totalCount correctly', () => {
      store.extractedIssues = [
        {
          title: 'Issue 1',
          description: 'Desc 1',
          confidence_tag: 'recommended',
          confidence_score: 0.9,
        },
        {
          title: 'Issue 2',
          description: 'Desc 2',
          confidence_tag: 'default',
          confidence_score: 0.7,
        },
      ];

      expect(store.totalCount).toBe(2);
    });

    it('should calculate hasRecommendedIssues correctly', () => {
      expect(store.hasRecommendedIssues).toBe(false);

      store.extractedIssues = [
        {
          title: 'Issue 1',
          description: 'Desc 1',
          confidence_tag: 'recommended',
          confidence_score: 0.9,
        },
      ];

      expect(store.hasRecommendedIssues).toBe(true);
    });
  });

  describe('clear', () => {
    it('should clear all extracted issues and state', () => {
      store.extractedIssues = [
        {
          title: 'Issue 1',
          description: 'Desc 1',
          confidence_tag: 'recommended',
          confidence_score: 0.9,
        },
      ];
      store.approvalId = 'approval-123';
      store.error = {
        code: AIErrorCode.UNKNOWN,
        message: 'Test error',
        retryable: false,
      };

      store.clear();

      expect(store.extractedIssues).toEqual([]);
      expect(store.approvalId).toBeNull();
      expect(store.error).toBeNull();
    });
  });

  describe('abort', () => {
    it('should set isLoading to false', () => {
      store.isLoading = true;

      store.abort();

      expect(store.isLoading).toBe(false);
    });
  });

  describe('createApprovedIssues', () => {
    it('should throw error if no approval ID', async () => {
      await expect(store.createApprovedIssues([0, 1])).rejects.toThrow('No approval ID available');
    });
  });
});
