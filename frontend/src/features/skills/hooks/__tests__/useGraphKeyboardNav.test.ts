/**
 * Tests for useGraphKeyboardNav (Phase 92 Plan 03 Task 2).
 *
 * Pure-logic hook: arrow/Enter/Esc handlers + node click dispatch. The
 * harness uses synthetic React Flow Node/Edge fixtures so the hook can be
 * exercised without mounting a canvas.
 *
 * UI-SPEC §Interaction Contract:
 *   - ↓ on skill   → first reference file (target of outgoing edge)
 *   - ↑ on file    → parent skill (source of incoming edge)
 *   - → on any     → next sibling within rank (alphabetical, wraps)
 *   - ← on any     → previous sibling within rank (wraps)
 *   - Enter on skill → router.push(/{ws}/skills/{slug})
 *   - Enter on file  → onOpenFilePeek(parentSkillSlug, path)
 *   - Esc          → clear selection
 *   - other keys   → no-op (no preventDefault, no state change)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import type { Edge, Node } from '@xyflow/react';
import type { FlowNodeData } from '../useSkillGraphLayout';

// ── Mocks ───────────────────────────────────────────────────────────────────

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

import { useGraphKeyboardNav } from '../useGraphKeyboardNav';

// ── Fixtures ────────────────────────────────────────────────────────────────

function makeSkillNode(slug: string, label = slug): Node<FlowNodeData> {
  return {
    id: `skill:${slug}`,
    type: 'skill',
    position: { x: 0, y: 0 },
    data: { label, kind: 'skill', slug, refCount: 0 },
  };
}

function makeFileNode(path: string, parentSkillSlug: string): Node<FlowNodeData> {
  return {
    id: `file:${path}`,
    type: 'file',
    position: { x: 0, y: 0 },
    data: {
      label: path.split('/').pop() ?? path,
      kind: 'file',
      path,
      parentSkillSlugs: [parentSkillSlug],
    },
  };
}

function makeEdge(source: string, target: string): Edge {
  return { id: `edge:${source}->${target}`, source, target };
}

// Canonical fixture: 2 skills, 2 files, alphabetical.
//   alpha → docs/a.md
//   beta  → docs/b.md
const FLOW_NODES: Node<FlowNodeData>[] = [
  makeSkillNode('alpha', 'Alpha'),
  makeSkillNode('beta', 'Beta'),
  makeFileNode('docs/a.md', 'alpha'),
  makeFileNode('docs/b.md', 'beta'),
];

const FLOW_EDGES: Edge[] = [
  makeEdge('skill:alpha', 'file:docs/a.md'),
  makeEdge('skill:beta', 'file:docs/b.md'),
];

function makeKeyboardEvent(key: string): React.KeyboardEvent {
  return {
    key,
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
  } as unknown as React.KeyboardEvent;
}

function makeMouseEvent(): React.MouseEvent {
  return {
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
  } as unknown as React.MouseEvent;
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe('useGraphKeyboardNav', () => {
  const onOpenFilePeek = vi.fn();

  beforeEach(() => {
    mockPush.mockReset();
    onOpenFilePeek.mockReset();
  });

  function setup() {
    return renderHook(() =>
      useGraphKeyboardNav({
        flowNodes: FLOW_NODES,
        flowEdges: FLOW_EDGES,
        workspaceSlug: 'workspace',
        onOpenFilePeek,
      }),
    );
  }

  it('initial selectedId === null', () => {
    const { result } = setup();
    expect(result.current.selectedId).toBeNull();
  });

  it('onNodeClick sets selectedId to the clicked node', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[0]!);
    });
    expect(result.current.selectedId).toBe('skill:alpha');
  });

  it('onNodeDoubleClick on skill calls router.push to detail page', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeDoubleClick(makeMouseEvent(), FLOW_NODES[0]!);
    });
    expect(mockPush).toHaveBeenCalledWith('/workspace/skills/alpha');
    expect(onOpenFilePeek).not.toHaveBeenCalled();
  });

  it('onNodeDoubleClick on file calls onOpenFilePeek with parent slug + path', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeDoubleClick(makeMouseEvent(), FLOW_NODES[2]!);
    });
    expect(onOpenFilePeek).toHaveBeenCalledWith('alpha', 'docs/a.md');
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('↓ on selected skill node selects first reference file', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[0]!);
    });
    act(() => {
      result.current.onKeyDown(makeKeyboardEvent('ArrowDown'));
    });
    expect(result.current.selectedId).toBe('file:docs/a.md');
  });

  it('↑ on selected file node selects parent skill', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[2]!);
    });
    act(() => {
      result.current.onKeyDown(makeKeyboardEvent('ArrowUp'));
    });
    expect(result.current.selectedId).toBe('skill:alpha');
  });

  it('→ on a skill node moves to next sibling skill (alphabetical)', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[0]!);
    });
    act(() => {
      result.current.onKeyDown(makeKeyboardEvent('ArrowRight'));
    });
    expect(result.current.selectedId).toBe('skill:beta');
  });

  it('→ on the last skill wraps to the first sibling skill', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[1]!);
    });
    act(() => {
      result.current.onKeyDown(makeKeyboardEvent('ArrowRight'));
    });
    expect(result.current.selectedId).toBe('skill:alpha');
  });

  it('← on the first skill wraps to the last sibling skill', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[0]!);
    });
    act(() => {
      result.current.onKeyDown(makeKeyboardEvent('ArrowLeft'));
    });
    expect(result.current.selectedId).toBe('skill:beta');
  });

  it('Enter on selected skill → router.push to detail page', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[0]!);
    });
    act(() => {
      result.current.onKeyDown(makeKeyboardEvent('Enter'));
    });
    expect(mockPush).toHaveBeenCalledWith('/workspace/skills/alpha');
  });

  it('Enter on selected file → onOpenFilePeek with parent slug + path', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[2]!);
    });
    act(() => {
      result.current.onKeyDown(makeKeyboardEvent('Enter'));
    });
    expect(onOpenFilePeek).toHaveBeenCalledWith('alpha', 'docs/a.md');
  });

  it('Esc clears selectedId', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[0]!);
    });
    expect(result.current.selectedId).toBe('skill:alpha');
    act(() => {
      result.current.onKeyDown(makeKeyboardEvent('Escape'));
    });
    expect(result.current.selectedId).toBeNull();
  });

  it('clearSelection() exposes Esc behavior imperatively', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[0]!);
    });
    act(() => {
      result.current.clearSelection();
    });
    expect(result.current.selectedId).toBeNull();
  });

  it('unhandled key (e.g. "a") does NOT preventDefault and leaves selection intact', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[0]!);
    });
    const event = makeKeyboardEvent('a');
    act(() => {
      result.current.onKeyDown(event);
    });
    expect(event.preventDefault).not.toHaveBeenCalled();
    expect(result.current.selectedId).toBe('skill:alpha');
  });

  it('arrow key with no selection is a safe no-op (does not throw)', () => {
    const { result } = setup();
    expect(() => {
      act(() => {
        result.current.onKeyDown(makeKeyboardEvent('ArrowDown'));
      });
    }).not.toThrow();
    expect(result.current.selectedId).toBeNull();
  });

  it('handled key (ArrowDown on a selected skill) calls preventDefault', () => {
    const { result } = setup();
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), FLOW_NODES[0]!);
    });
    const event = makeKeyboardEvent('ArrowDown');
    act(() => {
      result.current.onKeyDown(event);
    });
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it('Enter on file with no parentSkillSlugs is a safe no-op (does not call peek)', () => {
    const orphan: Node<FlowNodeData> = {
      id: 'file:orphan/x.md',
      type: 'file',
      position: { x: 0, y: 0 },
      data: { label: 'x.md', kind: 'file', path: 'orphan/x.md' },
    };
    const { result } = renderHook(() =>
      useGraphKeyboardNav({
        flowNodes: [...FLOW_NODES, orphan],
        flowEdges: FLOW_EDGES,
        workspaceSlug: 'workspace',
        onOpenFilePeek,
      }),
    );
    act(() => {
      result.current.onNodeClick(makeMouseEvent(), orphan);
    });
    act(() => {
      result.current.onKeyDown(makeKeyboardEvent('Enter'));
    });
    expect(onOpenFilePeek).not.toHaveBeenCalled();
  });
});
