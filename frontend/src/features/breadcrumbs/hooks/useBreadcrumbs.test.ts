import { renderHook } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useBreadcrumbs } from './useBreadcrumbs';
import type { OpenFile } from '@/features/editor/types';
import type { FileTreeItem } from '@/features/file-browser/hooks/useFileTree';

function makeFile(overrides: Partial<OpenFile> = {}): OpenFile {
  return {
    id: 'file-1',
    name: 'MonacoNoteEditor.tsx',
    path: 'src/features/editor/MonacoNoteEditor.tsx',
    source: 'local',
    language: 'typescript',
    content: '',
    isDirty: false,
    isReadOnly: false,
    ...overrides,
  };
}

function makeTree(): FileTreeItem[] {
  return [
    {
      id: 'src',
      name: 'src',
      path: 'src',
      type: 'directory',
      source: 'local',
      children: [
        {
          id: 'features',
          name: 'features',
          path: 'src/features',
          type: 'directory',
          source: 'local',
          children: [
            {
              id: 'editor',
              name: 'editor',
              path: 'src/features/editor',
              type: 'directory',
              source: 'local',
              children: [
                {
                  id: 'file-a',
                  name: 'FileA.tsx',
                  path: 'src/features/editor/FileA.tsx',
                  type: 'file',
                  source: 'local',
                },
                {
                  id: 'file-b',
                  name: 'FileB.tsx',
                  path: 'src/features/editor/FileB.tsx',
                  type: 'file',
                  source: 'local',
                },
                {
                  id: 'file-1',
                  name: 'MonacoNoteEditor.tsx',
                  path: 'src/features/editor/MonacoNoteEditor.tsx',
                  type: 'file',
                  source: 'local',
                },
              ],
            },
            {
              id: 'file-browser',
              name: 'file-browser',
              path: 'src/features/file-browser',
              type: 'directory',
              source: 'local',
              children: [],
            },
          ],
        },
        {
          id: 'stores',
          name: 'stores',
          path: 'src/stores',
          type: 'directory',
          source: 'local',
          children: [],
        },
      ],
    },
  ];
}

describe('useBreadcrumbs', () => {
  it('returns empty array when no active file', () => {
    const { result } = renderHook(() => useBreadcrumbs(undefined, []));
    expect(result.current).toEqual([]);
  });

  it('splits path into correct number of segments', () => {
    const file = makeFile();
    const tree = makeTree();
    const { result } = renderHook(() => useBreadcrumbs(file, tree));

    expect(result.current).toHaveLength(4);
    expect(result.current.map((s) => s.label)).toEqual([
      'src',
      'features',
      'editor',
      'MonacoNoteEditor.tsx',
    ]);
  });

  it('marks last segment as isLast and first as isFirst', () => {
    const file = makeFile();
    const tree = makeTree();
    const { result } = renderHook(() => useBreadcrumbs(file, tree));

    expect(result.current[0]!.isFirst).toBe(true);
    expect(result.current[0]!.isLast).toBe(false);
    expect(result.current[3]!.isFirst).toBe(false);
    expect(result.current[3]!.isLast).toBe(true);
  });

  it('resolves siblings from file tree', () => {
    const file = makeFile();
    const tree = makeTree();
    const { result } = renderHook(() => useBreadcrumbs(file, tree));

    // "editor" segment should have siblings: editor + file-browser (children of features)
    const featuresSegment = result.current[1]!; // 'features'
    const editorSegment = result.current[2]!; // 'editor'

    // siblings of "features" at its level = children of "src": features, stores
    expect(featuresSegment.siblings.map((s) => s.name)).toContain('features');
    expect(featuresSegment.siblings.map((s) => s.name)).toContain('stores');

    // siblings of "editor" at its level = children of "features": editor, file-browser
    expect(editorSegment.siblings.map((s) => s.name)).toContain('editor');
    expect(editorSegment.siblings.map((s) => s.name)).toContain('file-browser');
  });

  it('handles note files with workspace/project/title segments', () => {
    const file = makeFile({
      path: 'My Workspace/Project Alpha/Design Notes',
      source: 'note',
      name: 'Design Notes',
    });
    const { result } = renderHook(() => useBreadcrumbs(file, []));

    expect(result.current).toHaveLength(3);
    expect(result.current[0]!.label).toBe('My Workspace');
    expect(result.current[2]!.label).toBe('Design Notes');
    expect(result.current[2]!.isLast).toBe(true);
  });

  it('handles single-segment path (just filename)', () => {
    const file = makeFile({ path: 'README.md', name: 'README.md' });
    const { result } = renderHook(() => useBreadcrumbs(file, []));

    expect(result.current).toHaveLength(1);
    expect(result.current[0]!.label).toBe('README.md');
    expect(result.current[0]!.isFirst).toBe(true);
    expect(result.current[0]!.isLast).toBe(true);
  });

  it('builds correct path for each segment', () => {
    const file = makeFile();
    const tree = makeTree();
    const { result } = renderHook(() => useBreadcrumbs(file, tree));

    expect(result.current[0]!.path).toBe('src');
    expect(result.current[1]!.path).toBe('src/features');
    expect(result.current[2]!.path).toBe('src/features/editor');
    expect(result.current[3]!.path).toBe('src/features/editor/MonacoNoteEditor.tsx');
  });
});
