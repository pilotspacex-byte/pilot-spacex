import { describe, it, expect } from 'vitest';
import { buildTree, getAncestors, flattenTree } from '../tree-utils';
import type { PageTreeNode } from '../tree-utils';

// ---------------------------------------------------------------------------
// buildTree tests
// ---------------------------------------------------------------------------

describe('buildTree', () => {
  it('converts flat array into nested tree structure', () => {
    const flat = [
      { id: 'a', title: 'Root', parentId: null, depth: 0, position: 1000 },
      { id: 'b', title: 'Child', parentId: 'a', depth: 1, position: 1000 },
    ];

    const tree = buildTree(flat);

    expect(tree).toHaveLength(1);

    const root = tree[0]!;
    expect(root.id).toBe('a');
    expect(root.children).toHaveLength(1);

    expect(root.children[0]!.id).toBe('b');

    expect(root.children[0]!.children).toHaveLength(0);
  });

  it('sorts children by position within each parent group', () => {
    const flat = [
      { id: 'a', title: 'Root', parentId: null, depth: 0, position: 1000 },
      { id: 'c', title: 'Child C', parentId: 'a', depth: 1, position: 3000 },
      { id: 'b', title: 'Child B', parentId: 'a', depth: 1, position: 2000 },
      { id: 'd', title: 'Child D', parentId: 'a', depth: 1, position: 1000 },
    ];

    const tree = buildTree(flat);

    const children = tree[0]!.children;
    expect(children).toHaveLength(3);
    // Should be sorted by position ascending

    expect(children[0]!.id).toBe('d'); // position 1000

    expect(children[1]!.id).toBe('b'); // position 2000

    expect(children[2]!.id).toBe('c'); // position 3000
  });

  it('returns empty array for empty input', () => {
    const tree = buildTree([]);
    expect(tree).toEqual([]);
  });

  it('handles orphan nodes (parentId references missing parent) — treats as roots', () => {
    const flat = [
      { id: 'a', title: 'Root', parentId: null, depth: 0, position: 1000 },
      // 'b' references missing parent 'missing-id' — should become a root
      { id: 'b', title: 'Orphan', parentId: 'missing-id', depth: 1, position: 1000 },
    ];

    const tree = buildTree(flat);

    // Both become roots since parent is missing
    expect(tree).toHaveLength(2);
    const ids = tree.map((n) => n.id);
    expect(ids).toContain('a');
    expect(ids).toContain('b');
  });

  it('builds multi-level tree (root -> section -> page)', () => {
    const flat = [
      { id: 'root', title: 'Root', parentId: null, depth: 0, position: 1000 },
      { id: 'section', title: 'Section', parentId: 'root', depth: 1, position: 1000 },
      { id: 'page', title: 'Page', parentId: 'section', depth: 2, position: 1000 },
    ];

    const tree = buildTree(flat);

    expect(tree).toHaveLength(1);

    const root = tree[0]!;
    expect(root.children).toHaveLength(1);

    const section = root.children[0]!;
    expect(section.children).toHaveLength(1);

    expect(section.children[0]!.id).toBe('page');
  });

  it('defaults depth and position to 0 when not provided', () => {
    const flat = [{ id: 'a', title: 'Root', parentId: null }];

    const tree = buildTree(flat);

    const node = tree[0]!;
    expect(node.depth).toBe(0);
    expect(node.position).toBe(0);
  });

  it('produces nodes with correct shape including all fields', () => {
    const flat = [{ id: 'a', title: 'Root', parentId: null, depth: 0, position: 500 }];

    const tree = buildTree(flat);

    const node: PageTreeNode = tree[0]!;

    expect(node.id).toBe('a');
    expect(node.title).toBe('Root');
    expect(node.parentId).toBeNull();
    expect(node.depth).toBe(0);
    expect(node.position).toBe(500);
    expect(Array.isArray(node.children)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// getAncestors tests
// ---------------------------------------------------------------------------

describe('getAncestors', () => {
  const allNotes = [
    { id: 'grandparent', title: 'Grandparent', parentId: null },
    { id: 'parent', title: 'Parent', parentId: 'grandparent' },
    { id: 'child', title: 'Child', parentId: 'parent' },
  ];

  it('returns [] for a root node (parentId=null)', () => {
    const ancestors = getAncestors('grandparent', allNotes);
    expect(ancestors).toEqual([]);
  });

  it('returns [grandparent, parent] for a depth-2 node (root-first order)', () => {
    const ancestors = getAncestors('child', allNotes);
    expect(ancestors).toHaveLength(2);

    expect(ancestors[0]!.id).toBe('grandparent'); // root-first

    expect(ancestors[1]!.id).toBe('parent');
  });

  it('returns [parent] for a depth-1 node', () => {
    const ancestors = getAncestors('parent', allNotes);
    expect(ancestors).toHaveLength(1);

    expect(ancestors[0]!.id).toBe('grandparent');
  });

  it('handles missing parent gracefully — returns partial chain', () => {
    const notesWithMissingParent = [{ id: 'child', title: 'Child', parentId: 'missing-parent' }];

    // Should not throw; returns empty since parent is not found
    const ancestors = getAncestors('child', notesWithMissingParent);
    expect(Array.isArray(ancestors)).toBe(true);
    // Could be empty or partial — must not throw
  });

  it('returns [] for unknown noteId', () => {
    const ancestors = getAncestors('nonexistent', allNotes);
    expect(ancestors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// flattenTree tests
// ---------------------------------------------------------------------------

describe('flattenTree', () => {
  it('converts PageTreeNode[] tree into flat array preserving all nodes', () => {
    const tree: PageTreeNode[] = [
      {
        id: 'root',
        title: 'Root',
        parentId: null,
        depth: 0,
        position: 1000,
        children: [
          {
            id: 'child',
            title: 'Child',
            parentId: 'root',
            depth: 1,
            position: 1000,
            children: [
              {
                id: 'grandchild',
                title: 'Grandchild',
                parentId: 'child',
                depth: 2,
                position: 1000,
                children: [],
              },
            ],
          },
        ],
      },
    ];

    const flat = flattenTree(tree);

    expect(flat).toHaveLength(3);
    const ids = flat.map((n) => n.id);
    expect(ids).toContain('root');
    expect(ids).toContain('child');
    expect(ids).toContain('grandchild');
  });

  it('returns empty array for empty input', () => {
    const result = flattenTree([]);
    expect(result).toEqual([]);
  });

  it('preserves parentId relationships in flat output', () => {
    const tree: PageTreeNode[] = [
      {
        id: 'root',
        title: 'Root',
        parentId: null,
        depth: 0,
        position: 1000,
        children: [
          {
            id: 'child',
            title: 'Child',
            parentId: 'root',
            depth: 1,
            position: 1000,
            children: [],
          },
        ],
      },
    ];

    const flat = flattenTree(tree);

    const root = flat.find((n) => n.id === 'root');
    const child = flat.find((n) => n.id === 'child');

    expect(root?.parentId).toBeNull();
    expect(child?.parentId).toBe('root');
  });

  it('handles multiple root nodes', () => {
    const tree: PageTreeNode[] = [
      { id: 'a', title: 'A', parentId: null, depth: 0, position: 1000, children: [] },
      { id: 'b', title: 'B', parentId: null, depth: 0, position: 2000, children: [] },
    ];

    const flat = flattenTree(tree);

    expect(flat).toHaveLength(2);
    const ids = flat.map((n) => n.id);
    expect(ids).toContain('a');
    expect(ids).toContain('b');
  });
});
