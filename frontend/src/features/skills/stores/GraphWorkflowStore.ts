/**
 * GraphWorkflowStore — MobX observable store for graph workflow editor state.
 *
 * Tracks selected node, validation errors, dirty/saving state, and graph ID.
 * Follows sub-store delegation pattern.
 *
 * CRITICAL: The ReactFlow canvas component MUST NOT be wrapped in observer().
 * This store is accessed via GraphWorkflowContext (context bridge pattern).
 */

import { makeAutoObservable } from 'mobx';

import type { ValidationError } from '@/features/skills/utils/graph-validation-engine';
export type { ValidationError } from '@/features/skills/utils/graph-validation-engine';

export interface ExecutionTraceItem {
  nodeId: string;
  stepNumber: number;
}

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

  // ── Execution Preview State ──────────────────────────────────────────────

  /** Ordered list of nodes in execution order (null = no preview) */
  executionTrace: ExecutionTraceItem[] | null = null;

  /** Currently highlighted step index (null = not animating) */
  activeTraceStep: number | null = null;

  /** Whether preview animation is running */
  isPreviewRunning: boolean = false;

  /** Interval handle for trace stepping */
  private _previewInterval: ReturnType<typeof setInterval> | null = null;

  constructor() {
    makeAutoObservable(this, {
      // Exclude private interval from observation
    });
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

  // ── Preview Actions ──────────────────────────────────────────────────────

  startPreview(trace: ExecutionTraceItem[]): void {
    this.stopPreview();
    this.executionTrace = trace;
    this.activeTraceStep = 0;
    this.isPreviewRunning = true;

    this._previewInterval = setInterval(() => {
      this.advanceTraceStep();
    }, 800);
  }

  stopPreview(): void {
    if (this._previewInterval) {
      clearInterval(this._previewInterval);
      this._previewInterval = null;
    }
    this.executionTrace = null;
    this.activeTraceStep = null;
    this.isPreviewRunning = false;
  }

  advanceTraceStep(): void {
    if (this.executionTrace === null || this.activeTraceStep === null) return;
    const nextStep = this.activeTraceStep + 1;
    if (nextStep >= this.executionTrace.length) {
      this.stopPreview();
      return;
    }
    this.activeTraceStep = nextStep;
  }

  // ── Computed ─────────────────────────────────────────────────────────────

  get hasErrors(): boolean {
    return this.validationErrors.length > 0;
  }

  get activeTraceNodeId(): string | null {
    if (
      this.executionTrace === null ||
      this.activeTraceStep === null ||
      this.activeTraceStep >= this.executionTrace.length
    ) {
      return null;
    }
    const step = this.executionTrace[this.activeTraceStep];
    return step?.nodeId ?? null;
  }

  getNodeError(nodeId: string): string | undefined {
    return this.validationErrors.find((e) => e.nodeId === nodeId)?.message;
  }

  getNodeTraceState(nodeId: string): 'active' | 'completed' | 'future' | null {
    if (!this.executionTrace || this.activeTraceStep === null) return null;
    const idx = this.executionTrace.findIndex((t) => t.nodeId === nodeId);
    if (idx === -1) return null;
    if (idx === this.activeTraceStep) return 'active';
    if (idx < this.activeTraceStep) return 'completed';
    return 'future';
  }

  // ── Reset ───────────────────────────────────────────────────────────────

  reset(): void {
    this.stopPreview();
    this.selectedNodeId = null;
    this.validationErrors = [];
    this.isDirty = false;
    this.isSaving = false;
    this.graphId = null;
  }
}
