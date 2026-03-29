/**
 * GraphWorkflowStore — MobX observable store for graph workflow editor state.
 *
 * Tracks selected node, validation errors, dirty/saving state, and graph ID.
 * Follows sub-store delegation pattern from SkillGeneratorStore.
 *
 * CRITICAL: The ReactFlow canvas component MUST NOT be wrapped in observer().
 * This store is accessed via GraphWorkflowContext (context bridge pattern).
 */

import { makeAutoObservable } from 'mobx';

import type { ValidationError } from '@/features/skills/utils/graph-validation-engine';
export type { ValidationError } from '@/features/skills/utils/graph-validation-engine';

export class GraphWorkflowStore {
  /** Currently selected node ID (null = none) */
  selectedNodeId: string | null = null;

  /** Validation errors for nodes in the graph */
  validationErrors: ValidationError[] = [];

  /** Whether unsaved changes exist */
  isDirty: boolean = false;

  /** Whether a save is in progress */
  isSaving: boolean = false;

  /** ID of the current graph being edited (null for new/unsaved) */
  graphId: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  // ── Actions ─────────────────────────────────────────────────────────────

  selectNode(nodeId: string | null): void {
    this.selectedNodeId = nodeId;
  }

  setValidationErrors(errors: ValidationError[]): void {
    this.validationErrors = errors;
  }

  markDirty(): void {
    this.isDirty = true;
  }

  markSaved(): void {
    this.isDirty = false;
    this.isSaving = false;
  }

  setGraphId(id: string | null): void {
    this.graphId = id;
  }

  setSaving(saving: boolean): void {
    this.isSaving = saving;
  }

  // ── Computed ─────────────────────────────────────────────────────────────

  get hasErrors(): boolean {
    return this.validationErrors.length > 0;
  }

  getNodeError(nodeId: string): string | undefined {
    return this.validationErrors.find((e) => e.nodeId === nodeId)?.message;
  }

  // ── Reset ───────────────────────────────────────────────────────────────

  reset(): void {
    this.selectedNodeId = null;
    this.validationErrors = [];
    this.isDirty = false;
    this.isSaving = false;
    this.graphId = null;
  }
}
