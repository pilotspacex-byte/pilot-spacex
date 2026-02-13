/**
 * TDD red-phase tests for CodeBlockExtension mermaid preview integration.
 *
 * Tests verify that CodeBlockExtension detects `language: 'mermaid'`
 * and renders preview above source with a toggle button.
 *
 * Spec ref: FR-004 (live preview panel alongside source editor)
 *
 * These tests define the expected behavior for the enhanced CodeBlock.
 * The enhancement does not exist yet — all tests are expected to fail (red phase).
 *
 * @module pm-blocks/__tests__/CodeBlockPreview.test
 */
import { describe, it, expect } from 'vitest';

// These imports will fail until the enhancement is implemented
import { getDefaultCommands, filterCommands } from '../../slash-command-items';

// ── Slash command integration (verifiable now) ─────────────────────────
describe('diagram slash command integration', () => {
  it('includes diagram command in default commands', () => {
    const commands = getDefaultCommands();
    const diagramCmd = commands.find((c) => c.name === 'diagram');
    expect(diagramCmd).toBeDefined();
  });

  it('diagram command has correct metadata', () => {
    const commands = getDefaultCommands();
    const diagramCmd = commands.find((c) => c.name === 'diagram')!;
    expect(diagramCmd.label).toBe('Diagram');
    expect(diagramCmd.description).toBe('Insert a Mermaid diagram');
    expect(diagramCmd.icon).toBe('GitBranch');
    expect(diagramCmd.group).toBe('blocks');
  });

  it('diagram command has comprehensive keywords', () => {
    const commands = getDefaultCommands();
    const diagramCmd = commands.find((c) => c.name === 'diagram')!;
    expect(diagramCmd.keywords).toContain('mermaid');
    expect(diagramCmd.keywords).toContain('flowchart');
    expect(diagramCmd.keywords).toContain('sequence');
    expect(diagramCmd.keywords).toContain('gantt');
    expect(diagramCmd.keywords).toContain('class');
    expect(diagramCmd.keywords).toContain('er');
    expect(diagramCmd.keywords).toContain('diagram');
    expect(diagramCmd.keywords).toContain('chart');
  });

  it('filterCommands finds diagram via "mermaid" keyword', () => {
    const commands = getDefaultCommands();
    const results = filterCommands(commands, 'mermaid');
    expect(results).toHaveLength(1);
    expect(results[0]!.name).toBe('diagram');
  });

  it('filterCommands finds diagram via "flowchart" keyword', () => {
    const commands = getDefaultCommands();
    const results = filterCommands(commands, 'flowchart');
    expect(results).toHaveLength(1);
    expect(results[0]!.name).toBe('diagram');
  });

  it('filterCommands finds diagram via partial "diag" query', () => {
    const commands = getDefaultCommands();
    const results = filterCommands(commands, 'diag');
    expect(results.length).toBeGreaterThanOrEqual(1);
    expect(results.some((c) => c.name === 'diagram')).toBe(true);
  });

  it('diagram command has execute function', () => {
    const commands = getDefaultCommands();
    const diagramCmd = commands.find((c) => c.name === 'diagram')!;
    expect(typeof diagramCmd.execute).toBe('function');
  });
});

// ── FR-004: CodeBlock preview behavior (red phase) ─────────────────────
// These tests define the expected API for the enhanced CodeBlockExtension.
// They will fail until T009 (Enhance CodeBlockExtension) is implemented.
describe('FR-004: CodeBlock mermaid detection', () => {
  it.todo('detects language: "mermaid" in code block attributes');
  it.todo('renders MermaidPreview component above source when language is mermaid');
  it.todo('does not render MermaidPreview for non-mermaid code blocks');
  it.todo('provides toggle button to switch between source and preview');
  it.todo('toggle button shows "Source" label when preview is active');
  it.todo('toggle button shows "Preview" label when source is active');
  it.todo('defaults to showing both source and preview (split view)');
  it.todo('passes code block content to MermaidPreview as code prop');
  it.todo('passes current theme to MermaidPreview as theme prop');
});
