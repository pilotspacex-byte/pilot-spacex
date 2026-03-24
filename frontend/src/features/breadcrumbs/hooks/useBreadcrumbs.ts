import { useMemo } from 'react';
import type { OpenFile } from '@/features/editor/types';
import type { FileTreeItem } from '@/features/file-browser/hooks/useFileTree';
import type { BreadcrumbSegment } from '../types';

/**
 * Find sibling items at a given level in the file tree by walking the tree
 * to match the path prefix and returning children at that depth.
 */
function findSiblingsAtPath(
  tree: FileTreeItem[],
  pathParts: string[],
  depth: number
): { id: string; name: string; path: string }[] {
  if (depth === 0) {
    // Top level: siblings are the root items
    return tree.map((item) => ({ id: item.id, name: item.name, path: item.path }));
  }

  // Walk the tree to find the parent at depth-1
  let currentLevel = tree;
  for (let i = 0; i < depth; i++) {
    const targetName = pathParts[i];
    const match = currentLevel.find((item) => item.name === targetName);
    if (!match || !match.children) {
      return [];
    }
    currentLevel = match.children;
  }

  return currentLevel.map((item) => ({ id: item.id, name: item.name, path: item.path }));
}

/**
 * Derive breadcrumb segments from the active file path and file tree.
 *
 * Splits the file path into segments, resolves sibling items at each
 * tree level, and marks first/last segments for styling.
 */
export function useBreadcrumbs(
  activeFile: OpenFile | undefined,
  fileTreeItems: FileTreeItem[]
): BreadcrumbSegment[] {
  return useMemo(() => {
    if (!activeFile) return [];

    const parts = activeFile.path.split('/').filter(Boolean);
    if (parts.length === 0) return [];

    return parts.map((part, index) => {
      const path = parts.slice(0, index + 1).join('/');
      const siblings = findSiblingsAtPath(fileTreeItems, parts, index);

      return {
        label: part,
        path,
        isFirst: index === 0,
        isLast: index === parts.length - 1,
        siblings,
      };
    });
  }, [activeFile, fileTreeItems]);
}
