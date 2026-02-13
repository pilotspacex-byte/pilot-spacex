/**
 * TDD red-phase tests for PMBlockExtension (T024).
 *
 * PMBlockExtension is a generic TipTap node that serves as the container for
 * all PM block types: decision, form, raci, risk, timeline, dashboard.
 *
 * Attrs: blockType (string), data (JSON string), version (number).
 *
 * Spec refs: FR-020 (decision), FR-027 (form), FR-030 (RACI),
 * FR-032 (risk), FR-039 (timeline), FR-041 (dashboard)
 *
 * @module pm-blocks/__tests__/PMBlockExtension.test
 */
import { describe, it, expect } from 'vitest';

// This import will fail until the extension is created
import { PMBlockExtension, PM_BLOCK_TYPES } from '../PMBlockExtension';

/** Helper to get typed attribute config from the extension. */
function getAttrs(): Record<
  string,
  {
    default: unknown;
    renderHTML?: (attrs: Record<string, unknown>) => Record<string, string>;
    parseHTML?: (el: HTMLElement) => unknown;
  }
> {
  const fn = PMBlockExtension.config.addAttributes;
  if (typeof fn !== 'function') throw new Error('addAttributes is not a function');
  return fn.call(PMBlockExtension as never) as Record<
    string,
    {
      default: unknown;
      renderHTML?: (attrs: Record<string, unknown>) => Record<string, string>;
      parseHTML?: (el: HTMLElement) => unknown;
    }
  >;
}

// ── Extension basics ────────────────────────────────────────────────────
describe('PMBlockExtension basics', () => {
  it('exports a TipTap node extension', () => {
    expect(PMBlockExtension).toBeDefined();
    expect(PMBlockExtension.name).toBe('pmBlock');
  });

  it('is configured as a block node (not inline)', () => {
    expect(PMBlockExtension.config.group).toBe('block');
  });

  it('is an atom node (not editable content inside)', () => {
    expect(PMBlockExtension.config.atom).toBe(true);
  });

  it('is draggable', () => {
    expect(PMBlockExtension.config.draggable).toBe(true);
  });
});

// ── Block type constants ────────────────────────────────────────────────
describe('PM_BLOCK_TYPES', () => {
  it('exports all 6 block types', () => {
    expect(PM_BLOCK_TYPES).toEqual(['decision', 'form', 'raci', 'risk', 'timeline', 'dashboard']);
  });
});

// ── Attribute schema ────────────────────────────────────────────────────
describe('PMBlockExtension attributes', () => {
  it('defines blockType attr with default "decision"', () => {
    const attrs = getAttrs();
    expect(attrs).toHaveProperty('blockType');
    expect(attrs['blockType']!.default).toBe('decision');
  });

  it('defines data attr with default empty JSON object string', () => {
    const attrs = getAttrs();
    expect(attrs).toHaveProperty('data');
    expect(attrs['data']!.default).toBe('{}');
  });

  it('defines version attr with default 1', () => {
    const attrs = getAttrs();
    expect(attrs).toHaveProperty('version');
    expect(attrs['version']!.default).toBe(1);
  });
});

// ── HTML serialization ──────────────────────────────────────────────────
describe('PMBlockExtension HTML serialization', () => {
  it('renders blockType as data-block-type attribute', () => {
    const attrs = getAttrs();
    const rendered = attrs['blockType']!.renderHTML?.({ blockType: 'decision' });
    expect(rendered).toEqual({ 'data-block-type': 'decision' });
  });

  it('renders data as data-pm-data attribute', () => {
    const attrs = getAttrs();
    const testData = JSON.stringify({ status: 'open' });
    const rendered = attrs['data']!.renderHTML?.({ data: testData });
    expect(rendered).toEqual({ 'data-pm-data': testData });
  });

  it('renders version as data-version attribute', () => {
    const attrs = getAttrs();
    const rendered = attrs['version']!.renderHTML?.({ version: 1 });
    expect(rendered).toEqual({ 'data-version': '1' });
  });

  it('parses blockType from data-block-type', () => {
    const attrs = getAttrs();
    const el = document.createElement('div');
    el.setAttribute('data-block-type', 'form');
    const parsed = attrs['blockType']!.parseHTML?.(el);
    expect(parsed).toBe('form');
  });

  it('parses data from data-pm-data', () => {
    const attrs = getAttrs();
    const el = document.createElement('div');
    const testData = JSON.stringify({ fields: [] });
    el.setAttribute('data-pm-data', testData);
    const parsed = attrs['data']!.parseHTML?.(el);
    expect(parsed).toBe(testData);
  });
});

// ── Node view ───────────────────────────────────────────────────────────
describe('PMBlockExtension node view', () => {
  it('configures addNodeView for React rendering', () => {
    expect(PMBlockExtension.config.addNodeView).toBeDefined();
  });
});
