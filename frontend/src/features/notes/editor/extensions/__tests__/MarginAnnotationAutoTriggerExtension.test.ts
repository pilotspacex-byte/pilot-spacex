/**
 * MarginAnnotationAutoTriggerExtension tests (T001)
 * Validates noteId is passed through extension options to trigger context.
 */
import { describe, it, expect } from 'vitest';
import { MarginAnnotationAutoTriggerExtension } from '../MarginAnnotationAutoTriggerExtension';

describe('MarginAnnotationAutoTriggerExtension', () => {
  describe('options', () => {
    it('should have noteId in default options as empty string', () => {
      const ext = MarginAnnotationAutoTriggerExtension.configure({});
      // TipTap extensions expose options after configure
      expect(ext.options).toBeDefined();
      expect(ext.options.noteId).toBe('');
    });

    it('should accept noteId via configure', () => {
      const ext = MarginAnnotationAutoTriggerExtension.configure({
        noteId: 'note-abc-123',
      });
      expect(ext.options.noteId).toBe('note-abc-123');
    });

    it('should preserve default values for other options when noteId is set', () => {
      const ext = MarginAnnotationAutoTriggerExtension.configure({
        noteId: 'note-abc-123',
      });
      expect(ext.options.debounceMs).toBe(2000);
      expect(ext.options.minChars).toBe(50);
      expect(ext.options.contextBlocks).toBe(3);
      expect(ext.options.enabled).toBe(true);
    });

    it('should allow overriding all options together', () => {
      const ext = MarginAnnotationAutoTriggerExtension.configure({
        noteId: 'note-xyz',
        debounceMs: 3000,
        minChars: 100,
        contextBlocks: 5,
        enabled: false,
      });
      expect(ext.options.noteId).toBe('note-xyz');
      expect(ext.options.debounceMs).toBe(3000);
      expect(ext.options.minChars).toBe(100);
      expect(ext.options.contextBlocks).toBe(5);
      expect(ext.options.enabled).toBe(false);
    });
  });
});
