/**
 * Unit tests for NoteLinkExtension.
 *
 * Tests the TipTap node extension definition:
 * - Node name, group, inline, atom properties
 * - Default options
 * - Config structure (attributes, parse/render, commands, shortcuts)
 *
 * @module features/notes/editor/extensions/__tests__/NoteLinkExtension.test
 */
import { describe, it, expect } from 'vitest';
import { NoteLinkExtension } from '../NoteLinkExtension';

describe('NoteLinkExtension', () => {
  it('has correct node name', () => {
    expect(NoteLinkExtension.name).toBe('noteLink');
  });

  it('is an inline node', () => {
    expect(NoteLinkExtension.config.inline).toBe(true);
    expect(NoteLinkExtension.config.group).toBe('inline');
  });

  it('is an atom node (not directly editable)', () => {
    expect(NoteLinkExtension.config.atom).toBe(true);
  });

  it('is selectable and draggable', () => {
    expect(NoteLinkExtension.config.selectable).toBe(true);
    expect(NoteLinkExtension.config.draggable).toBe(true);
  });

  it('has addAttributes config defined', () => {
    expect(NoteLinkExtension.config.addAttributes).toBeDefined();
  });

  it('has parseHTML config defined', () => {
    expect(NoteLinkExtension.config.parseHTML).toBeDefined();
  });

  it('has renderHTML config defined', () => {
    expect(NoteLinkExtension.config.renderHTML).toBeDefined();
  });

  it('has addCommands config defined', () => {
    expect(NoteLinkExtension.config.addCommands).toBeDefined();
  });

  it('has addKeyboardShortcuts config defined', () => {
    expect(NoteLinkExtension.config.addKeyboardShortcuts).toBeDefined();
  });

  it('has addNodeView config for React rendering', () => {
    expect(NoteLinkExtension.config.addNodeView).toBeDefined();
  });

  it('has default options with correct values', () => {
    expect(NoteLinkExtension.options.workspaceSlug).toBe('');
    expect(NoteLinkExtension.options.currentNoteId).toBe('');
    expect(NoteLinkExtension.options.maxSuggestions).toBe(10);
    expect(NoteLinkExtension.options.debounceMs).toBe(150);
    expect(typeof NoteLinkExtension.options.onSearch).toBe('function');
    expect(NoteLinkExtension.options.onLinkCreated).toBeUndefined();
    expect(NoteLinkExtension.options.onClick).toBeUndefined();
  });

  it('onSearch returns empty array by default', async () => {
    const results = await NoteLinkExtension.options.onSearch('test');
    expect(results).toEqual([]);
  });

  it('has addStorage for markdown serialization', () => {
    expect(NoteLinkExtension.config.addStorage).toBeDefined();
  });

  it('has addProseMirrorPlugins for suggestion handling', () => {
    expect(NoteLinkExtension.config.addProseMirrorPlugins).toBeDefined();
  });
});
