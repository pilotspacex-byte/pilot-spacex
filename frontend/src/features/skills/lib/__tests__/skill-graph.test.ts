/**
 * buildSkillGraph tests — Phase 92 Plan 01 Task 1.
 *
 * TDD red→green: assertions cover dedup, sorting, cycles contract, edge format,
 * non-mutation guarantee, and silent-skip of empty paths. The set is intentionally
 * thorough so Plan 92-02 / 92-03 can rely on a frozen contract.
 */
import { describe, expect, it } from 'vitest';
import type { Skill } from '@/types/skill';
import { buildSkillGraph } from '../skill-graph';

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

describe('buildSkillGraph', () => {
  it('returns an empty result for an empty input array', () => {
    expect(buildSkillGraph([])).toEqual({ nodes: [], edges: [], cycles: [] });
  });

  it('emits a single skill node with zero edges when reference_files is empty', () => {
    const result = buildSkillGraph([makeSkill({ name: 'Alpha', slug: 'alpha' })]);
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0]).toMatchObject({
      id: 'skill:alpha',
      kind: 'skill',
      label: 'Alpha',
      data: { slug: 'alpha', refCount: 0 },
    });
    expect(result.edges).toEqual([]);
  });

  it('emits 1 skill + 2 file nodes + 2 edges for a skill with two refs', () => {
    const result = buildSkillGraph([
      makeSkill({
        name: 'Alpha',
        slug: 'alpha',
        reference_files: ['docs/a.md', 'docs/b.md'],
      }),
    ]);
    const skillNodes = result.nodes.filter((n) => n.kind === 'skill');
    const fileNodes = result.nodes.filter((n) => n.kind === 'file');
    expect(skillNodes).toHaveLength(1);
    expect(fileNodes).toHaveLength(2);
    expect(result.edges).toHaveLength(2);
  });

  it('dedupes a file shared across two skills into one file node with sorted parentSkillSlugs and 2 edges', () => {
    const result = buildSkillGraph([
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
    ]);
    const fileNodes = result.nodes.filter((n) => n.kind === 'file');
    expect(fileNodes).toHaveLength(1);
    expect(fileNodes[0]?.data.parentSkillSlugs).toEqual(['alpha', 'beta']);
    expect(result.edges).toHaveLength(2);
  });

  it('orders skill nodes alphabetically by name (Charlie/Alice/Bob → Alice, Bob, Charlie)', () => {
    const result = buildSkillGraph([
      makeSkill({ name: 'Charlie', slug: 'charlie' }),
      makeSkill({ name: 'Alice', slug: 'alice' }),
      makeSkill({ name: 'Bob', slug: 'bob' }),
    ]);
    const skillIds = result.nodes.filter((n) => n.kind === 'skill').map((n) => n.id);
    expect(skillIds).toEqual(['skill:alice', 'skill:bob', 'skill:charlie']);
  });

  it('orders file nodes alphabetically by path (zebra.md, apple.md → apple.md, zebra.md)', () => {
    const result = buildSkillGraph([
      makeSkill({
        name: 'Alpha',
        slug: 'alpha',
        reference_files: ['zebra.md', 'apple.md'],
      }),
    ]);
    const fileIds = result.nodes.filter((n) => n.kind === 'file').map((n) => n.id);
    expect(fileIds).toEqual(['file:apple.md', 'file:zebra.md']);
  });

  it('always returns cycles=[] in v1', () => {
    const result = buildSkillGraph([
      makeSkill({
        name: 'Alpha',
        slug: 'alpha',
        reference_files: ['a.md', 'b.md'],
      }),
      makeSkill({
        name: 'Beta',
        slug: 'beta',
        reference_files: ['a.md'],
      }),
    ]);
    expect(result.cycles).toEqual([]);
  });

  it('refCount on a skill node matches the count of meaningful reference_files entries', () => {
    const result = buildSkillGraph([
      makeSkill({
        name: 'Alpha',
        slug: 'alpha',
        reference_files: ['a.md', 'b.md', 'c.md'],
      }),
    ]);
    const skill = result.nodes.find((n) => n.id === 'skill:alpha')!;
    expect(skill.data.refCount).toBe(3);
  });

  it('silently skips empty / whitespace-only paths (no node, no edge, no throw)', () => {
    const result = buildSkillGraph([
      makeSkill({
        name: 'Alpha',
        slug: 'alpha',
        reference_files: ['', '   ', 'real.md'],
      }),
    ]);
    const fileNodes = result.nodes.filter((n) => n.kind === 'file');
    expect(fileNodes).toHaveLength(1);
    expect(fileNodes[0]?.id).toBe('file:real.md');
    expect(result.edges).toHaveLength(1);
    // refCount counts only meaningful entries
    const skill = result.nodes.find((n) => n.id === 'skill:alpha')!;
    expect(skill.data.refCount).toBe(1);
  });

  it('dedupes duplicate paths within a single skill (one edge, not two)', () => {
    const result = buildSkillGraph([
      makeSkill({
        name: 'Alpha',
        slug: 'alpha',
        reference_files: ['dup.md', 'dup.md'],
      }),
    ]);
    expect(result.edges).toHaveLength(1);
    expect(result.nodes.filter((n) => n.kind === 'file')).toHaveLength(1);
  });

  it('does not mutate the input array or its skill objects (Object.freeze tolerant)', () => {
    const input: ReadonlyArray<Skill> = Object.freeze([
      Object.freeze(
        makeSkill({
          name: 'Alpha',
          slug: 'alpha',
          reference_files: Object.freeze(['b.md', 'a.md']) as unknown as string[],
        }),
      ),
    ]);
    const before = JSON.stringify(input);
    expect(() => buildSkillGraph(input)).not.toThrow();
    const after = JSON.stringify(input);
    expect(after).toBe(before);
  });

  it('emits edge id with exact format edge:skill:<slug>->file:<path>', () => {
    const result = buildSkillGraph([
      makeSkill({
        name: 'Alpha',
        slug: 'alpha',
        reference_files: ['nested/dir/file.md'],
      }),
    ]);
    expect(result.edges[0]).toEqual({
      id: 'edge:skill:alpha->file:nested/dir/file.md',
      source: 'skill:alpha',
      target: 'file:nested/dir/file.md',
      kind: 'references',
    });
  });

  it('emits node ids with exact format skill:<slug> and file:<path>', () => {
    const result = buildSkillGraph([
      makeSkill({
        name: 'Alpha',
        slug: 'alpha-slug',
        reference_files: ['some/path.md'],
      }),
    ]);
    expect(result.nodes.map((n) => n.id).sort()).toEqual([
      'file:some/path.md',
      'skill:alpha-slug',
    ]);
  });

  it('label = skill.name for skill nodes; label = basename(path) for file nodes', () => {
    const result = buildSkillGraph([
      makeSkill({
        name: 'Alpha Skill',
        slug: 'alpha',
        reference_files: ['subdir/architecture.md', 'topfile.md'],
      }),
    ]);
    const skill = result.nodes.find((n) => n.id === 'skill:alpha')!;
    const nestedFile = result.nodes.find(
      (n) => n.id === 'file:subdir/architecture.md',
    )!;
    const topFile = result.nodes.find((n) => n.id === 'file:topfile.md')!;
    expect(skill.label).toBe('Alpha Skill');
    expect(nestedFile.label).toBe('architecture.md');
    expect(topFile.label).toBe('topfile.md');
  });
});
