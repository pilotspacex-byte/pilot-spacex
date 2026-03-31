/**
 * Behavioral tests for PilotSpaceStore skill event handlers.
 *
 * Tests the iterative refine loop:
 * - handleSkillPreview appends a system message with structuredResult
 * - handleTestResult appends a system message with structuredResult
 * - Multiple calls simulate the create → update → test → refine loop
 *
 * Phase 64-04
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock supabase before any store imports
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}));

vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn(),
}));

import { PilotSpaceStore } from '../PilotSpaceStore';
import type { AIStore } from '../AIStore';
import type { SkillPreviewEvent, TestResultEvent } from '../types/events';

describe('PilotSpaceStore — skill event handlers', () => {
  let store: PilotSpaceStore;

  beforeEach(() => {
    const mockRootStore = {} as AIStore;
    store = new PilotSpaceStore(mockRootStore);
    store.setWorkspaceId('workspace-123');
  });

  // ─── handleSkillPreview ──────────────────────────────────────────────────

  describe('handleSkillPreview', () => {
    it('appends a system message with skillPreview structuredResult', () => {
      const event: SkillPreviewEvent = {
        type: 'skill_preview',
        data: {
          skillName: 'review-pr',
          frontmatter: { description: 'Reviews pull requests' },
          content: '# Review PR\nYou are an expert reviewer.',
          isUpdate: false,
        },
      };

      store.handleSkillPreview(event);

      expect(store.messages).toHaveLength(1);
      const msg = store.messages[0]!;
      expect(msg.role).toBe('system');
      expect(msg.structuredResult).toBeDefined();
      expect(msg.structuredResult!.schemaType).toBe('skill_preview');
      expect(msg.structuredResult!.data).toMatchObject({
        skillName: 'review-pr',
        isUpdate: false,
      });
    });

    it('sets skillPreview observable to event data', () => {
      const event: SkillPreviewEvent = {
        type: 'skill_preview',
        data: {
          skillName: 'standup-helper',
          frontmatter: { description: 'Generates standups' },
          content: '# Standup\nSummarize daily work.',
          isUpdate: false,
        },
      };

      store.handleSkillPreview(event);

      expect(store.skillPreview).toEqual(event.data);
    });

    it('propagates isUpdate=true to the appended message structuredResult', () => {
      const event: SkillPreviewEvent = {
        type: 'skill_preview',
        data: {
          skillName: 'review-pr',
          frontmatter: { description: 'Reviews pull requests with rate limiting' },
          content: '# Review PR v2\nAlso checks rate limiting.',
          isUpdate: true,
        },
      };

      store.handleSkillPreview(event);

      const msg = store.messages[0]!;
      expect(msg.structuredResult!.data).toMatchObject({ isUpdate: true });
    });

    it('each call appends a separate message (simulates create then refine loop)', () => {
      const createEvent: SkillPreviewEvent = {
        type: 'skill_preview',
        data: {
          skillName: 'review-pr',
          frontmatter: { description: 'v1' },
          content: '# v1',
          isUpdate: false,
        },
      };
      const updateEvent: SkillPreviewEvent = {
        type: 'skill_preview',
        data: {
          skillName: 'review-pr',
          frontmatter: { description: 'v2 — adds rate limiting check' },
          content: '# v2',
          isUpdate: true,
        },
      };

      store.handleSkillPreview(createEvent);
      store.handleSkillPreview(updateEvent);

      expect(store.messages).toHaveLength(2);
      expect(store.messages[0]!.structuredResult!.data).toMatchObject({ isUpdate: false });
      expect(store.messages[1]!.structuredResult!.data).toMatchObject({ isUpdate: true });
    });

    it('each message has a unique id', () => {
      const event: SkillPreviewEvent = {
        type: 'skill_preview',
        data: {
          skillName: 'test-skill',
          frontmatter: {},
          content: '# Test',
          isUpdate: false,
        },
      };

      store.handleSkillPreview(event);
      store.handleSkillPreview({ ...event, data: { ...event.data, isUpdate: true } });

      const [msg1, msg2] = store.messages;
      expect(msg1!.id).not.toBe(msg2!.id);
    });
  });

  // ─── handleTestResult ────────────────────────────────────────────────────

  describe('handleTestResult', () => {
    it('appends a system message with test_result structuredResult', () => {
      const event: TestResultEvent = {
        type: 'test_result',
        data: {
          skillName: 'review-pr',
          score: 7,
          passed: ['Catches obvious bugs', 'Clear feedback'],
          failed: ['Missed security issue'],
          suggestions: ['Add OWASP checks'],
          sampleOutput: 'The PR looks good overall, but...',
        },
      };

      store.handleTestResult(event);

      expect(store.messages).toHaveLength(1);
      const msg = store.messages[0]!;
      expect(msg.role).toBe('system');
      expect(msg.structuredResult!.schemaType).toBe('test_result');
      expect(msg.structuredResult!.data).toMatchObject({
        skillName: 'review-pr',
        score: 7,
      });
    });

    it('sets skillTestResult observable to event data', () => {
      const event: TestResultEvent = {
        type: 'test_result',
        data: {
          skillName: 'standup-helper',
          score: 9,
          passed: ['Concise', 'Actionable'],
          failed: [],
          suggestions: [],
          sampleOutput: 'Yesterday: finished auth. Today: PR review.',
        },
      };

      store.handleTestResult(event);

      expect(store.skillTestResult).toEqual(event.data);
    });

    it('passes arrays for passed, failed, suggestions', () => {
      const event: TestResultEvent = {
        type: 'test_result',
        data: {
          skillName: 'review-pr',
          score: 5,
          passed: ['A', 'B'],
          failed: ['C'],
          suggestions: ['D', 'E'],
          sampleOutput: 'sample',
        },
      };

      store.handleTestResult(event);

      const data = store.messages[0]!.structuredResult!.data;
      expect(data['passed']).toEqual(['A', 'B']);
      expect(data['failed']).toEqual(['C']);
      expect(data['suggestions']).toEqual(['D', 'E']);
    });
  });

  // ─── Full refine loop simulation ─────────────────────────────────────────

  describe('iterative refine loop (integration)', () => {
    it('simulates create → update → test flow: 3 messages in order', () => {
      // Step 1: User asks to create a skill → agent calls create_skill
      store.handleSkillPreview({
        type: 'skill_preview',
        data: {
          skillName: 'rate-limiter-checker',
          frontmatter: { description: 'Check rate limits' },
          content: '# Rate Limiter v1',
          isUpdate: false,
        },
      });

      // Step 2: User refines → agent calls update_skill
      store.handleSkillPreview({
        type: 'skill_preview',
        data: {
          skillName: 'rate-limiter-checker',
          frontmatter: { description: 'Check rate limits and auth' },
          content: '# Rate Limiter v2 + Auth',
          isUpdate: true,
        },
      });

      // Step 3: User tests → agent calls test_skill
      store.handleTestResult({
        type: 'test_result',
        data: {
          skillName: 'rate-limiter-checker',
          score: 8,
          passed: ['Detects missing rate limit', 'Flags auth issues'],
          failed: [],
          suggestions: ['Also check JWT expiry'],
          sampleOutput: 'Rate limiting: ✓ Auth: ✓',
        },
      });

      expect(store.messages).toHaveLength(3);
      expect(store.messages[0]!.structuredResult!.schemaType).toBe('skill_preview');
      expect(store.messages[1]!.structuredResult!.schemaType).toBe('skill_preview');
      expect(store.messages[2]!.structuredResult!.schemaType).toBe('test_result');

      // skillPreview tracks the LATEST skill state
      expect(store.skillPreview?.isUpdate).toBe(true);
      expect(store.skillTestResult?.score).toBe(8);
    });

    it('handleSkillSaved clears skillPreview and skillTestResult', () => {
      store.handleSkillPreview({
        type: 'skill_preview',
        data: {
          skillName: 'my-skill',
          frontmatter: {},
          content: '# My Skill',
          isUpdate: false,
        },
      });
      store.handleTestResult({
        type: 'test_result',
        data: {
          skillName: 'my-skill',
          score: 9,
          passed: ['All good'],
          failed: [],
          suggestions: [],
          sampleOutput: 'output',
        },
      });

      expect(store.skillPreview).not.toBeNull();
      expect(store.skillTestResult).not.toBeNull();

      store.handleSkillSaved({
        type: 'skill_saved',
        data: { skillName: 'my-skill' },
      });

      expect(store.skillPreview).toBeNull();
      expect(store.skillTestResult).toBeNull();
    });
  });
});
