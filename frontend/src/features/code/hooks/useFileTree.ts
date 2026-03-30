'use client';

import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { Artifact } from '@/types/artifact';

// ─── Tree Node Types ──────────────────────────────────────────────────────────

export interface FileTreeItem {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'directory';
  language?: string;
  children?: FileTreeItem[];
}

export interface FlattenedFileTreeItem extends FileTreeItem {
  depth: number;
  isExpanded: boolean;
  parentId: string | null;
}

// ─── Tree Building ────────────────────────────────────────────────────────────

/**
 * Transform a flat artifact list into a nested FileTreeItem tree.
 * Groups by directory path components.
 */
function buildTree(artifacts: Artifact[]): FileTreeItem[] {
  const root: FileTreeItem[] = [];
  const dirMap = new Map<string, FileTreeItem>();

  // Ensure directories are created for each path segment
  function ensureDir(segments: string[], parentList: FileTreeItem[], parentPath: string): FileTreeItem[] {
    if (segments.length === 0) return parentList;
    const [first, ...rest] = segments;
    if (!first) return parentList;

    const dirPath = parentPath ? `${parentPath}/${first}` : first;
    let dir = dirMap.get(dirPath);
    if (!dir) {
      dir = {
        id: `dir:${dirPath}`,
        name: first,
        path: dirPath,
        type: 'directory',
        children: [],
      };
      dirMap.set(dirPath, dir);
      parentList.push(dir);
    }
    if (rest.length > 0) {
      dir.children = dir.children ?? [];
      ensureDir(rest, dir.children, dirPath);
    }
    return parentList;
  }

  // Sort artifacts: directories first (by path depth), then alphabetically
  const sorted = [...artifacts].sort((a, b) => {
    const aDir = a.filename.includes('/');
    const bDir = b.filename.includes('/');
    if (aDir !== bDir) return aDir ? -1 : 1;
    return a.filename.localeCompare(b.filename);
  });

  for (const artifact of sorted) {
    const parts = artifact.filename.split('/');
    if (parts.length === 1) {
      // Root-level file
      root.push({
        id: artifact.id,
        name: artifact.filename,
        path: artifact.filename,
        type: 'file',
        language: getLanguageFromName(artifact.filename),
      });
    } else {
      // Nested file: ensure parent directories exist
      const dirs = parts.slice(0, -1);
      const filename = parts[parts.length - 1] ?? artifact.filename;
      ensureDir(dirs, root, '');

      // Find the parent dir
      const parentPath = dirs.join('/');
      const parent = dirMap.get(parentPath);
      if (parent) {
        parent.children = parent.children ?? [];
        parent.children.push({
          id: artifact.id,
          name: filename,
          path: artifact.filename,
          type: 'file',
          language: getLanguageFromName(filename),
        });
      }
    }
  }

  return root;
}

/**
 * Get Monaco language ID from a filename.
 */
function getLanguageFromName(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  const EXT_MAP: Record<string, string> = {
    ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
    py: 'python', go: 'go', rs: 'rust', java: 'java',
    json: 'json', yaml: 'yaml', yml: 'yaml', md: 'markdown',
    html: 'html', css: 'css', scss: 'scss', sql: 'sql',
    sh: 'shell', bash: 'shell', rb: 'ruby', php: 'php',
    swift: 'swift', kt: 'kotlin', cpp: 'cpp', c: 'c',
  };
  return EXT_MAP[ext] ?? 'plaintext';
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * useFileTree provides:
 * 1. TanStack Query fetch for project artifacts
 * 2. Tree transformation from flat artifact list
 * 3. Expand/collapse state management
 * 4. Keyboard navigation handlers
 */
export function useFileTree(
  projectId: string,
  workspaceId: string,
  items?: FileTreeItem[],
  onOpen?: (item: FileTreeItem) => void
) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Fetch artifacts via TanStack Query
  const {
    data: artifacts,
    isLoading,
    error,
  } = useQuery<Artifact[]>({
    queryKey: ['artifacts', workspaceId, projectId],
    queryFn: async () => {
      const { artifactsApi } = await import('@/services/api/artifacts');
      return artifactsApi.list(workspaceId, projectId);
    },
    enabled: Boolean(projectId) && Boolean(workspaceId) && !items,
  });

  // Build tree from fetched artifacts OR passed items
  const tree = useMemo<FileTreeItem[]>(() => {
    if (items) return items;
    if (!artifacts) return [];
    return buildTree(artifacts);
  }, [items, artifacts]);

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
    walk(tree);
    return ids;
  }, [tree]);

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
    flatten(tree, 0, null);
    return result;
  }, [tree, expandedIds]);

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
              toggleExpand(current.id);
            } else if (currentIndex < flattenedItems.length - 1) {
              const next = flattenedItems[currentIndex + 1]!;
              if (next.depth > current.depth) setSelectedId(next.id);
            }
          }
          break;
        }
        case 'ArrowLeft': {
          e.preventDefault();
          if (current.type === 'directory' && expandedIds.has(current.id)) {
            toggleExpand(current.id);
          } else if (current.parentId) {
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
    tree,
    isLoading: isLoading && !items,
    error: error as Error | null,
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
