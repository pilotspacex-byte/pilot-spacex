/**
 * Tests for SkillGraphNode + FileGraphNode (Phase 92 Plan 02 Task 2).
 *
 * Custom React Flow node components. Tests verify:
 *  - default geometry (56px skill / 40px file circles)
 *  - data-selected="true" toggle when `selected` prop is true
 *  - aria-label copy verbatim per UI-SPEC §Surface 2
 *  - singular/plural rules for `{N} ref` and "and N other skill(s)"
 *  - Lucide icon dispatch by extension (file node)
 *  - expanded preview content (skill name + `{N} refs` JBM meta)
 */

import * as React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import type { NodeProps } from '@xyflow/react';

// ── Mock @xyflow/react Handle so we don't need a ReactFlowProvider ──────────

vi.mock('@xyflow/react', () => ({
  Handle: ({ type }: { type: string }) => (
    <div data-testid={`handle-${type}`} />
  ),
  Position: {
    Top: 'top',
    Right: 'right',
    Bottom: 'bottom',
    Left: 'left',
  },
}));

// Imports must come AFTER mocks.
import { SkillGraphNode } from '../graph-nodes/SkillGraphNode';
import { FileGraphNode } from '../graph-nodes/FileGraphNode';
import type { FlowNodeData } from '../../hooks/useSkillGraphLayout';

// ── Helpers ─────────────────────────────────────────────────────────────────

function makeNodeProps<T>(data: T, selected = false): NodeProps {
  // The custom node only reads `data`, `selected`, and `id`. Cast through
  // unknown so we don't need to satisfy the full React Flow NodeProps shape
  // (which carries 15+ runtime fields irrelevant to rendering).
  return {
    id: 'node-id',
    data,
    selected,
    type: 'skill',
    dragging: false,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    zIndex: 0,
    targetPosition: 'left',
    sourcePosition: 'right',
  } as unknown as NodeProps;
}

const skillData = (overrides: Partial<FlowNodeData> = {}): FlowNodeData => ({
  label: 'Repository',
  kind: 'skill',
  slug: 'repository',
  refCount: 3,
  ...overrides,
});

const fileData = (overrides: Partial<FlowNodeData> = {}): FlowNodeData => ({
  label: 'architecture.md',
  kind: 'file',
  path: 'docs/architecture.md',
  parentSkillSlugs: ['repository'],
  ...overrides,
});

// ── SkillGraphNode ─────────────────────────────────────────────────────────

describe('SkillGraphNode', () => {
  it('renders a 56px circle when not selected', () => {
    const { container } = render(
      <SkillGraphNode {...makeNodeProps(skillData(), false)} />,
    );
    const inner = container.querySelector('[data-skill-node-inner]');
    expect(inner).toBeTruthy();
    // Tailwind class h-14 (56px) on the collapsed inner
    expect(inner?.className).toMatch(/h-14|w-14/);
  });

  it('aria-label includes skill name and reference count', () => {
    render(<SkillGraphNode {...makeNodeProps(skillData({ refCount: 3 }), false)} />);
    expect(
      screen.getByLabelText(
        /Skill: Repository, 3 reference files\. Press Enter to expand\./i,
      ),
    ).toBeInTheDocument();
  });

  it('uses singular copy "1 reference file" when refCount === 1', () => {
    render(<SkillGraphNode {...makeNodeProps(skillData({ refCount: 1 }), false)} />);
    expect(
      screen.getByLabelText(
        /Skill: Repository, 1 reference file\. Press Enter to expand\./i,
      ),
    ).toBeInTheDocument();
  });

  it('renders a Lucide icon (svg with aria-hidden)', () => {
    const { container } = render(
      <SkillGraphNode {...makeNodeProps(skillData(), false)} />,
    );
    const svg = container.querySelector('svg[aria-hidden="true"]');
    expect(svg).toBeTruthy();
  });

  it('stamps data-selected="true" when selected prop is true', () => {
    const { container } = render(
      <SkillGraphNode {...makeNodeProps(skillData(), true)} />,
    );
    expect(
      container.querySelector('[data-skill-node-inner][data-selected="true"]'),
    ).toBeTruthy();
  });

  it('expanded mode shows skill name and "{N} refs" meta with singular form', () => {
    render(<SkillGraphNode {...makeNodeProps(skillData({ refCount: 1 }), true)} />);
    expect(screen.getByText('Repository')).toBeInTheDocument();
    expect(screen.getByText('1 ref')).toBeInTheDocument();
  });

  it('expanded mode "{N} refs" uses plural form for N !== 1', () => {
    render(<SkillGraphNode {...makeNodeProps(skillData({ refCount: 0 }), true)} />);
    expect(screen.getByText('0 refs')).toBeInTheDocument();
  });
});

// ── FileGraphNode ──────────────────────────────────────────────────────────

describe('FileGraphNode', () => {
  it('renders a 40px circle when not selected', () => {
    const { container } = render(
      <FileGraphNode {...makeNodeProps(fileData(), false)} />,
    );
    const inner = container.querySelector('[data-file-node-inner]');
    expect(inner).toBeTruthy();
    expect(inner?.className).toMatch(/h-10|w-10/);
  });

  it('aria-label uses singular phrasing when only one parent skill', () => {
    render(
      <FileGraphNode
        {...makeNodeProps(fileData({ parentSkillSlugs: ['repository'] }), false)}
      />,
    );
    expect(
      screen.getByLabelText(
        /Reference file: architecture\.md, used by repository\. Press Enter to expand\./i,
      ),
    ).toBeInTheDocument();
  });

  it('aria-label says "and 1 other skill" when 2 parents', () => {
    render(
      <FileGraphNode
        {...makeNodeProps(
          fileData({ parentSkillSlugs: ['alpha', 'beta'] }),
          false,
        )}
      />,
    );
    expect(
      screen.getByLabelText(/used by alpha and 1 other skill\./i),
    ).toBeInTheDocument();
  });

  it('aria-label says "and N other skills" when 3+ parents', () => {
    render(
      <FileGraphNode
        {...makeNodeProps(
          fileData({ parentSkillSlugs: ['alpha', 'beta', 'gamma'] }),
          false,
        )}
      />,
    );
    expect(
      screen.getByLabelText(/used by alpha and 2 other skills\./i),
    ).toBeInTheDocument();
  });

  it('renders the correct icon by extension', () => {
    const cases: Array<[string, string]> = [
      ['docs/notes.md', 'FileText'],
      ['scripts/run.py', 'Code2'],
      ['assets/logo.png', 'Image'],
      ['data/values.csv', 'Table'],
      ['LICENSE', 'File'],
    ];

    for (const [path, expectedIconName] of cases) {
      const { container, unmount } = render(
        <FileGraphNode
          {...makeNodeProps(
            fileData({ path, label: path.split('/').pop() ?? path }),
            false,
          )}
        />,
      );
      // lucide-react attaches `lucide-{name-kebab}` class to the svg.
      const svg = container.querySelector('svg[aria-hidden="true"]');
      expect(svg, `svg present for ${path}`).toBeTruthy();
      const expectedKebab = expectedIconName
        .replace(/([A-Z0-9])/g, '-$1')
        .toLowerCase()
        .replace(/^-/, '');
      expect(
        svg!.className.baseVal ?? svg!.getAttribute('class') ?? '',
        `expected lucide-${expectedKebab} class for ${path}`,
      ).toContain(`lucide-${expectedKebab}`);
      unmount();
    }
  });

  it('stamps data-selected="true" when selected prop is true', () => {
    const { container } = render(
      <FileGraphNode {...makeNodeProps(fileData(), true)} />,
    );
    expect(
      container.querySelector('[data-file-node-inner][data-selected="true"]'),
    ).toBeTruthy();
  });

  it('expanded mode shows basename and parent fallback meta', () => {
    render(
      <FileGraphNode
        {...makeNodeProps(
          fileData({ path: 'docs/architecture.md', parentSkillSlugs: ['repository'] }),
          true,
        )}
      />,
    );
    expect(screen.getByText('architecture.md')).toBeInTheDocument();
    expect(screen.getByText(/from repository/i)).toBeInTheDocument();
  });

  it('expanded aria-label includes full path and "Press Escape to collapse"', () => {
    render(
      <FileGraphNode
        {...makeNodeProps(
          fileData({ path: 'docs/architecture.md', parentSkillSlugs: ['repository'] }),
          true,
        )}
      />,
    );
    expect(
      screen.getByLabelText(
        /Reference file: docs\/architecture\.md\. Press Enter to open in peek drawer\. Press Escape to collapse\./i,
      ),
    ).toBeInTheDocument();
  });
});
