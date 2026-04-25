/**
 * Deterministic layered + d3-force layout for the skill DAG viewer.
 *
 * Phase 92 Plan 01 Task 2.
 *
 * Design (per 92-UI-SPEC §Component Dimensions + Design-Debt #8):
 *  - Two ranks: skills at x=0, files at x=COLUMN_PITCH.
 *  - Initial y = index_within_rank * ROW_PITCH.
 *  - d3-force refines with collision (36px radius) + soft y-pull + strict x-pull.
 *  - Fixed iteration count (100), stopped manually for determinism.
 *
 * d3-force has no seed parameter. Determinism is achieved via fixed initial
 * positions + a fixed iteration count. Cross-browser FP variance is acceptable
 * per 92-UI-SPEC Design-Debt #8 — any visible jitter is well below the 36px
 * collision radius.
 *
 * The helper is pure: it never mutates the input array or the input nodes.
 * Internally it builds a working copy carrying the d3-force scratch fields
 * (vx/vy/__rankX/__rankY), then projects clean SkillGraphNode shapes back out.
 */
import { forceCollide, forceSimulation, forceX, forceY } from 'd3-force';
import type { SkillGraphEdge, SkillGraphNode } from './skill-graph';

export const COLUMN_PITCH = 280;
export const ROW_PITCH = 88;

const COLLIDE_RADIUS = 36;
const ITERATIONS = 100;
const X_STRENGTH = 1.0;
const Y_STRENGTH = 0.3;
const ALPHA_DECAY = 0.0228;

interface SimNode {
  id: string;
  __rankX: number;
  __rankY: number;
  x: number;
  y: number;
  vx?: number;
  vy?: number;
}

/**
 * Position a SkillGraphResult-shaped input on a deterministic two-rank grid
 * refined by d3-force collision avoidance.
 *
 * @param input — typically the output of {@link buildSkillGraph}. The function
 *   does NOT mutate this object, its `nodes` array, or any node within.
 * @returns `{ nodes }` where each node is a fresh SkillGraphNode with `x`/`y`
 *   populated. Edges are not transformed; consumers reuse `input.edges` directly.
 */
export function layoutSkillGraph(input: {
  nodes: readonly SkillGraphNode[];
  edges: readonly SkillGraphEdge[];
}): { nodes: SkillGraphNode[] } {
  if (input.nodes.length === 0) {
    return { nodes: [] };
  }

  // Rank assignment: skill→0, file→1. Within-rank order = input order
  // (buildSkillGraph already sorted by name/path, so this preserves the
  // catalog's deterministic sort.).
  let skillCursor = 0;
  let fileCursor = 0;
  const sim: SimNode[] = input.nodes.map((node) => {
    const rank = node.kind === 'skill' ? 0 : 1;
    const within = node.kind === 'skill' ? skillCursor++ : fileCursor++;
    const rx = rank * COLUMN_PITCH;
    const ry = within * ROW_PITCH;
    return {
      id: node.id,
      x: rx,
      y: ry,
      __rankX: rx,
      __rankY: ry,
    };
  });

  const simulation = forceSimulation<SimNode>(sim)
    .force('collide', forceCollide<SimNode>(COLLIDE_RADIUS))
    .force('y', forceY<SimNode>((d) => d.__rankY).strength(Y_STRENGTH))
    .force('x', forceX<SimNode>((d) => d.__rankX).strength(X_STRENGTH))
    .alphaDecay(ALPHA_DECAY)
    .stop();

  for (let i = 0; i < ITERATIONS; i++) simulation.tick();

  // Project sim positions back into fresh SkillGraphNode objects, preserving
  // input order. Round to 0.01px so determinism assertions are stable.
  const out: SkillGraphNode[] = input.nodes.map((node, idx) => {
    const s = sim[idx];
    return {
      ...node,
      data: { ...node.data },
      x: Math.round((s?.x ?? 0) * 100) / 100,
      y: Math.round((s?.y ?? 0) * 100) / 100,
    };
  });

  return { nodes: out };
}
