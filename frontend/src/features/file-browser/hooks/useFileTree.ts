'use client';

import { useState, useMemo, useCallback } from 'react';
import type { FileSource } from '@/features/editor/types';

export interface FileTreeItem {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'directory';
  source: FileSource;
  language?: string;
  children?: FileTreeItem[];
}

export interface FlattenedFileTreeItem extends FileTreeItem {
  depth: number;
  isExpanded: boolean;
  parentId: string | null;
}

/**
 * useFileTree provides tree flattening, expand/collapse state, and keyboard
 * navigation for a VS Code-style file tree sidebar.
 */
export function useFileTree(items: FileTreeItem[], onOpen?: (item: FileTreeItem) => void) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Collect all directory IDs for expandAll
  const allDirectoryIds = useMemo(() => {
    const ids = new Set<string>();
    function walk(nodes: FileTreeItem[]) {
      for (const node of nodes) {
        if (node.type === 'directory') {
          ids.add(node.id);
          if (node.children) walk(node.children);
        }
      }
    }
    walk(items);
    return ids;
  }, [items]);

  // Flatten tree respecting expand state via DFS
  const flattenedItems = useMemo(() => {
    const result: FlattenedFileTreeItem[] = [];
    function flatten(nodes: FileTreeItem[], depth: number, parentId: string | null) {
      for (const node of nodes) {
        const isExpanded = node.type === 'directory' && expandedIds.has(node.id);
        result.push({ ...node, depth, isExpanded, parentId });
        if (isExpanded && node.children) {
          flatten(node.children, depth + 1, node.id);
        }
      }
    }
    flatten(items, 0, null);
    return result;
  }, [items, expandedIds]);

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpandedIds(new Set(allDirectoryIds));
  }, [allDirectoryIds]);

  const collapseAll = useCallback(() => {
    setExpandedIds(new Set());
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!selectedId) return;

      const currentIndex = flattenedItems.findIndex((item) => item.id === selectedId);
      if (currentIndex === -1) return;

      const current = flattenedItems[currentIndex]!;

      switch (e.key) {
        case 'ArrowDown': {
          e.preventDefault();
          if (currentIndex < flattenedItems.length - 1) {
            setSelectedId(flattenedItems[currentIndex + 1]!.id);
          }
          break;
        }
        case 'ArrowUp': {
          e.preventDefault();
          if (currentIndex > 0) {
            setSelectedId(flattenedItems[currentIndex - 1]!.id);
          }
          break;
        }
        case 'ArrowRight': {
          e.preventDefault();
          if (current.type === 'directory') {
            if (!expandedIds.has(current.id)) {
              // Collapsed directory: expand it
              toggleExpand(current.id);
            } else {
              // Expanded directory: move to first child
              if (currentIndex < flattenedItems.length - 1) {
                const next = flattenedItems[currentIndex + 1]!;
                if (next.depth > current.depth) {
                  setSelectedId(next.id);
                }
              }
            }
          }
          break;
        }
        case 'ArrowLeft': {
          e.preventDefault();
          if (current.type === 'directory' && expandedIds.has(current.id)) {
            // Expanded directory: collapse it
            toggleExpand(current.id);
          } else if (current.parentId) {
            // File or collapsed dir: move to parent
            setSelectedId(current.parentId);
          }
          break;
        }
        case 'Enter': {
          e.preventDefault();
          if (current.type === 'file' && onOpen) {
            onOpen(current);
          }
          break;
        }
      }
    },
    [selectedId, flattenedItems, expandedIds, toggleExpand, onOpen]
  );

  return {
    expandedIds,
    selectedId,
    setSelectedId,
    flattenedItems,
    toggleExpand,
    expandAll,
    collapseAll,
    handleKeyDown,
  };
}
