import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useSymbolOutline } from './useSymbolOutline';
import type { DocumentSymbol } from '../types';

// Mock parseMarkdownSymbols
vi.mock('../parsers/markdownSymbols', () => ({
  parseMarkdownSymbols: vi.fn(() => []),
}));

import { parseMarkdownSymbols } from '../parsers/markdownSymbols';
const mockParse = vi.mocked(parseMarkdownSymbols);

const MOCK_SYMBOLS: DocumentSymbol[] = [
  {
    name: 'Title',
    kind: 'heading',
    line: 1,
    level: 1,
    children: [
      {
        name: 'Section',
        kind: 'heading',
        line: 5,
        level: 2,
        children: [],
      },
    ],
  },
  {
    name: 'Footer',
    kind: 'heading',
    line: 20,
    level: 1,
    children: [],
  },
];

describe('useSymbolOutline', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockParse.mockReturnValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('returns empty symbols array for empty content', () => {
    const { result } = renderHook(() => useSymbolOutline('', 'markdown', null));
    act(() => {
      vi.advanceTimersByTime(600);
    });
    expect(result.current.symbols).toEqual([]);
  });

  it('returns parsed markdown symbols when language is markdown', () => {
    mockParse.mockReturnValue(MOCK_SYMBOLS);

    const { result } = renderHook(() =>
      useSymbolOutline('# Title\n\n## Section\n\n# Footer', 'markdown', null)
    );

    act(() => {
      vi.advanceTimersByTime(600);
    });

    expect(result.current.symbols).toEqual(MOCK_SYMBOLS);
    expect(mockParse).toHaveBeenCalledWith('# Title\n\n## Section\n\n# Footer');
  });

  it('debounces symbol extraction', () => {
    mockParse.mockReturnValue(MOCK_SYMBOLS);

    const { result } = renderHook(() => useSymbolOutline('# Title', 'markdown', null));

    // Before debounce completes, symbols should be empty
    expect(result.current.symbols).toEqual([]);

    act(() => {
      vi.advanceTimersByTime(600);
    });

    // After debounce, symbols should be populated
    expect(result.current.symbols).toEqual(MOCK_SYMBOLS);
  });

  it('tracks active symbol based on cursor line', () => {
    mockParse.mockReturnValue(MOCK_SYMBOLS);

    // Create a mock editor with cursor position tracking
    const mockEditor = {
      getPosition: vi.fn().mockReturnValue({ lineNumber: 5 }),
      onDidChangeCursorPosition: vi.fn(() => {
        return { dispose: vi.fn() };
      }),
    };

    const { result } = renderHook(() =>
      useSymbolOutline('# Title\n\n## Section', 'markdown', mockEditor as never)
    );

    act(() => {
      vi.advanceTimersByTime(600);
    });

    // Cursor at line 5 should match 'Section' (deepest symbol at line 5)
    expect(result.current.activeSymbolId).toBe('Section');
  });

  it('updates activeSymbolId when cursor moves', () => {
    mockParse.mockReturnValue(MOCK_SYMBOLS);

    let cursorCallback: ((e: unknown) => void) | null = null;
    const mockEditor = {
      getPosition: vi.fn().mockReturnValue({ lineNumber: 1 }),
      onDidChangeCursorPosition: vi.fn((cb: (e: unknown) => void) => {
        cursorCallback = cb;
        return { dispose: vi.fn() };
      }),
    };

    const { result } = renderHook(() =>
      useSymbolOutline('# Title', 'markdown', mockEditor as never)
    );

    act(() => {
      vi.advanceTimersByTime(600);
    });

    expect(result.current.activeSymbolId).toBe('Title');

    // Move cursor to line 20 (Footer)
    mockEditor.getPosition.mockReturnValue({ lineNumber: 20 });
    act(() => {
      cursorCallback?.({ position: { lineNumber: 20 } });
    });

    expect(result.current.activeSymbolId).toBe('Footer');
  });

  it('returns isLoading=true while debounce is pending, false after', () => {
    mockParse.mockReturnValue(MOCK_SYMBOLS);

    const { result } = renderHook(() => useSymbolOutline('# Title', 'markdown', null));

    expect(result.current.isLoading).toBe(true);

    act(() => {
      vi.advanceTimersByTime(600);
    });

    expect(result.current.isLoading).toBe(false);
  });
});
