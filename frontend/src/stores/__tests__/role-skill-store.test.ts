/**
 * Unit tests for RoleSkillStore.
 *
 * T018: Tests for role-skill MobX UI state management.
 * Source: FR-001, FR-002, FR-018, US1
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { RoleSkillStore } from '../RoleSkillStore';

describe('RoleSkillStore', () => {
  let store: RoleSkillStore;

  beforeEach(() => {
    store = new RoleSkillStore();
  });

  describe('initial state', () => {
    it('should have empty selectedRoles', () => {
      expect(store.selectedRoles).toEqual([]);
    });

    it('should not be generating', () => {
      expect(store.isGenerating).toBe(false);
    });

    it('should have null generationStep', () => {
      expect(store.generationStep).toBeNull();
    });

    it('should have empty experienceDescription', () => {
      expect(store.experienceDescription).toBe('');
    });

    it('should have null skillPreview', () => {
      expect(store.skillPreview).toBeNull();
    });

    it('should have null editingSkillId', () => {
      expect(store.editingSkillId).toBeNull();
    });

    it('should have empty customRoleDescription', () => {
      expect(store.customRoleDescription).toBe('');
    });
  });

  describe('computed: canContinue', () => {
    it('should return false when no roles selected', () => {
      expect(store.canContinue).toBe(false);
    });

    it('should return true when at least one role selected', () => {
      store.toggleRole('developer');
      expect(store.canContinue).toBe(true);
    });
  });

  describe('computed: selectedCount', () => {
    it('should return 0 when no roles selected', () => {
      expect(store.selectedCount).toBe(0);
    });

    it('should return correct count', () => {
      store.toggleRole('developer');
      store.toggleRole('tester');
      expect(store.selectedCount).toBe(2);
    });
  });

  describe('computed: remainingSlots', () => {
    it('should return 3 when no roles selected', () => {
      expect(store.remainingSlots).toBe(3);
    });

    it('should decrease as roles are selected', () => {
      store.toggleRole('developer');
      expect(store.remainingSlots).toBe(2);

      store.toggleRole('tester');
      expect(store.remainingSlots).toBe(1);

      store.toggleRole('architect');
      expect(store.remainingSlots).toBe(0);
    });
  });

  describe('computed: primaryRole', () => {
    it('should return null when no roles selected', () => {
      expect(store.primaryRole).toBeNull();
    });

    it('should return the first selected role', () => {
      store.toggleRole('tester');
      store.toggleRole('developer');
      expect(store.primaryRole).toBe('tester');
    });

    it('should update when first role is deselected', () => {
      store.toggleRole('tester');
      store.toggleRole('developer');
      store.toggleRole('tester'); // deselect tester
      expect(store.primaryRole).toBe('developer');
    });
  });

  describe('toggleRole', () => {
    it('should add a role when not selected', () => {
      store.toggleRole('developer');
      expect(store.selectedRoles).toEqual(['developer']);
    });

    it('should remove a role when already selected', () => {
      store.toggleRole('developer');
      store.toggleRole('developer');
      expect(store.selectedRoles).toEqual([]);
    });

    it('should allow selecting up to 3 roles', () => {
      store.toggleRole('developer');
      store.toggleRole('tester');
      store.toggleRole('architect');
      expect(store.selectedRoles).toEqual(['developer', 'tester', 'architect']);
    });

    it('should NOT allow selecting more than 3 roles', () => {
      store.toggleRole('developer');
      store.toggleRole('tester');
      store.toggleRole('architect');
      store.toggleRole('devops'); // 4th should be ignored
      expect(store.selectedRoles).toEqual(['developer', 'tester', 'architect']);
      expect(store.selectedCount).toBe(3);
    });

    it('should allow deselecting when at max', () => {
      store.toggleRole('developer');
      store.toggleRole('tester');
      store.toggleRole('architect');
      store.toggleRole('architect'); // deselect
      expect(store.selectedRoles).toEqual(['developer', 'tester']);
    });
  });

  describe('clearSelectedRoles', () => {
    it('should clear all selections', () => {
      store.toggleRole('developer');
      store.toggleRole('tester');
      store.clearSelectedRoles();
      expect(store.selectedRoles).toEqual([]);
      expect(store.selectedCount).toBe(0);
    });
  });

  describe('setGenerationStep', () => {
    it('should set the generation step', () => {
      store.setGenerationStep('select');
      expect(store.generationStep).toBe('select');

      store.setGenerationStep('describe');
      expect(store.generationStep).toBe('describe');

      store.setGenerationStep('generating');
      expect(store.generationStep).toBe('generating');

      store.setGenerationStep('preview');
      expect(store.generationStep).toBe('preview');
    });

    it('should set to null', () => {
      store.setGenerationStep('select');
      store.setGenerationStep(null);
      expect(store.generationStep).toBeNull();
    });
  });

  describe('setExperienceDescription', () => {
    it('should update the description', () => {
      store.setExperienceDescription('Full-stack engineer with 5 years');
      expect(store.experienceDescription).toBe('Full-stack engineer with 5 years');
    });
  });

  describe('skillPreview', () => {
    it('should set the preview', () => {
      const preview = {
        content: '# Developer\n## Focus Areas',
        suggestedName: 'Senior Full-Stack Developer',
        wordCount: 150,
      };

      store.setSkillPreview(preview);
      expect(store.skillPreview).toEqual(preview);
    });

    it('should clear the preview', () => {
      store.setSkillPreview({
        content: '# Test',
        suggestedName: 'Test',
        wordCount: 1,
      });
      store.clearSkillPreview();
      expect(store.skillPreview).toBeNull();
    });
  });

  describe('setIsGenerating', () => {
    it('should set generating state', () => {
      store.setIsGenerating(true);
      expect(store.isGenerating).toBe(true);

      store.setIsGenerating(false);
      expect(store.isGenerating).toBe(false);
    });
  });

  describe('editingSkillId', () => {
    it('should set the editing skill ID', () => {
      store.setEditingSkillId('skill-123');
      expect(store.editingSkillId).toBe('skill-123');
    });

    it('should clear the editing skill ID', () => {
      store.setEditingSkillId('skill-123');
      store.clearEditingSkillId();
      expect(store.editingSkillId).toBeNull();
    });
  });

  describe('setCustomRoleDescription', () => {
    it('should update custom role description', () => {
      store.setCustomRoleDescription('Security specialist');
      expect(store.customRoleDescription).toBe('Security specialist');
    });
  });

  describe('reset', () => {
    it('should reset all state to initial values', () => {
      // Modify all state
      store.toggleRole('developer');
      store.toggleRole('tester');
      store.setIsGenerating(true);
      store.setGenerationStep('preview');
      store.setExperienceDescription('Some description');
      store.setSkillPreview({
        content: '# Skill',
        suggestedName: 'Name',
        wordCount: 100,
      });
      store.setEditingSkillId('skill-1');
      store.setCustomRoleDescription('Custom role');

      // Reset
      store.reset();

      // Verify all back to defaults
      expect(store.selectedRoles).toEqual([]);
      expect(store.isGenerating).toBe(false);
      expect(store.generationStep).toBeNull();
      expect(store.experienceDescription).toBe('');
      expect(store.skillPreview).toBeNull();
      expect(store.editingSkillId).toBeNull();
      expect(store.customRoleDescription).toBe('');
      expect(store.canContinue).toBe(false);
      expect(store.selectedCount).toBe(0);
      expect(store.remainingSlots).toBe(3);
      expect(store.primaryRole).toBeNull();
    });
  });
});
