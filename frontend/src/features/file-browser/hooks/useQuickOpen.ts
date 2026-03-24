'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import type { FileTreeItem } from './useFileTree';

/**
 * Fuzzy-match score for substring matching.
 * Returns matched character indices for highlighting, or null if no match.
 */
function fuzzyMatch(query: string, target: string): number[] | null {
  if (!query) return [];
  const lowerQuery = query.toLowerCase();
  const lowerTarget = target.toLowerCase();
  const indices: number[] = [];
  let qi = 0;
  for (let ti = 0; ti < lowerTarget.length && qi < lowerQuery.length; ti++) {
    if (lowerTarget[ti] === lowerQuery[qi]) {
      indices.push(ti);
      qi++;
    }
  }
  return qi === lowerQuery.length ? indices : null;
}

/**
 * Flattens all files from a nested FileTreeItem[] into a flat list (files only).
 */
function flattenFiles(items: FileTreeItem[]): FileTreeItem[] {
  const result: FileTreeItem[] = [];
  function walk(nodes: FileTreeItem[]) {
    for (const node of nodes) {
      if (node.type === 'file') {
        result.push(node);
      }
      if (node.children) {
        walk(node.children);
      }
    }
  }
  walk(items);
  return result;
}

export interface QuickOpenResult {
  item: FileTreeItem;
  nameIndices: number[];
  pathIndices: number[];
}

export function useQuickOpen(allFiles: FileTreeItem[]) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const flatFiles = useMemo(() => flattenFiles(allFiles), [allFiles]);

  const results: QuickOpenResult[] = useMemo(() => {
    if (!query) {
      return flatFiles.slice(0, 10).map((item) => ({
        item,
        nameIndices: [],
        pathIndices: [],
      }));
    }

    const scored: QuickOpenResult[] = [];
    for (const item of flatFiles) {
      const nameMatch = fuzzyMatch(query, item.name);
      const pathMatch = fuzzyMatch(query, item.path);
      if (nameMatch || pathMatch) {
        scored.push({
          item,
          nameIndices: nameMatch ?? [],
          pathIndices: pathMatch ?? [],
        });
      }
    }
    // Prioritize name matches
    return scored.slice(0, 10);
  }, [query, flatFiles]);

  const handleSetQuery = useCallback((q: string) => {
    setQuery(q);
    setSelectedIndex(0);
  }, []);

  const open = useCallback(() => {
    setIsOpen(true);
    setQuery('');
    setSelectedIndex(0);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setQuery('');
  }, []);

  const moveUp = useCallback(() => {
    setSelectedIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const moveDown = useCallback(() => {
    setSelectedIndex((prev) => Math.min(results.length - 1, prev + 1));
  }, [results.length]);

  const selectCurrent = useCallback((): FileTreeItem | null => {
    return results[selectedIndex]?.item ?? null;
  }, [results, selectedIndex]);

  // Global keyboard listener: Cmd+P to open, Escape to close
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'p') {
        e.preventDefault();
        if (isOpen) {
          close();
        } else {
          open();
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, open, close]);

  return {
    isOpen,
    open,
    close,
    query,
    setQuery: handleSetQuery,
    results,
    selectedIndex,
    setSelectedIndex,
    moveUp,
    moveDown,
    selectCurrent,
  };
}
