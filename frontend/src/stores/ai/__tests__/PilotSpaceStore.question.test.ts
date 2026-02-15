/**
 * Unit tests for PilotSpaceStore question state management.
 *
 * Tests handleQuestionRequest, clearPendingQuestion, and isWaitingForUser computed.
 *
 * @module stores/ai/__tests__/PilotSpaceStore.question.test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock supabase before any store imports
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token' } },
      }),
    },
  },
}));

vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn().mockImplementation(() => ({
    connect: vi.fn().mockResolvedValue(undefined),
    abort: vi.fn(),
  })),
}));

import { PilotSpaceStore } from '../PilotSpaceStore';
import type { AIStore } from '../AIStore';
import type { QuestionRequestEvent } from '../types/events';

describe('PilotSpaceStore — question state management', () => {
  let store: PilotSpaceStore;

  beforeEach(() => {
    const mockAIStore = {} as AIStore;
    store = new PilotSpaceStore(mockAIStore);
  });

  describe('handleQuestionRequest', () => {
    it('should set pendingQuestion from event data', () => {
      const event: QuestionRequestEvent = {
        type: 'question_request',
        data: {
          messageId: 'msg-1',
          questionId: 'q-1',
          toolCallId: 'tc-1',
          questions: [
            {
              question: 'Which priority?',
              options: [{ label: 'High' }, { label: 'Medium' }, { label: 'Low' }],
              multiSelect: false,
            },
          ],
        },
      };

      store.handleQuestionRequest(event);

      expect(store.pendingQuestion).not.toBeNull();
      expect(store.pendingQuestion?.questionId).toBe('q-1');
      expect(store.pendingQuestion?.questions).toHaveLength(1);
      expect(store.pendingQuestion?.questions[0]?.question).toBe('Which priority?');
    });

    it('should pause streaming state when question arrives', () => {
      store.updateStreamingState({ isStreaming: true, streamContent: 'partial' });

      const event: QuestionRequestEvent = {
        type: 'question_request',
        data: {
          messageId: 'msg-1',
          questionId: 'q-1',
          toolCallId: 'tc-1',
          questions: [{ question: 'Confirm?', options: [], multiSelect: false }],
        },
      };

      store.handleQuestionRequest(event);

      // Stream stays active with waiting_for_user phase (WARNING-2 fix)
      expect(store.streamingState.isStreaming).toBe(true);
      expect(store.streamingState.phase).toBe('waiting_for_user');
    });

    it('should replace existing pending question with new one', () => {
      store.pendingQuestion = {
        questionId: 'old-q',
        questions: [{ question: 'Old?', options: [], multiSelect: false }],
      };

      const event: QuestionRequestEvent = {
        type: 'question_request',
        data: {
          messageId: 'msg-2',
          questionId: 'new-q',
          toolCallId: 'tc-2',
          questions: [{ question: 'New?', options: [], multiSelect: false }],
        },
      };

      store.handleQuestionRequest(event);

      expect(store.pendingQuestion?.questionId).toBe('new-q');
    });
  });

  describe('clearPendingQuestion', () => {
    it('should set pendingQuestion to null', () => {
      store.pendingQuestion = {
        questionId: 'q-1',
        questions: [{ question: 'Test?', options: [], multiSelect: false }],
      };

      store.clearPendingQuestion();

      expect(store.pendingQuestion).toBeNull();
    });

    it('should be safe to call when pendingQuestion is already null', () => {
      store.pendingQuestion = null;
      expect(() => store.clearPendingQuestion()).not.toThrow();
      expect(store.pendingQuestion).toBeNull();
    });
  });

  describe('isWaitingForUser computed', () => {
    it('should return false when no pending question and no approvals', () => {
      expect(store.isWaitingForUser).toBe(false);
    });

    it('should return true when pendingQuestion is set', () => {
      store.pendingQuestion = {
        questionId: 'q-1',
        questions: [{ question: 'Test?', options: [], multiSelect: false }],
      };

      expect(store.isWaitingForUser).toBe(true);
    });

    it('should return true when there are unresolved approvals', () => {
      store.addApproval({
        requestId: 'req-1',
        actionType: 'create_issue',
        description: 'Test',
        affectedEntities: [],
        urgency: 'low',
        expiresAt: new Date(),
        createdAt: new Date(),
      });

      expect(store.isWaitingForUser).toBe(true);
    });

    it('should return true when both question and approval are pending', () => {
      store.pendingQuestion = {
        questionId: 'q-1',
        questions: [{ question: 'Test?', options: [], multiSelect: false }],
      };
      store.addApproval({
        requestId: 'req-1',
        actionType: 'delete_issue',
        description: 'Delete',
        affectedEntities: [],
        urgency: 'high',
        expiresAt: new Date(),
        createdAt: new Date(),
      });

      expect(store.isWaitingForUser).toBe(true);
    });

    it('should return false after clearing question and approvals', () => {
      store.pendingQuestion = {
        questionId: 'q-1',
        questions: [{ question: 'Test?', options: [], multiSelect: false }],
      };

      store.clearPendingQuestion();
      expect(store.isWaitingForUser).toBe(false);
    });
  });
});
