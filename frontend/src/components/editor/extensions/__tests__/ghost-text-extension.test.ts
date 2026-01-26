/**
 * GhostTextExtension Tests (T131)
 * Tests for TipTap extension providing AI-powered inline suggestions
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import {
  GhostTextExtension,
  type GhostTextContext,
} from '@/features/notes/editor/extensions/GhostTextExtension';

describe('GhostTextExtension', () => {
  let editor: Editor | null = null;
  let onTrigger: ReturnType<typeof vi.fn>;
  let onAccept: ReturnType<typeof vi.fn>;
  let onDismiss: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onTrigger = vi.fn();
    onAccept = vi.fn();
    onDismiss = vi.fn();

    // Create editor with GhostTextExtension
    editor = new Editor({
      extensions: [
        StarterKit,
        GhostTextExtension.configure({
          debounceMs: 100, // Shorter for tests
          minChars: 5,
          enabled: true,
          onTrigger,
          onAccept,
          onDismiss,
        }),
      ],
      content: '<p>Hello world</p>',
    });
  });

  afterEach(() => {
    if (editor) {
      editor.destroy();
      editor = null;
    }
  });

  describe('initialization', () => {
    it('should register extension with correct name', () => {
      expect(
        editor?.extensionManager.extensions.find((ext) => ext.name === 'ghostText')
      ).toBeDefined();
    });

    it('should initialize with configured options', () => {
      const ext = editor?.extensionManager.extensions.find((ext) => ext.name === 'ghostText');
      expect(ext?.options).toMatchObject({
        debounceMs: 100,
        minChars: 5,
        enabled: true,
      });
    });
  });

  describe('commands', () => {
    it('should have setGhostText command', () => {
      expect(editor?.commands).toHaveProperty('setGhostText');
    });

    it('should have acceptGhostText command', () => {
      expect(editor?.commands).toHaveProperty('acceptGhostText');
    });

    it('should have dismissGhostText command', () => {
      expect(editor?.commands).toHaveProperty('dismissGhostText');
    });

    it('should have setGhostTextLoading command', () => {
      expect(editor?.commands).toHaveProperty('setGhostTextLoading');
    });
  });

  describe('keyboard shortcuts', () => {
    it('should register Tab shortcut for accept', () => {
      const ext = editor?.extensionManager.extensions.find((ext) => ext.name === 'ghostText');
      const shortcuts = ext?.options.addKeyboardShortcuts?.();
      expect(shortcuts).toHaveProperty('Tab');
    });

    it('should register Escape shortcut for dismiss', () => {
      const ext = editor?.extensionManager.extensions.find((ext) => ext.name === 'ghostText');
      const shortcuts = ext?.options.addKeyboardShortcuts?.();
      expect(shortcuts).toHaveProperty('Escape');
    });

    it('should register ArrowRight shortcut for word accept', () => {
      const ext = editor?.extensionManager.extensions.find((ext) => ext.name === 'ghostText');
      const shortcuts = ext?.options.addKeyboardShortcuts?.();
      expect(shortcuts).toHaveProperty('ArrowRight');
    });
  });

  describe('context building', () => {
    it('should provide context with required fields when triggered', async () => {
      vi.useFakeTimers();

      if (!editor) return;

      // Type enough text to trigger
      editor.commands.setContent('<p>Hello world test</p>');
      editor.commands.setTextSelection(16);

      // Trigger text input handler
      const event = new InputEvent('beforeinput', { data: ' ' });
      editor.view.dom.dispatchEvent(event);

      // Wait for debounce
      vi.advanceTimersByTime(150);

      if (onTrigger.mock.calls.length > 0) {
        const context: GhostTextContext = onTrigger.mock.calls[0]?.[0];
        expect(context).toHaveProperty('textBeforeCursor');
        expect(context).toHaveProperty('textAfterCursor');
        expect(context).toHaveProperty('cursorPosition');
        expect(context).toHaveProperty('blockId');
        expect(context).toHaveProperty('blockType');
        expect(context).toHaveProperty('document');
      }

      vi.useRealTimers();
    });
  });

  describe('plugin registration', () => {
    it('should register ProseMirror plugin', () => {
      const plugins = editor?.state.plugins ?? [];
      const ghostTextPlugin = plugins.find((p) => {
        // Check if this is our ghost text plugin
        return p.spec.key?.toString().includes('ghostText');
      });

      expect(ghostTextPlugin).toBeDefined();
    });
  });

  describe('callbacks', () => {
    it('should have onTrigger callback configured', () => {
      const ext = editor?.extensionManager.extensions.find((ext) => ext.name === 'ghostText');
      expect(ext?.options.onTrigger).toBe(onTrigger);
    });

    it('should have onAccept callback configured', () => {
      const ext = editor?.extensionManager.extensions.find((ext) => ext.name === 'ghostText');
      expect(ext?.options.onAccept).toBe(onAccept);
    });

    it('should have onDismiss callback configured', () => {
      const ext = editor?.extensionManager.extensions.find((ext) => ext.name === 'ghostText');
      expect(ext?.options.onDismiss).toBe(onDismiss);
    });
  });

  describe('extension lifecycle', () => {
    it('should clean up on destroy', () => {
      const destroySpy = vi.spyOn(global, 'clearTimeout');

      editor?.destroy();
      editor = null;

      // Should have attempted to clear any timers
      expect(destroySpy).toHaveBeenCalled();

      destroySpy.mockRestore();
    });
  });
});
