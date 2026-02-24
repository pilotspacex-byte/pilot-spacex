/**
 * ChatView constants tests (T002)
 * Validates skill definitions, categories, and tool utilities.
 */
import { describe, it, expect } from 'vitest';
import {
  FALLBACK_SKILLS,
  SESSION_SKILLS,
  SKILLS,
  SKILL_CATEGORIES,
  isInteractionTool,
  getToolSummary,
  getToolDisplayName,
} from '../constants';

describe('ChatView constants', () => {
  describe('FALLBACK_SKILLS', () => {
    it('should contain daily-standup skill', () => {
      const dailyStandup = FALLBACK_SKILLS.find((s) => s.name === 'daily-standup');
      expect(dailyStandup).toBeDefined();
      expect(dailyStandup!.description).toBe('Generate daily standup summary');
      expect(dailyStandup!.category).toBe('planning');
      expect(dailyStandup!.icon).toBeTruthy();
      expect(dailyStandup!.examples).toBeDefined();
      expect(dailyStandup!.examples!.length).toBeGreaterThan(0);
    });

    it('should have unique skill names', () => {
      const names = FALLBACK_SKILLS.map((s) => s.name);
      expect(new Set(names).size).toBe(names.length);
    });

    it('should have valid categories for all skills', () => {
      const validCategories = SKILL_CATEGORIES.map((c) => c.id);
      for (const skill of FALLBACK_SKILLS) {
        expect(validCategories).toContain(skill.category);
      }
    });
  });

  describe('SKILLS', () => {
    it('should combine SESSION_SKILLS and FALLBACK_SKILLS', () => {
      expect(SKILLS.length).toBe(SESSION_SKILLS.length + FALLBACK_SKILLS.length);
    });
  });

  describe('isInteractionTool', () => {
    it('should detect ask_user tool', () => {
      expect(isInteractionTool('ask_user')).toBe(true);
      expect(isInteractionTool('pilot-interaction__ask_user')).toBe(true);
    });

    it('should not match non-interaction tools', () => {
      expect(isInteractionTool('update_note_block')).toBe(false);
    });
  });

  describe('getToolDisplayName', () => {
    it('should return mapped name for known tools', () => {
      expect(getToolDisplayName('update_note_block')).toBe('Updating Note Block');
    });

    it('should title-case unknown tool names', () => {
      expect(getToolDisplayName('some_new_tool')).toBe('Some New Tool');
    });
  });

  describe('getToolSummary', () => {
    it('should return summary for update_note_block with block_id', () => {
      const result = getToolSummary('update_note_block', { block_id: 'abc12345-rest' });
      expect(result).toBe('Updated block abc12345…');
    });

    it('should return null for unknown tools', () => {
      expect(getToolSummary('unknown_tool', {})).toBeNull();
    });
  });
});
