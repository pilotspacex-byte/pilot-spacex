/**
 * Tree utility functions for the page hierarchy sidebar.
 *
 * Provides buildTree (flat -> nested) and getAncestors (breadcrumb chain)
 * for use in sidebar tree components and TanStack Query select transforms.
 */

export interface PageTreeNode {
  id: string;
  title: string;
  parentId: string | null;
  depth: number;
  position: number;
  children: PageTreeNode[];
  iconEmoji?: string | null;
}

type FlatNote = {
  id: string;
  title: string;
  parentId?: string | null;
  depth?: number;
  position?: number;
  iconEmoji?: string | null;
};

/**
 * Build a nested tree structure from a flat array of notes.
 *
 * Two-pass algorithm:
 * 1. Create id -> PageTreeNode map with empty children
 * 2. Attach children to parents, collect root nodes
 *
 * Orphan nodes (parentId references a missing parent) are promoted to roots.
 * Children arrays are sorted by position ascending.
 *
 * @param notes Flat array of note objects (from API response)
 * @returns Nested tree nodes, sorted by position at each level
 */
export function buildTree(notes: FlatNote[]): PageTreeNode[] {
  // Pass 1: build map of id -> node
  const nodeMap = new Map<string, PageTreeNode>();
  for (const note of notes) {
    nodeMap.set(note.id, {
      id: note.id,
      title: note.title,
      parentId: note.parentId ?? null,
      depth: note.depth ?? 0,
      position: note.position ?? 0,
      children: [],
      iconEmoji: note.iconEmoji ?? null,
    });
  }

  // Pass 2: attach children to parents, collect roots
  const roots: PageTreeNode[] = [];

  for (const node of nodeMap.values()) {
    if (node.parentId == null) {
      roots.push(node);
    } else {
      const parent = nodeMap.get(node.parentId);
      if (parent) {
        parent.children.push(node);
      } else {
        // Orphan node — parent not in set, treat as root
        roots.push(node);
      }
    }
  }

  // Sort all children arrays by position ascending
  const sortByPosition = (nodes: PageTreeNode[]): void => {
    nodes.sort((a, b) => a.position - b.position);
    for (const node of nodes) {
      if (node.children.length > 0) {
        sortByPosition(node.children);
      }
    }
  };

  sortByPosition(roots);

  return roots;
}

/**
 * Flattens a PageTreeNode[] tree back into a flat array.
 *
 * Needed because useProjectPageTree returns post-select PageTreeNode[] (tree structure),
 * but getAncestors requires a flat array to traverse parentId chains.
 *
 * @param nodes Nested tree nodes (from useProjectPageTree)
 * @returns Flat array with id, title, parentId for each node
 */
export function flattenTree(
  nodes: PageTreeNode[]
): Array<{ id: string; title: string; parentId: string | null }> {
  const result: Array<{ id: string; title: string; parentId: string | null }> = [];

  function walk(nodeList: PageTreeNode[]): void {
    for (const node of nodeList) {
      result.push({ id: node.id, title: node.title, parentId: node.parentId });
      if (node.children.length > 0) {
        walk(node.children);
      }
    }
  }

  walk(nodes);
  return result;
}

/**
 * Flatten a PageTreeNode[] tree into a flat array for DnD SortableContext.
 *
 * Only includes nodes that are currently visible (i.e. their parent is expanded).
 * This ensures the SortableContext items array matches rendered nodes — a
 * requirement of @dnd-kit to avoid id mismatch errors.
 *
 * @param nodes Nested tree nodes (from useProjectPageTree)
 * @param isExpanded Predicate that returns true if a node is expanded
 * @returns Flat array with id, parentId, depth for each visible node
 */
export function flattenTreeWithDepth(
  nodes: PageTreeNode[],
  isExpanded: (id: string) => boolean
): Array<{ id: string; parentId: string | null; depth: number }> {
  const result: Array<{ id: string; parentId: string | null; depth: number }> = [];

  function walk(list: PageTreeNode[]): void {
    for (const node of list) {
      result.push({ id: node.id, parentId: node.parentId, depth: node.depth });
      if (node.children.length > 0 && isExpanded(node.id)) {
        walk(node.children);
      }
    }
  }

  walk(nodes);
  return result;
}

/**
 * Compute the max depth of descendants relative to the given node.
 *
 * Returns 0 for a leaf node (no children), 1 for a node with only
 * direct children, 2 for a node with grandchildren, and so on.
 *
 * Used by ProjectPageTree.handleDragOver to determine whether re-parenting
 * a dragged subtree onto a target would exceed the 3-level depth limit.
 *
 * @param node The root of the subtree to measure
 * @returns Max descendant depth (0 = leaf)
 */
export function getSubtreeHeight(node: PageTreeNode): number {
  if (node.children.length === 0) return 0;
  return 1 + Math.max(...node.children.map(getSubtreeHeight));
}

type AncestorNote = {
  id: string;
  title: string;
  parentId?: string | null;
};

/**
 * Get the ancestor chain for a note, ordered root-first.
 *
 * Traverses parentId chain up from the given noteId, collecting
 * each ancestor until a root (parentId=null) or missing parent is found.
 *
 * @param noteId The note whose ancestors to retrieve
 * @param allNotes Flat array of all notes in scope
 * @returns Ancestor array ordered root-first: [grandparent, parent]
 */
export function getAncestors(
  noteId: string,
  allNotes: AncestorNote[]
): Array<{ id: string; title: string }> {
  const noteMap = new Map<string, AncestorNote>();
  for (const note of allNotes) {
    noteMap.set(note.id, note);
  }

  const current = noteMap.get(noteId);
  if (!current) {
    return [];
  }

  const ancestors: Array<{ id: string; title: string }> = [];
  let parentId = current.parentId ?? null;

  while (parentId != null) {
    const parent = noteMap.get(parentId);
    if (!parent) {
      // Missing parent — stop traversal (partial chain is acceptable)
      break;
    }
    ancestors.unshift({ id: parent.id, title: parent.title });
    parentId = parent.parentId ?? null;
  }

  return ancestors;
}
