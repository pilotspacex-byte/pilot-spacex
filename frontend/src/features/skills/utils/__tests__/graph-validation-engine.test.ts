/**
 * graph-validation-engine.test.ts — TDD tests for graph validation.
 *
 * Covers: disconnected nodes, missing connections, cycle detection,
 * type mismatches, and valid graph cases.
 */

import { describe, it, expect } from 'vitest';
import type { Node, Edge } from '@xyflow/react';
import { WorkflowNodeType, type WorkflowNodeData } from '../graph-node-types';
import { validateGraph } from '../graph-validation-engine';

// ── Helpers ────────────────────────────────────────────────────────────────

function makeNode(
  id: string,
  nodeType: WorkflowNodeType,
  overrides?: Partial<Node<WorkflowNodeData>>
): Node<WorkflowNodeData> {
  return {
    id,
    type: nodeType,
    position: { x: 0, y: 0 },
    data: { nodeType, label: nodeType, config: {} },
    ...overrides,
  };
}

function makeEdge(
  id: string,
  source: string,
  target: string,
  sourceHandle = 'output:text',
  targetHandle = 'input:any',
  type = 'default'
): Edge {
  return { id, source, target, sourceHandle, targetHandle, type };
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('validateGraph', () => {
  it('returns no errors for an empty graph', () => {
    const errors = validateGraph([], []);
    expect(errors).toEqual([]);
  });

  it('detects a single disconnected node (no edges)', () => {
    const nodes = [makeNode('n1', WorkflowNodeType.Prompt)];
    const errors = validateGraph(nodes, []);
    expect(errors).toContainEqual(
      expect.objectContaining({ type: 'disconnected', nodeId: 'n1' })
    );
  });

  it('detects Input node with no outgoing edge as missing output connection', () => {
    const nodes = [makeNode('n1', WorkflowNodeType.Input)];
    const errors = validateGraph(nodes, []);
    expect(errors).toContainEqual(
      expect.objectContaining({ type: 'missing_output', nodeId: 'n1' })
    );
  });

  it('detects Output node with no incoming edge as missing input connection', () => {
    const nodes = [makeNode('n1', WorkflowNodeType.Output)];
    const errors = validateGraph(nodes, []);
    expect(errors).toContainEqual(
      expect.objectContaining({ type: 'missing_input', nodeId: 'n1' })
    );
  });

  it('detects cycle A->B->C->A (non-loop edges) as circular dependency', () => {
    const nodes = [
      makeNode('a', WorkflowNodeType.Prompt),
      makeNode('b', WorkflowNodeType.Transform),
      makeNode('c', WorkflowNodeType.Skill),
    ];
    const edges = [
      makeEdge('e1', 'a', 'b'),
      makeEdge('e2', 'b', 'c'),
      makeEdge('e3', 'c', 'a'),
    ];
    const errors = validateGraph(nodes, edges);
    expect(errors).toContainEqual(
      expect.objectContaining({ type: 'cycle' })
    );
  });

  it('does NOT produce cycle error for loop edges', () => {
    const nodes = [
      makeNode('a', WorkflowNodeType.Prompt),
      makeNode('b', WorkflowNodeType.Transform),
    ];
    const edges = [
      makeEdge('e1', 'a', 'b', 'output:text', 'input:any', 'default'),
      makeEdge('e2', 'b', 'a', 'output:text', 'input:any', 'loop'),
    ];
    const errors = validateGraph(nodes, edges);
    const cycleErrors = errors.filter((e) => e.type === 'cycle');
    expect(cycleErrors).toHaveLength(0);
  });

  it('detects type mismatch when text handle connects to boolean handle', () => {
    const nodes = [
      makeNode('a', WorkflowNodeType.Prompt),
      makeNode('b', WorkflowNodeType.Condition),
    ];
    // Source outputs text, target expects boolean
    const edges = [makeEdge('e1', 'a', 'b', 'output:text', 'input:boolean')];
    const errors = validateGraph(nodes, edges);
    expect(errors).toContainEqual(
      expect.objectContaining({ type: 'type_mismatch' })
    );
  });

  it('produces no error when text handle connects to any handle', () => {
    const nodes = [
      makeNode('a', WorkflowNodeType.Prompt),
      makeNode('b', WorkflowNodeType.Transform),
    ];
    const edges = [makeEdge('e1', 'a', 'b', 'output:text', 'input:any')];
    const errors = validateGraph(nodes, edges);
    const typeMismatches = errors.filter((e) => e.type === 'type_mismatch');
    expect(typeMismatches).toHaveLength(0);
  });

  it('produces no error when any handle connects to any handle', () => {
    const nodes = [
      makeNode('a', WorkflowNodeType.Input),
      makeNode('b', WorkflowNodeType.Output),
    ];
    const edges = [makeEdge('e1', 'a', 'b', 'output:any', 'input:any')];
    const errors = validateGraph(nodes, edges);
    const typeMismatches = errors.filter((e) => e.type === 'type_mismatch');
    expect(typeMismatches).toHaveLength(0);
  });

  it('produces no errors for a valid linear graph (Input->Prompt->Output)', () => {
    const nodes = [
      makeNode('i', WorkflowNodeType.Input),
      makeNode('p', WorkflowNodeType.Prompt),
      makeNode('o', WorkflowNodeType.Output),
    ];
    const edges = [
      makeEdge('e1', 'i', 'p', 'output:any', 'input:any'),
      makeEdge('e2', 'p', 'o', 'output:text', 'input:any'),
    ];
    const errors = validateGraph(nodes, edges);
    expect(errors).toEqual([]);
  });

  it('produces no errors for Condition node with both branches connected', () => {
    const nodes = [
      makeNode('i', WorkflowNodeType.Input),
      makeNode('c', WorkflowNodeType.Condition),
      makeNode('t', WorkflowNodeType.Prompt),
      makeNode('f', WorkflowNodeType.Prompt),
      makeNode('o1', WorkflowNodeType.Output),
      makeNode('o2', WorkflowNodeType.Output),
    ];
    const edges = [
      makeEdge('e1', 'i', 'c', 'output:any', 'input:any'),
      makeEdge('e2', 'c', 't', 'output:boolean:true', 'input:any'),
      makeEdge('e3', 'c', 'f', 'output:boolean:false', 'input:any'),
      makeEdge('e4', 't', 'o1', 'output:text', 'input:any'),
      makeEdge('e5', 'f', 'o2', 'output:text', 'input:any'),
    ];
    const errors = validateGraph(nodes, edges);
    expect(errors).toEqual([]);
  });
});
