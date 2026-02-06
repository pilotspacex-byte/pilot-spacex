'use client';

import { makeAutoObservable, computed } from 'mobx';
import type { SDLCRoleType } from '@/services/api/role-skills';

/**
 * RoleSkillStore - MobX UI state for role-based skills feature.
 *
 * Tracks client-side UI state for role selection, skill generation wizard,
 * and skill editing. Server state (templates, saved skills) is managed
 * by TanStack Query.
 *
 * T018: Create RoleSkillStore (MobX UI state)
 * Source: FR-001, FR-002, FR-003, FR-004, FR-009, US1, US2, US6
 */

/** Steps in the skill generation wizard. */
export type GenerationStep =
  | 'select'
  | 'path'
  | 'describe'
  | 'generating'
  | 'preview'
  | 'examples'
  | null;

/** Preview data from AI skill generation. */
export interface SkillPreview {
  content: string;
  suggestedName: string;
  wordCount: number;
}

/** Maximum roles per workspace (FR-018). */
const MAX_ROLES = 3;

export class RoleSkillStore {
  /**
   * Roles selected in the role selection grid.
   * First element is automatically the primary role.
   */
  selectedRoles: SDLCRoleType[] = [];

  /** Whether AI skill generation is in progress. */
  isGenerating = false;

  /** Current step in the skill generation wizard. */
  generationStep: GenerationStep = null;

  /** User's expertise description input for AI generation. */
  experienceDescription = '';

  /** Generated skill preview before saving. */
  skillPreview: SkillPreview | null = null;

  /** ID of the skill currently being edited in settings. */
  editingSkillId: string | null = null;

  /** Text input for custom role description. */
  customRoleDescription = '';

  constructor() {
    makeAutoObservable(this, {
      canContinue: computed,
      selectedCount: computed,
      remainingSlots: computed,
      primaryRole: computed,
    });
  }

  // ---------------------------------------------------------------------------
  // Computed
  // ---------------------------------------------------------------------------

  /** Whether the user can proceed from role selection (at least 1 selected). */
  get canContinue(): boolean {
    return this.selectedRoles.length > 0;
  }

  /** Number of currently selected roles. */
  get selectedCount(): number {
    return this.selectedRoles.length;
  }

  /** Remaining selection slots (max 3). */
  get remainingSlots(): number {
    return MAX_ROLES - this.selectedRoles.length;
  }

  /** The primary role (first selected), or null if none selected. */
  get primaryRole(): SDLCRoleType | null {
    return this.selectedRoles[0] ?? null;
  }

  // ---------------------------------------------------------------------------
  // Actions — Role Selection
  // ---------------------------------------------------------------------------

  /**
   * Toggle a role's selection state.
   * - If already selected, removes it.
   * - If not selected and under the max, adds it.
   * - First selected role becomes primary automatically.
   */
  toggleRole(roleType: SDLCRoleType): void {
    const index = this.selectedRoles.indexOf(roleType);

    if (index >= 0) {
      this.selectedRoles.splice(index, 1);
    } else if (this.selectedRoles.length < MAX_ROLES) {
      this.selectedRoles.push(roleType);
    }
  }

  /**
   * Clear all role selections.
   */
  clearSelectedRoles(): void {
    this.selectedRoles = [];
  }

  // ---------------------------------------------------------------------------
  // Actions — Skill Generation Wizard
  // ---------------------------------------------------------------------------

  /**
   * Navigate to a wizard step.
   */
  setGenerationStep(step: GenerationStep): void {
    this.generationStep = step;
  }

  /**
   * Update the experience description input.
   */
  setExperienceDescription(text: string): void {
    this.experienceDescription = text;
  }

  /**
   * Set the AI-generated skill preview.
   */
  setSkillPreview(preview: SkillPreview): void {
    this.skillPreview = preview;
  }

  /**
   * Clear the skill preview.
   */
  clearSkillPreview(): void {
    this.skillPreview = null;
  }

  /**
   * Set generation loading state.
   */
  setIsGenerating(value: boolean): void {
    this.isGenerating = value;
  }

  // ---------------------------------------------------------------------------
  // Actions — Skill Editing (Settings page)
  // ---------------------------------------------------------------------------

  /**
   * Enter edit mode for a skill in settings.
   */
  setEditingSkillId(id: string | null): void {
    this.editingSkillId = id;
  }

  /**
   * Exit edit mode.
   */
  clearEditingSkillId(): void {
    this.editingSkillId = null;
  }

  // ---------------------------------------------------------------------------
  // Actions — Custom Role
  // ---------------------------------------------------------------------------

  /**
   * Update custom role description text.
   */
  setCustomRoleDescription(text: string): void {
    this.customRoleDescription = text;
  }

  // ---------------------------------------------------------------------------
  // Reset
  // ---------------------------------------------------------------------------

  /**
   * Reset store to initial state.
   */
  reset(): void {
    this.selectedRoles = [];
    this.isGenerating = false;
    this.generationStep = null;
    this.experienceDescription = '';
    this.skillPreview = null;
    this.editingSkillId = null;
    this.customRoleDescription = '';
  }
}
