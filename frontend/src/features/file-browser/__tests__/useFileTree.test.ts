import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useFileTree } from '../hooks/useFileTree';
import type { FileTreeItem } from '../hooks/useFileTree';

/**
 * Test fixtures: a nested file tree structure.
 *
 * root/
 *   src/                (directory)
 *     components/       (directory)
 *       Button.tsx      (file)
 *     index.ts          (file)
 *   README.md           (file)
 */
function makeItems(): FileTreeItem[] {
  return [
    {
      id: 'src',
      name: 'src',
      path: '/src',
      type: 'directory',
      source: 'local',
      children: [
        {
          id: 'components',
          name: 'components',
          path: '/src/components',
          type: 'directory',
          source: 'local',
          children: [
            {
              id: 'button',
              name: 'Button.tsx',
              path: '/src/components/Button.tsx',
              type: 'file',
              source: 'local',
              language: 'typescriptreact',
            },
          ],
        },
        {
          id: 'index',
          name: 'index.ts',
          path: '/src/index.ts',
          type: 'file',
          source: 'local',
          language: 'typescript',
        },
      ],
    },
    {
      id: 'readme',
      name: 'README.md',
      path: '/README.md',
      type: 'file',
      source: 'local',
      language: 'markdown',
    },
  ];
}

describe('useFileTree', () => {
  let items: FileTreeItem[];

  beforeEach(() => {
    items = makeItems();
  });

  describe('flattenedItems', () => {
    it('returns empty array when no items', () => {
      const { result } = renderHook(() => useFileTree([]));
      expect(result.current.flattenedItems).toEqual([]);
    });

    it('returns flat file list at depth 0', () => {
      const flatFiles: FileTreeItem[] = [
        { id: 'a', name: 'a.ts', path: '/a.ts', type: 'file', source: 'local' },
        { id: 'b', name: 'b.ts', path: '/b.ts', type: 'file', source: 'local' },
      ];
      const { result } = renderHook(() => useFileTree(flatFiles));
      expect(result.current.flattenedItems).toHaveLength(2);
      expect(result.current.flattenedItems[0]!.depth).toBe(0);
      expect(result.current.flattenedItems[1]!.depth).toBe(0);
    });

    it('returns children at depth+1 when parent is expanded', () => {
      const { result } = renderHook(() => useFileTree(items));
      // Expand 'src'
      act(() => {
        result.current.toggleExpand('src');
      });
      const flat = result.current.flattenedItems;
      // src (0), components (1), index (1), README (0)
      expect(flat).toHaveLength(4);
      expect(flat[0]!.id).toBe('src');
      expect(flat[0]!.depth).toBe(0);
      expect(flat[1]!.id).toBe('components');
      expect(flat[1]!.depth).toBe(1);
      expect(flat[2]!.id).toBe('index');
      expect(flat[2]!.depth).toBe(1);
      expect(flat[3]!.id).toBe('readme');
      expect(flat[3]!.depth).toBe(0);
    });

    it('hides children of collapsed directories', () => {
      const { result } = renderHook(() => useFileTree(items));
      // By default nothing is expanded
      const flat = result.current.flattenedItems;
      // Only top-level: src, README
      expect(flat).toHaveLength(2);
      expect(flat[0]!.id).toBe('src');
      expect(flat[1]!.id).toBe('readme');
    });
  });

  describe('toggleExpand', () => {
    it('adds id to expandedIds if absent', () => {
      const { result } = renderHook(() => useFileTree(items));
      expect(result.current.expandedIds.has('src')).toBe(false);
      act(() => {
        result.current.toggleExpand('src');
      });
      expect(result.current.expandedIds.has('src')).toBe(true);
    });

    it('removes id from expandedIds if present', () => {
      const { result } = renderHook(() => useFileTree(items));
      act(() => {
        result.current.toggleExpand('src');
      });
      expect(result.current.expandedIds.has('src')).toBe(true);
      act(() => {
        result.current.toggleExpand('src');
      });
      expect(result.current.expandedIds.has('src')).toBe(false);
    });
  });

  describe('expandAll / collapseAll', () => {
    it('expandAll expands all directory ids', () => {
      const { result } = renderHook(() => useFileTree(items));
      act(() => {
        result.current.expandAll();
      });
      expect(result.current.expandedIds.has('src')).toBe(true);
      expect(result.current.expandedIds.has('components')).toBe(true);
      // All items visible now: src, components, button, index, readme
      expect(result.current.flattenedItems).toHaveLength(5);
    });

    it('collapseAll clears expandedIds', () => {
      const { result } = renderHook(() => useFileTree(items));
      act(() => {
        result.current.expandAll();
      });
      act(() => {
        result.current.collapseAll();
      });
      expect(result.current.expandedIds.size).toBe(0);
      expect(result.current.flattenedItems).toHaveLength(2);
    });
  });

  describe('keyboard navigation', () => {
    it('ArrowDown moves selectedId to next item', () => {
      const { result } = renderHook(() => useFileTree(items));
      // Flat: src, readme
      act(() => {
        result.current.setSelectedId('src');
      });
      act(() => {
        result.current.handleKeyDown({
          key: 'ArrowDown',
          preventDefault: vi.fn(),
        } as unknown as KeyboardEvent);
      });
      expect(result.current.selectedId).toBe('readme');
    });

    it('ArrowUp moves selectedId to previous item', () => {
      const { result } = renderHook(() => useFileTree(items));
      act(() => {
        result.current.setSelectedId('readme');
      });
      act(() => {
        result.current.handleKeyDown({
          key: 'ArrowUp',
          preventDefault: vi.fn(),
        } as unknown as KeyboardEvent);
      });
      expect(result.current.selectedId).toBe('src');
    });

    it('ArrowRight on collapsed directory expands it', () => {
      const { result } = renderHook(() => useFileTree(items));
      act(() => {
        result.current.setSelectedId('src');
      });
      act(() => {
        result.current.handleKeyDown({
          key: 'ArrowRight',
          preventDefault: vi.fn(),
        } as unknown as KeyboardEvent);
      });
      expect(result.current.expandedIds.has('src')).toBe(true);
    });

    it('ArrowRight on expanded directory moves to first child', () => {
      const { result } = renderHook(() => useFileTree(items));
      act(() => {
        result.current.toggleExpand('src');
      });
      act(() => {
        result.current.setSelectedId('src');
      });
      act(() => {
        result.current.handleKeyDown({
          key: 'ArrowRight',
          preventDefault: vi.fn(),
        } as unknown as KeyboardEvent);
      });
      expect(result.current.selectedId).toBe('components');
    });

    it('ArrowLeft on expanded directory collapses it', () => {
      const { result } = renderHook(() => useFileTree(items));
      act(() => {
        result.current.toggleExpand('src');
      });
      act(() => {
        result.current.setSelectedId('src');
      });
      act(() => {
        result.current.handleKeyDown({
          key: 'ArrowLeft',
          preventDefault: vi.fn(),
        } as unknown as KeyboardEvent);
      });
      expect(result.current.expandedIds.has('src')).toBe(false);
    });

    it('ArrowLeft on file or collapsed dir moves to parent', () => {
      const { result } = renderHook(() => useFileTree(items));
      // Expand src so index is visible
      act(() => {
        result.current.toggleExpand('src');
      });
      act(() => {
        result.current.setSelectedId('index');
      });
      act(() => {
        result.current.handleKeyDown({
          key: 'ArrowLeft',
          preventDefault: vi.fn(),
        } as unknown as KeyboardEvent);
      });
      expect(result.current.selectedId).toBe('src');
    });

    it('Enter on file calls onOpen callback', () => {
      const onOpen = vi.fn();
      const { result } = renderHook(() => useFileTree(items, onOpen));
      // Expand src so index is visible
      act(() => {
        result.current.toggleExpand('src');
      });
      act(() => {
        result.current.setSelectedId('index');
      });
      act(() => {
        result.current.handleKeyDown({
          key: 'Enter',
          preventDefault: vi.fn(),
        } as unknown as KeyboardEvent);
      });
      expect(onOpen).toHaveBeenCalledOnce();
      expect(onOpen).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'index', name: 'index.ts' })
      );
    });
  });
});
