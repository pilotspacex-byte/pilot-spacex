/**
 * layoutSkillGraph tests — Phase 92 Plan 01 Task 2.
 *
 * TDD red→green. Determinism is the load-bearing assertion: d3-force has no
 * seed parameter, so equality is achieved via fixed initial positions + a
 * fixed iteration count. Within a single Node.js process, repeat invocations
 * MUST yield equal positions within 0.001px.
 */
import { describe, expect, it } from 'vitest';
import {
  COLUMN_PITCH,
  ROW_PITCH,
  layoutSkillGraph,
} from '../skill-graph-layout';
import { buildSkillGraph, type SkillGraphNode } from '../skill-graph';
import type { Skill } from '@/types/skill';

function makeSkill(overrides: Partial<Skill> & Pick<Skill, 'name' | 'slug'>): Skill {
  return {
    description: '',
    category: 'general',
    icon: 'Sparkles',
    examples: [],
    feature_module: null,
    reference_files: [],
    updated_at: null,
    ...overrides,
  };
}

function skillNode(slug: string, label = slug): SkillGraphNode {
  return {
    id: `skill:${slug}`,
    kind: 'skill',
    label,
    data: { slug, refCount: 0 },
  };
}

function fileNode(path: string): SkillGraphNode {
  return {
    id: `file:${path}`,
    kind: 'file',
    label: path,
    data: { path, parentSkillSlugs: [] },
  };
}

describe('layoutSkillGraph', () => {
  it('returns empty nodes for empty input', () => {
    expect(layoutSkillGraph({ nodes: [], edges: [] })).toEqual({ nodes: [] });
  });

  it('places a single skill node at (0, 0)', () => {
    const result = layoutSkillGraph({ nodes: [skillNode('alpha')], edges: [] });
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0]?.x).toBeCloseTo(0, 1);
    expect(result.nodes[0]?.y).toBeCloseTo(0, 1);
  });

  it('keeps two skill nodes apart by at least the collide radius', () => {
    const result = layoutSkillGraph({
      nodes: [skillNode('alpha'), skillNode('beta')],
      edges: [],
    });
    const [a, b] = result.nodes;
    const dx = (a?.x ?? 0) - (b?.x ?? 0);
    const dy = (a?.y ?? 0) - (b?.y ?? 0);
    const dist = Math.sqrt(dx * dx + dy * dy);
    // Collide radius is 36 in implementation; pairs converge at >= 2 * radius.
    expect(dist).toBeGreaterThan(36);
  });

  it('places skill rank near x≈0 and file rank near x≈COLUMN_PITCH', () => {
    const result = layoutSkillGraph({
      nodes: [skillNode('alpha'), fileNode('a.md')],
      edges: [
        {
          id: 'edge:skill:alpha->file:a.md',
          source: 'skill:alpha',
          target: 'file:a.md',
          kind: 'references',
        },
      ],
    });
    const skill = result.nodes.find((n) => n.kind === 'skill')!;
    const file = result.nodes.find((n) => n.kind === 'file')!;
    expect(Math.abs(skill.x ?? 0)).toBeLessThanOrEqual(5);
    expect(Math.abs((file.x ?? 0) - COLUMN_PITCH)).toBeLessThanOrEqual(5);
  });

  it('produces distinct y values for three file-rank nodes', () => {
    const result = layoutSkillGraph({
      nodes: [fileNode('a.md'), fileNode('b.md'), fileNode('c.md')],
      edges: [],
    });
    const ys = result.nodes.map((n) => n.y ?? 0);
    expect(new Set(ys.map((y) => Math.round(y))).size).toBe(3);
    for (const n of result.nodes) {
      expect(Math.abs((n.x ?? 0) - COLUMN_PITCH)).toBeLessThanOrEqual(5);
    }
  });

  it('is deterministic: two consecutive calls yield positions within 0.001px', () => {
    const input = {
      nodes: [
        skillNode('alpha'),
        skillNode('beta'),
        fileNode('a.md'),
        fileNode('b.md'),
      ],
      edges: [
        {
          id: 'edge:skill:alpha->file:a.md',
          source: 'skill:alpha',
          target: 'file:a.md',
          kind: 'references' as const,
        },
        {
          id: 'edge:skill:beta->file:b.md',
          source: 'skill:beta',
          target: 'file:b.md',
          kind: 'references' as const,
        },
      ],
    };
    const a = layoutSkillGraph(input);
    const b = layoutSkillGraph(input);
    expect(a.nodes).toHaveLength(b.nodes.length);
    for (let i = 0; i < a.nodes.length; i++) {
      const an = a.nodes[i]!;
      const bn = b.nodes[i]!;
      expect(an.id).toBe(bn.id);
      expect(Math.abs((an.x ?? 0) - (bn.x ?? 0))).toBeLessThan(0.001);
      expect(Math.abs((an.y ?? 0) - (bn.y ?? 0))).toBeLessThan(0.001);
    }
  });

  it('does not mutate input nodes (Object.freeze tolerant; no x/y leaked back)', () => {
    const original = skillNode('alpha');
    const frozen = Object.freeze({ ...original, data: Object.freeze({ ...original.data }) });
    const input = Object.freeze({
      nodes: Object.freeze([frozen]) as unknown as SkillGraphNode[],
      edges: Object.freeze([]) as unknown as never[],
    });
    expect(() => layoutSkillGraph(input)).not.toThrow();
    expect(frozen.x).toBeUndefined();
    expect(frozen.y).toBeUndefined();
  });

  it('exports COLUMN_PITCH = 280 and ROW_PITCH = 88', () => {
    expect(COLUMN_PITCH).toBe(280);
    expect(ROW_PITCH).toBe(88);
  });

  it('preserves input node id order in output', () => {
    const input = {
      nodes: [skillNode('alpha'), skillNode('beta'), fileNode('a.md')],
      edges: [],
    };
    const result = layoutSkillGraph(input);
    expect(result.nodes.map((n) => n.id)).toEqual([
      'skill:alpha',
      'skill:beta',
      'file:a.md',
    ]);
  });

  it('output node array length equals input node array length', () => {
    const input = {
      nodes: [skillNode('alpha'), fileNode('a.md'), fileNode('b.md')],
      edges: [],
    };
    expect(layoutSkillGraph(input).nodes).toHaveLength(input.nodes.length);
  });

  it('skill rank stays close to x=0 even with crowded files', () => {
    const result = layoutSkillGraph({
      nodes: [
        skillNode('only'),
        fileNode('a.md'),
        fileNode('b.md'),
        fileNode('c.md'),
        fileNode('d.md'),
      ],
      edges: [],
    });
    const skill = result.nodes.find((n) => n.kind === 'skill')!;
    expect(Math.abs(skill.x ?? 0)).toBeLessThanOrEqual(5);
  });

  it('file rank stays close to x=COLUMN_PITCH even with many siblings', () => {
    const files = Array.from({ length: 6 }, (_, i) => fileNode(`f${i}.md`));
    const result = layoutSkillGraph({ nodes: files, edges: [] });
    for (const n of result.nodes) {
      expect(Math.abs((n.x ?? 0) - COLUMN_PITCH)).toBeLessThanOrEqual(5);
    }
  });

  it('integrates with buildSkillGraph (planted shared file → 3 nodes, all positioned)', () => {
    const skills: Skill[] = [
      makeSkill({
        name: 'Alpha',
        slug: 'alpha',
        reference_files: ['shared.md'],
      }),
      makeSkill({
        name: 'Beta',
        slug: 'beta',
        reference_files: ['shared.md'],
      }),
    ];
    const built = buildSkillGraph(skills);
    expect(built.cycles).toEqual([]);
    expect(built.nodes).toHaveLength(3);
    const positioned = layoutSkillGraph(built);
    expect(positioned.nodes).toHaveLength(3);
    for (const n of positioned.nodes) {
      expect(typeof n.x).toBe('number');
      expect(typeof n.y).toBe('number');
      expect(Number.isFinite(n.x)).toBe(true);
      expect(Number.isFinite(n.y)).toBe(true);
    }
  });

  it('handles a 25-node perf smoke without throwing', () => {
    const skills: Skill[] = Array.from({ length: 25 }, (_, i) =>
      makeSkill({
        name: `Skill ${String(i).padStart(2, '0')}`,
        slug: `skill-${i}`,
        reference_files: Array.from({ length: 5 }, (_, j) => `dir${i}/file${j}.md`),
      }),
    );
    const built = buildSkillGraph(skills);
    expect(() => layoutSkillGraph(built)).not.toThrow();
    const positioned = layoutSkillGraph(built);
    expect(positioned.nodes.length).toBe(built.nodes.length);
  });
});
