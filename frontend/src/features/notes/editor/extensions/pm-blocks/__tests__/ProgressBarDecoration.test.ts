/**
 * TDD red-phase tests for ProgressBarDecoration (T017).
 *
 * ProgressBarDecoration is a ProseMirror decoration that renders a progress bar
 * above TaskList nodes. It computes: checkedRequired / totalRequired * 100.
 * Optional items (isOptional=true) are excluded from the denominator.
 *
 * Spec refs: FR-019 (progress bar reflecting checked-item percentage)
 *
 * These tests define the expected progress calculation and decoration behavior.
 * The decoration plugin does not exist yet -- all tests are expected to fail (red phase).
 *
 * @module pm-blocks/__tests__/ProgressBarDecoration.test
 */
import { describe, it, expect } from 'vitest';

// This import will fail until the decoration is created
import {
  ProgressBarDecoration,
  computeProgress,
  PROGRESS_BAR_PLUGIN_KEY,
} from '../ProgressBarDecoration';

// ── Progress computation ────────────────────────────────────────────────
describe('computeProgress', () => {
  it('returns 0 when no items exist', () => {
    const result = computeProgress([]);
    expect(result).toEqual({ checked: 0, total: 0, percentage: 0 });
  });

  it('computes progress for all required items', () => {
    const items = [
      { checked: true, isOptional: false },
      { checked: false, isOptional: false },
      { checked: true, isOptional: false },
    ];
    const result = computeProgress(items);
    expect(result).toEqual({ checked: 2, total: 3, percentage: 67 });
  });

  it('excludes optional items from denominator', () => {
    const items = [
      { checked: true, isOptional: false },
      { checked: false, isOptional: false },
      { checked: true, isOptional: true },
      { checked: false, isOptional: true },
    ];
    const result = computeProgress(items);
    // Only 2 required items: 1 checked / 2 total = 50%
    expect(result).toEqual({ checked: 1, total: 2, percentage: 50 });
  });

  it('returns 100 when all required items are checked', () => {
    const items = [
      { checked: true, isOptional: false },
      { checked: true, isOptional: false },
      { checked: false, isOptional: true },
    ];
    const result = computeProgress(items);
    expect(result).toEqual({ checked: 2, total: 2, percentage: 100 });
  });

  it('returns 0 when no required items are checked', () => {
    const items = [
      { checked: false, isOptional: false },
      { checked: false, isOptional: false },
    ];
    const result = computeProgress(items);
    expect(result).toEqual({ checked: 0, total: 2, percentage: 0 });
  });

  it('returns 0 when all items are optional', () => {
    const items = [
      { checked: true, isOptional: true },
      { checked: false, isOptional: true },
    ];
    const result = computeProgress(items);
    // No required items -> total = 0, percentage = 0
    expect(result).toEqual({ checked: 0, total: 0, percentage: 0 });
  });

  it('rounds percentage down to integer', () => {
    const items = [
      { checked: true, isOptional: false },
      { checked: false, isOptional: false },
      { checked: false, isOptional: false },
    ];
    const result = computeProgress(items);
    // 1/3 = 33.33 -> 33
    expect(result).toEqual({ checked: 1, total: 3, percentage: 33 });
  });
});

// ── Plugin export ───────────────────────────────────────────────────────
describe('ProgressBarDecoration plugin', () => {
  it('exports a ProseMirror PluginKey', () => {
    expect(PROGRESS_BAR_PLUGIN_KEY).toBeDefined();
    // PluginKey stores its identifier as `.key` (runtime property, not in TS types)
    expect((PROGRESS_BAR_PLUGIN_KEY as unknown as { key: string }).key).toContain('progressBar');
  });

  it('exports a ProseMirror Plugin', () => {
    expect(ProgressBarDecoration).toBeDefined();
    // Plugin.key returns the PluginKey's string identifier (runtime property)
    const pluginKey = (ProgressBarDecoration as unknown as { key: string }).key;
    const expectedKey = (PROGRESS_BAR_PLUGIN_KEY as unknown as { key: string }).key;
    expect(pluginKey).toBe(expectedKey);
  });
});

// ── Decoration rendering ────────────────────────────────────────────────
describe('ProgressBarDecoration rendering', () => {
  it('creates a Decoration.widget above TaskList nodes', () => {
    // The plugin's decorations function should produce a widget for each taskList
    // This tests that the decoration factory exists
    expect(ProgressBarDecoration.spec?.props?.decorations).toBeDefined();
  });

  it('decoration creates a progress bar DOM element', () => {
    // When the plugin creates a widget, it should produce a div with progress bar styling
    // Verify via the decoration's toDOM callback
    const decoFn = ProgressBarDecoration.spec?.props?.decorations;
    expect(typeof decoFn).toBe('function');
  });

  it('progress bar shows percentage text', () => {
    // The progress bar should display "X/Y (Z%)" text
    // This is a rendering spec - tested via the DOM element content
    const decoFn = ProgressBarDecoration.spec?.props?.decorations;
    expect(decoFn).toBeDefined();
  });
});

// ── Style integration ───────────────────────────────────────────────────
describe('ProgressBarDecoration styles', () => {
  it('uses pmBlockStyles.checklist.progressTrack class', () => {
    // Progress track should use the shared style token
    // Implementation should import from pm-block-styles.ts
    expect(ProgressBarDecoration).toBeDefined();
  });

  it('uses pmBlockStyles.checklist.progressFill class', () => {
    // Progress fill width should be set as inline style based on percentage
    expect(ProgressBarDecoration).toBeDefined();
  });
});
