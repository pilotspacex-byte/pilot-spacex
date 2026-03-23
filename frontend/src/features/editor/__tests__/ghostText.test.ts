/**
 * Tests for useMonacoGhostText hook — Monaco InlineCompletionsProvider for AI ghost text.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useMonacoGhostText } from '../hooks/useMonacoGhostText';
import type { GhostTextContext } from '../types';

// --- Mock Monaco types ---

interface MockDisposable {
  dispose: ReturnType<typeof vi.fn>;
}

interface MockProvider {
  provideInlineCompletions: (
    model: MockModel,
    position: MockPosition,
    context: unknown,
    token: MockCancellationToken
  ) => Promise<{ items: Array<{ insertText: string; range: unknown }> }>;
}

interface MockPosition {
  lineNumber: number;
  column: number;
}

interface MockModel {
  getValueInRange: ReturnType<typeof vi.fn>;
  getOffsetAt: ReturnType<typeof vi.fn>;
  getLineCount: ReturnType<typeof vi.fn>;
  getLineMaxColumn: ReturnType<typeof vi.fn>;
}

interface MockCancellationToken {
  isCancellationRequested: boolean;
}

// Track registered providers
let registeredProvider: MockProvider | null = null;
let registeredLanguage: string | null = null;
const mockDisposable: MockDisposable = { dispose: vi.fn() };

function createMockMonaco() {
  registeredProvider = null;
  registeredLanguage = null;

  return {
    languages: {
      registerInlineCompletionsProvider: vi.fn(
        (language: string, provider: MockProvider): MockDisposable => {
          registeredLanguage = language;
          registeredProvider = provider;
          return mockDisposable;
        }
      ),
    },
    Range: class MockRange {
      constructor(
        public startLineNumber: number,
        public startColumn: number,
        public endLineNumber: number,
        public endColumn: number
      ) {}
    },
  };
}

function createMockEditor() {
  return {} as unknown;
}

function createMockModel(): MockModel {
  return {
    getValueInRange: vi.fn(
      (range: {
        startLineNumber: number;
        startColumn: number;
        endLineNumber: number;
        endColumn: number;
      }) => {
        // Return 'before' for text before cursor, 'after' for text after
        if (range.startLineNumber === 1 && range.startColumn === 1) return 'text before cursor';
        return 'text after cursor';
      }
    ),
    getOffsetAt: vi.fn(() => 18),
    getLineCount: vi.fn(() => 5),
    getLineMaxColumn: vi.fn(() => 20),
  };
}

describe('useMonacoGhostText', () => {
  let mockMonaco: ReturnType<typeof createMockMonaco>;
  let mockEditor: unknown;
  let mockFetchCompletion: ReturnType<typeof vi.fn<(ctx: GhostTextContext) => Promise<string>>>;

  beforeEach(() => {
    mockMonaco = createMockMonaco();
    mockEditor = createMockEditor();
    mockFetchCompletion = vi.fn<(ctx: GhostTextContext) => Promise<string>>();
    mockDisposable.dispose.mockClear();
  });

  afterEach(() => {
    registeredProvider = null;
    registeredLanguage = null;
  });

  it('registers InlineCompletionsProvider and returns IDisposable on cleanup', () => {
    const { unmount } = renderHook(() =>
      useMonacoGhostText(mockMonaco as never, mockEditor as never, mockFetchCompletion, 'note-123')
    );

    expect(mockMonaco.languages.registerInlineCompletionsProvider).toHaveBeenCalledTimes(1);
    expect(registeredLanguage).toBe('markdown');
    expect(registeredProvider).toBeTruthy();

    // Cleanup should dispose
    unmount();
    expect(mockDisposable.dispose).toHaveBeenCalledTimes(1);
  });

  it('calls fetchCompletion with textBeforeCursor, textAfterCursor, cursorPosition', async () => {
    mockFetchCompletion.mockResolvedValue('suggested text');

    renderHook(() =>
      useMonacoGhostText(mockMonaco as never, mockEditor as never, mockFetchCompletion, 'note-456')
    );

    expect(registeredProvider).toBeTruthy();

    const model = createMockModel();
    const position: MockPosition = { lineNumber: 2, column: 5 };
    const token: MockCancellationToken = { isCancellationRequested: false };

    const result = await registeredProvider!.provideInlineCompletions(model, position, {}, token);

    expect(mockFetchCompletion).toHaveBeenCalledWith({
      textBeforeCursor: 'text before cursor',
      textAfterCursor: 'text after cursor',
      cursorPosition: 18,
      noteId: 'note-456',
    });

    expect(result.items).toHaveLength(1);
    expect(result.items[0]!.insertText).toBe('suggested text');
  });

  it('returns empty items when fetchCompletion returns empty string', async () => {
    mockFetchCompletion.mockResolvedValue('');

    renderHook(() =>
      useMonacoGhostText(mockMonaco as never, mockEditor as never, mockFetchCompletion, 'note-789')
    );

    const model = createMockModel();
    const position: MockPosition = { lineNumber: 1, column: 1 };
    const token: MockCancellationToken = { isCancellationRequested: false };

    const result = await registeredProvider!.provideInlineCompletions(model, position, {}, token);
    expect(result.items).toHaveLength(0);
  });

  it('returns empty items when cancellation token is requested', async () => {
    mockFetchCompletion.mockResolvedValue('some suggestion');

    renderHook(() =>
      useMonacoGhostText(
        mockMonaco as never,
        mockEditor as never,
        mockFetchCompletion,
        'note-cancel'
      )
    );

    const model = createMockModel();
    const position: MockPosition = { lineNumber: 1, column: 1 };
    const token: MockCancellationToken = { isCancellationRequested: true };

    const result = await registeredProvider!.provideInlineCompletions(model, position, {}, token);
    expect(result.items).toHaveLength(0);
  });

  it('does not register provider when monaco is null', () => {
    renderHook(() =>
      useMonacoGhostText(null, mockEditor as never, mockFetchCompletion, 'note-123')
    );

    expect(registeredProvider).toBeNull();
  });

  it('does not register provider when editor is null', () => {
    renderHook(() =>
      useMonacoGhostText(mockMonaco as never, null, mockFetchCompletion, 'note-123')
    );

    expect(registeredProvider).toBeNull();
  });
});
