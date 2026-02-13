/**
 * TDD red-phase tests for TaskItemEnhanced extension (T015).
 *
 * TaskItemEnhanced extends TipTap's default TaskItem with 6 new attrs:
 * assignee, dueDate, priority, isOptional, estimatedEffort, conditionalParentId.
 *
 * Spec refs: FR-013 (structured checklist), FR-014 (assignee),
 * FR-015 (due date), FR-016 (priority), FR-017 (optional flag),
 * FR-018 (conditional visibility)
 *
 * These tests define the expected attribute schema and serialization behavior.
 * The extension does not exist yet -- all tests are expected to fail (red phase).
 *
 * @module pm-blocks/__tests__/TaskItemEnhanced.test
 */
import { describe, it, expect } from 'vitest';

// This import will fail until the extension is created
import { TaskItemEnhanced } from '../TaskItemEnhanced';

/** Helper to extract attrs with proper typing for test assertions. */
function getAttrs(): Record<
  string,
  {
    default: unknown;
    renderHTML?: (attrs: Record<string, unknown>) => Record<string, string>;
    parseHTML?: (el: HTMLElement) => unknown;
  }
> {
  const fn = TaskItemEnhanced.config.addAttributes;
  if (typeof fn !== 'function') throw new Error('addAttributes is not a function');
  return fn.call(TaskItemEnhanced as never) as Record<
    string,
    {
      default: unknown;
      renderHTML?: (attrs: Record<string, unknown>) => Record<string, string>;
      parseHTML?: (el: HTMLElement) => unknown;
    }
  >;
}

// ── Attr schema ─────────────────────────────────────────────────────────
describe('TaskItemEnhanced attribute schema', () => {
  it('exports a TipTap extension', () => {
    expect(TaskItemEnhanced).toBeDefined();
    expect(TaskItemEnhanced.name).toBe('taskItem');
  });

  it('defines assignee attr with default null', () => {
    const attrs = getAttrs();
    expect(attrs).toHaveProperty('assignee');
    expect(attrs['assignee']!.default).toBeNull();
  });

  it('defines dueDate attr with default null', () => {
    const attrs = getAttrs();
    expect(attrs).toHaveProperty('dueDate');
    expect(attrs['dueDate']!.default).toBeNull();
  });

  it('defines priority attr with default "none"', () => {
    const attrs = getAttrs();
    expect(attrs).toHaveProperty('priority');
    expect(attrs['priority']!.default).toBe('none');
  });

  it('defines isOptional attr with default false', () => {
    const attrs = getAttrs();
    expect(attrs).toHaveProperty('isOptional');
    expect(attrs['isOptional']!.default).toBe(false);
  });

  it('defines estimatedEffort attr with default null', () => {
    const attrs = getAttrs();
    expect(attrs).toHaveProperty('estimatedEffort');
    expect(attrs['estimatedEffort']!.default).toBeNull();
  });

  it('defines conditionalParentId attr with default null', () => {
    const attrs = getAttrs();
    expect(attrs).toHaveProperty('conditionalParentId');
    expect(attrs['conditionalParentId']!.default).toBeNull();
  });

  it('preserves the original checked attr', () => {
    const attrs = getAttrs();
    expect(attrs).toHaveProperty('checked');
    expect(attrs['checked']!.default).toBe(false);
  });
});

// ── HTML serialization (parseHTML / renderHTML) ─────────────────────────
describe('TaskItemEnhanced HTML serialization', () => {
  it('renders assignee as data-assignee attribute', () => {
    const attrs = getAttrs();
    const rendered = attrs['assignee']!.renderHTML?.({ assignee: 'user-123' });
    expect(rendered).toEqual({ 'data-assignee': 'user-123' });
  });

  it('renders dueDate as data-due-date attribute', () => {
    const attrs = getAttrs();
    const rendered = attrs['dueDate']!.renderHTML?.({ dueDate: '2026-03-15' });
    expect(rendered).toEqual({ 'data-due-date': '2026-03-15' });
  });

  it('renders priority as data-priority attribute', () => {
    const attrs = getAttrs();
    const rendered = attrs['priority']!.renderHTML?.({ priority: 'high' });
    expect(rendered).toEqual({ 'data-priority': 'high' });
  });

  it('renders isOptional as data-optional attribute', () => {
    const attrs = getAttrs();
    const rendered = attrs['isOptional']!.renderHTML?.({ isOptional: true });
    expect(rendered).toEqual({ 'data-optional': 'true' });
  });

  it('renders estimatedEffort as data-estimated-effort attribute', () => {
    const attrs = getAttrs();
    const rendered = attrs['estimatedEffort']!.renderHTML?.({ estimatedEffort: '3sp' });
    expect(rendered).toEqual({ 'data-estimated-effort': '3sp' });
  });

  it('renders conditionalParentId as data-conditional-parent attribute', () => {
    const attrs = getAttrs();
    const rendered = attrs['conditionalParentId']!.renderHTML?.({
      conditionalParentId: 'block-abc',
    });
    expect(rendered).toEqual({ 'data-conditional-parent': 'block-abc' });
  });

  it('does not render null attrs as HTML attributes', () => {
    const attrs = getAttrs();
    const rendered = attrs['assignee']!.renderHTML?.({ assignee: null });
    // Null attrs should not produce DOM attributes
    expect(rendered).toEqual({});
  });
});

// ── JSON serialization ──────────────────────────────────────────────────
describe('TaskItemEnhanced JSON serialization', () => {
  it('includes all 6 new attrs in toJSON output', () => {
    // Verify the extension's attribute config defines all 6 new attrs
    const attrs = getAttrs();
    const attrNames = Object.keys(attrs);
    expect(attrNames).toContain('assignee');
    expect(attrNames).toContain('dueDate');
    expect(attrNames).toContain('priority');
    expect(attrNames).toContain('isOptional');
    expect(attrNames).toContain('estimatedEffort');
    expect(attrNames).toContain('conditionalParentId');
  });

  it('priority accepts valid values: none, low, medium, high, urgent', () => {
    const validPriorities = ['none', 'low', 'medium', 'high', 'urgent'];
    // Extension should accept these values without throwing
    const attrs = getAttrs();
    for (const p of validPriorities) {
      const rendered = attrs['priority']!.renderHTML?.({ priority: p });
      expect(rendered).toEqual({ 'data-priority': p });
    }
  });
});
