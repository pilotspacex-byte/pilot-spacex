/**
 * Pure graph builder for the skill DAG viewer (Phase 92 Plan 01).
 *
 * Consumed by Plan 92-02's <SkillGraphView /> via the data hook layer.
 * The contract is intentionally unit-testable — no DOM, no React, no
 * React Flow imports.
 *
 * v1 emits a bipartite skill→file DAG. Cross-skill edges and cross-file
 * edges are deferred (see 92-CONTEXT.md §Deferred); the cycles[] return
 * slot is preserved as future-proofing and is always empty in v1.
 *
 * Determinism contract:
 *   - skill nodes ordered alphabetically by name (ties broken by slug)
 *   - file nodes ordered alphabetically by path
 *   - edges ordered by (skill order, alphabetical refPath within a skill)
 *   - same input array → identical output (modulo Object.freeze)
 */
import type { Skill } from '@/types/skill';

export interface SkillGraphNode {
  /** `skill:<slug>` for skill nodes, `file:<path>` for file nodes. */
  id: string;
  kind: 'skill' | 'file';
  /** Display label — skill.name for skill nodes, basename(path) for file nodes. */
  label: string;
  data: {
    /** Present on skill nodes — the original skill slug. */
    slug?: string;
    /** Present on file nodes — the full reference file path. */
    path?: string;
    /** Present on skill nodes — number of meaningful reference_files entries. */
    refCount?: number;
    /** Present on file nodes — sorted slugs of skills referencing this path. */
    parentSkillSlugs?: string[];
  };
  /** Populated by `layoutSkillGraph` (Task 2); undefined on the builder output. */
  x?: number;
  y?: number;
}

export interface SkillGraphEdge {
  /** `edge:skill:<slug>->file:<path>`. */
  id: string;
  source: string;
  target: string;
  kind: 'references';
}

export interface SkillGraphResult {
  nodes: SkillGraphNode[];
  edges: SkillGraphEdge[];
  /** Always [] in v1; reserved for future cross-skill/cross-file edges. */
  cycles: string[][];
}

function basename(p: string): string {
  const segments = p.split('/').filter(Boolean);
  const last = segments[segments.length - 1];
  return last ?? p;
}

function isMeaningfulPath(p: unknown): p is string {
  return typeof p === 'string' && p.trim().length > 0;
}

/**
 * Build a bipartite skill→file graph from a Skill[] catalog.
 *
 * @param skills — typically the result of `useSkillCatalog()`. The function
 *   does NOT mutate this array or any element; `Object.freeze`d input is safe.
 * @returns deterministic `{ nodes, edges, cycles }` shaped per the contract above.
 */
export function buildSkillGraph(skills: readonly Skill[]): SkillGraphResult {
  if (skills.length === 0) {
    return { nodes: [], edges: [], cycles: [] };
  }

  // Sort skills alphabetically by name, ties by slug — stable + deterministic.
  // Spread first so the input array is never mutated.
  const sortedSkills = [...skills].sort(
    (a, b) => a.name.localeCompare(b.name) || a.slug.localeCompare(b.slug),
  );

  // Collect unique file paths and their parent-skill slugs.
  const fileToParents = new Map<string, Set<string>>();
  for (const skill of sortedSkills) {
    const seenWithinSkill = new Set<string>();
    for (const raw of skill.reference_files) {
      if (!isMeaningfulPath(raw)) continue;
      if (seenWithinSkill.has(raw)) continue; // dedup duplicates within one skill
      seenWithinSkill.add(raw);
      let bag = fileToParents.get(raw);
      if (!bag) {
        bag = new Set<string>();
        fileToParents.set(raw, bag);
      }
      bag.add(skill.slug);
    }
  }

  const skillNodes: SkillGraphNode[] = sortedSkills.map((skill) => ({
    id: `skill:${skill.slug}`,
    kind: 'skill',
    label: skill.name,
    data: {
      slug: skill.slug,
      refCount: skill.reference_files.filter(isMeaningfulPath).length,
    },
  }));

  const filePaths = [...fileToParents.keys()].sort((a, b) => a.localeCompare(b));
  const fileNodes: SkillGraphNode[] = filePaths.map((path) => ({
    id: `file:${path}`,
    kind: 'file',
    label: basename(path),
    data: {
      path,
      parentSkillSlugs: [...(fileToParents.get(path) ?? [])].sort((a, b) =>
        a.localeCompare(b),
      ),
    },
  }));

  const edges: SkillGraphEdge[] = [];
  for (const skill of sortedSkills) {
    const seen = new Set<string>();
    const sortedRefs = [...skill.reference_files]
      .filter(isMeaningfulPath)
      .sort((a, b) => a.localeCompare(b));
    for (const path of sortedRefs) {
      if (seen.has(path)) continue;
      seen.add(path);
      edges.push({
        id: `edge:skill:${skill.slug}->file:${path}`,
        source: `skill:${skill.slug}`,
        target: `file:${path}`,
        kind: 'references',
      });
    }
  }

  return { nodes: [...skillNodes, ...fileNodes], edges, cycles: [] };
}
