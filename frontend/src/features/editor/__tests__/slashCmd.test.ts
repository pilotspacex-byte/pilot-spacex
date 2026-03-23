/**
 * Tests for useMonacoSlashCmd hook — Monaco CompletionItemProvider for slash commands and mentions.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useMonacoSlashCmd } from '../hooks/useMonacoSlashCmd';

// --- Mock Monaco types ---

interface MockDisposable {
  dispose: ReturnType<typeof vi.fn>;
}

interface MockCompletionProvider {
  triggerCharacters: string[];
  provideCompletionItems: (
    model: MockModel,
    position: MockPosition,
    context: unknown,
    token: MockCancellationToken
  ) =>
    | Promise<{
        suggestions: Array<{
          label: string;
          insertText: string;
          kind: number;
          documentation?: string;
          range: unknown;
          sortText?: string;
        }>;
      }>
    | {
        suggestions: Array<{
          label: string;
          insertText: string;
          kind: number;
          documentation?: string;
          range: unknown;
          sortText?: string;
        }>;
      };
}

interface MockPosition {
  lineNumber: number;
  column: number;
}

interface MockModel {
  getLineContent: ReturnType<typeof vi.fn>;
}

interface MockCancellationToken {
  isCancellationRequested: boolean;
}

// Track registered providers
let registeredProviders: Array<{ language: string; provider: MockCompletionProvider }> = [];
const mockDisposable1: MockDisposable = { dispose: vi.fn() };
const mockDisposable2: MockDisposable = { dispose: vi.fn() };
let disposableIndex = 0;

function createMockMonaco() {
  registeredProviders = [];
  disposableIndex = 0;

  return {
    languages: {
      registerCompletionItemProvider: vi.fn(
        (language: string, provider: MockCompletionProvider): MockDisposable => {
          registeredProviders.push({ language, provider });
          const d = disposableIndex === 0 ? mockDisposable1 : mockDisposable2;
          disposableIndex++;
          return d;
        }
      ),
      CompletionItemKind: {
        Function: 1,
        User: 16,
        Snippet: 27,
      },
      CompletionItemInsertTextRule: {
        InsertAsSnippet: 4,
      },
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

function createMockModel(lineContent = '/he'): MockModel {
  return {
    getLineContent: vi.fn(() => lineContent),
  };
}

describe('useMonacoSlashCmd', () => {
  let mockMonaco: ReturnType<typeof createMockMonaco>;
  let mockEditor: unknown;

  beforeEach(() => {
    mockMonaco = createMockMonaco();
    mockEditor = createMockEditor();
    mockDisposable1.dispose.mockClear();
    mockDisposable2.dispose.mockClear();
  });

  afterEach(() => {
    registeredProviders = [];
  });

  it('registers two CompletionItemProviders (slash and mention)', () => {
    renderHook(() => useMonacoSlashCmd(mockMonaco as never, mockEditor as never));

    expect(mockMonaco.languages.registerCompletionItemProvider).toHaveBeenCalledTimes(2);
    expect(registeredProviders).toHaveLength(2);

    // Both should be for markdown
    expect(registeredProviders[0]!.language).toBe('markdown');
    expect(registeredProviders[1]!.language).toBe('markdown');
  });

  it('slash command provider triggers on "/" character', () => {
    renderHook(() => useMonacoSlashCmd(mockMonaco as never, mockEditor as never));

    const slashProvider = registeredProviders.find((p) =>
      p.provider.triggerCharacters.includes('/')
    );
    expect(slashProvider).toBeTruthy();
  });

  it('slash command provider returns completion items for known commands', () => {
    renderHook(() => useMonacoSlashCmd(mockMonaco as never, mockEditor as never));

    const slashProvider = registeredProviders.find((p) =>
      p.provider.triggerCharacters.includes('/')
    )!;

    const model = createMockModel('/');
    const position: MockPosition = { lineNumber: 1, column: 2 };
    const token: MockCancellationToken = { isCancellationRequested: false };

    const result = slashProvider.provider.provideCompletionItems(model, position, {}, token);

    // Result should be synchronous or a promise
    const handleResult = (res: { suggestions: Array<{ label: string; insertText: string }> }) => {
      expect(res.suggestions.length).toBeGreaterThan(0);

      // Check known commands are present
      const labels = res.suggestions.map((s) => s.label);
      expect(labels).toContain('Heading 1');
      expect(labels).toContain('Bullet List');
      expect(labels).toContain('Code Block');
      expect(labels).toContain('Divider');
    };

    if (result instanceof Promise) {
      return result.then(handleResult);
    }
    handleResult(result as { suggestions: Array<{ label: string; insertText: string }> });
  });

  it('each completion item has label, insertText, and documentation', () => {
    renderHook(() => useMonacoSlashCmd(mockMonaco as never, mockEditor as never));

    const slashProvider = registeredProviders.find((p) =>
      p.provider.triggerCharacters.includes('/')
    )!;

    const model = createMockModel('/');
    const position: MockPosition = { lineNumber: 1, column: 2 };
    const token: MockCancellationToken = { isCancellationRequested: false };

    const result = slashProvider.provider.provideCompletionItems(model, position, {}, token);

    const handleResult = (res: {
      suggestions: Array<{ label: string; insertText: string; documentation?: string }>;
    }) => {
      for (const item of res.suggestions) {
        expect(item.label).toBeTruthy();
        expect(item.insertText).toBeTruthy();
        expect(item.documentation).toBeTruthy();
      }
    };

    if (result instanceof Promise) {
      return result.then(handleResult);
    }
    handleResult(
      result as {
        suggestions: Array<{ label: string; insertText: string; documentation?: string }>;
      }
    );
  });

  it('includes PM block slash commands including pm:decision', () => {
    renderHook(() => useMonacoSlashCmd(mockMonaco as never, mockEditor as never));

    const slashProvider = registeredProviders.find((p) =>
      p.provider.triggerCharacters.includes('/')
    )!;

    const model = createMockModel('/');
    const position: MockPosition = { lineNumber: 1, column: 2 };
    const token: MockCancellationToken = { isCancellationRequested: false };

    const result = slashProvider.provider.provideCompletionItems(model, position, {}, token);

    const handleResult = (res: { suggestions: Array<{ label: string; insertText: string }> }) => {
      const labels = res.suggestions.map((s) => s.label);
      expect(labels).toContain('Decision Record');
      expect(labels).toContain('RACI Matrix');
      expect(labels).toContain('Risk Register');
      expect(labels).toContain('Timeline');
      expect(labels).toContain('KPI Dashboard');
      expect(labels).toContain('Form');

      // Check that pm:decision insert text is present
      const decisionItem = res.suggestions.find((s) => s.label === 'Decision Record');
      expect(decisionItem?.insertText).toContain('pm:decision');
    };

    if (result instanceof Promise) {
      return result.then(handleResult);
    }
    handleResult(result as { suggestions: Array<{ label: string; insertText: string }> });
  });

  it('mention provider triggers on "@" character', () => {
    renderHook(() => useMonacoSlashCmd(mockMonaco as never, mockEditor as never));

    const mentionProvider = registeredProviders.find((p) =>
      p.provider.triggerCharacters.includes('@')
    );
    expect(mentionProvider).toBeTruthy();
  });

  it('mention provider calls fetchMembers and returns member completion items', async () => {
    const mockFetchMembers = vi.fn().mockResolvedValue([
      { id: 'u1', name: 'Alice Smith', email: 'alice@example.com' },
      { id: 'u2', name: 'Bob Jones', email: 'bob@example.com' },
    ]);

    renderHook(() => useMonacoSlashCmd(mockMonaco as never, mockEditor as never, mockFetchMembers));

    const mentionProvider = registeredProviders.find((p) =>
      p.provider.triggerCharacters.includes('@')
    )!;

    const model = createMockModel('@ali');
    const position: MockPosition = { lineNumber: 1, column: 5 };
    const token: MockCancellationToken = { isCancellationRequested: false };

    const result = await mentionProvider.provider.provideCompletionItems(
      model,
      position,
      {},
      token
    );

    expect(mockFetchMembers).toHaveBeenCalled();
    expect(result.suggestions).toHaveLength(2);
    expect(result.suggestions[0]!.label).toBe('Alice Smith');
    expect(result.suggestions[1]!.label).toBe('Bob Jones');
  });

  it('disposes both providers on cleanup', () => {
    const { unmount } = renderHook(() =>
      useMonacoSlashCmd(mockMonaco as never, mockEditor as never)
    );

    unmount();
    expect(mockDisposable1.dispose).toHaveBeenCalledTimes(1);
    expect(mockDisposable2.dispose).toHaveBeenCalledTimes(1);
  });

  it('does not register providers when monaco is null', () => {
    renderHook(() => useMonacoSlashCmd(null, mockEditor as never));

    expect(registeredProviders).toHaveLength(0);
  });
});
