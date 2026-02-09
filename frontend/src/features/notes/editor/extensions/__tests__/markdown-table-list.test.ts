/**
 * Markdown Table & List Rendering Tests
 *
 * Verifies that markdown tables, bullet lists, and ordered lists
 * are correctly parsed into TipTap nodes when inserted via
 * insertContentAt (the same path used by SSE content_update handlers).
 *
 * Also tests the save/load roundtrip: markdown → JSON (getJSON) → reload
 * (setContent) to ensure tables and lists survive the persistence cycle.
 */
import { describe, it, expect, afterEach } from 'vitest';
import { Editor } from '@tiptap/core';
import type { Content } from '@tiptap/core';
import { createEditorExtensions } from '../createEditorExtensions';

/** Loose JSON node type for test assertions (avoids TipTap's strict union). */
interface JsonNode {
  type: string;
  content?: JsonNode[];
  text?: string;
  attrs?: Record<string, unknown>;
  marks?: Array<{ type: string }>;
}

const extensions = createEditorExtensions({
  placeholder: 'Test editor',
  enableSlashCommands: false,
  enableMentions: false,
});

function createTestEditor(content: string | Content = '') {
  return new Editor({
    extensions,
    content,
  });
}

/** Helper: get editor JSON with loose typing for deep assertions. */
function getJson(ed: Editor): { content?: JsonNode[] } {
  return ed.getJSON() as { content?: JsonNode[] };
}

let editor: Editor | null = null;
let editor2: Editor | null = null;

afterEach(() => {
  editor?.destroy();
  editor = null;
  editor2?.destroy();
  editor2 = null;
});

describe('Markdown Table Rendering', () => {
  it('should parse a markdown table into table nodes', () => {
    const markdown = [
      '| Name | Role |',
      '|------|------|',
      '| Alice | Engineer |',
      '| Bob | Designer |',
    ].join('\n');

    editor = createTestEditor(markdown);
    const json = getJson(editor);

    const tableNode = json.content?.find((n) => n.type === 'table');
    expect(tableNode).toBeDefined();
    expect(tableNode!.content).toBeDefined();
    // Header row + 2 data rows
    expect(tableNode!.content!.length).toBe(3);
  });

  it('should parse table with many columns', () => {
    const markdown = [
      '| Stakeholder | Role | Interest | Input Needed | Review Point |',
      '|-------------|------|----------|-------------|-------------|',
      '| Product Owner | Accountable | Reduce churn | Define tradeoffs | Spec review |',
      '| Tech Lead | Responsible | Security | Validate approach | Pre-plan review |',
    ].join('\n');

    editor = createTestEditor(markdown);
    const json = getJson(editor);

    const tableNode = json.content?.find((n) => n.type === 'table');
    expect(tableNode).toBeDefined();

    // Check header row has 5 cells
    const headerRow = tableNode!.content![0]!;
    expect(headerRow.type).toBe('tableRow');
    expect(headerRow.content!.length).toBe(5);
    // First cell should be tableHeader
    expect(headerRow.content![0]!.type).toBe('tableHeader');
  });

  it('should insert a markdown table via insertContentAt', () => {
    editor = createTestEditor('# Title\n\nSome text.');

    const markdown = ['| A | B |', '|---|---|', '| 1 | 2 |'].join('\n');

    // Simulate SSE content_update: insert at end of document
    const endPos = editor.state.doc.content.size;
    editor.commands.insertContentAt(endPos, markdown);

    const json = getJson(editor);
    const tableNode = json.content?.find((n) => n.type === 'table');
    expect(tableNode).toBeDefined();
  });
});

describe('Markdown Bullet List Rendering', () => {
  it('should parse bullet list into bulletList nodes', () => {
    const markdown = '- Item one\n- Item two\n- Item three';

    editor = createTestEditor(markdown);
    const json = getJson(editor);

    const listNode = json.content?.find((n) => n.type === 'bulletList');
    expect(listNode).toBeDefined();
    expect(listNode!.content!.length).toBe(3);
    expect(listNode!.content![0]!.type).toBe('listItem');
  });

  it('should parse asterisk bullet list', () => {
    const markdown = '* First\n* Second';

    editor = createTestEditor(markdown);
    const json = getJson(editor);

    const listNode = json.content?.find((n) => n.type === 'bulletList');
    expect(listNode).toBeDefined();
    expect(listNode!.content!.length).toBe(2);
  });

  it('should insert bullet list via insertContentAt', () => {
    editor = createTestEditor('# Title');

    const markdown = '- Apple\n- Banana\n- Cherry';
    const endPos = editor.state.doc.content.size;
    editor.commands.insertContentAt(endPos, markdown);

    const json = getJson(editor);
    const listNode = json.content?.find((n) => n.type === 'bulletList');
    expect(listNode).toBeDefined();
    expect(listNode!.content!.length).toBe(3);
  });
});

describe('Markdown Ordered List Rendering', () => {
  it('should parse ordered list into orderedList nodes', () => {
    const markdown = '1. First\n2. Second\n3. Third';

    editor = createTestEditor(markdown);
    const json = getJson(editor);

    const listNode = json.content?.find((n) => n.type === 'orderedList');
    expect(listNode).toBeDefined();
    expect(listNode!.content!.length).toBe(3);
    expect(listNode!.content![0]!.type).toBe('listItem');
  });

  it('should insert ordered list via insertContentAt', () => {
    editor = createTestEditor('# Steps');

    const markdown = '1. Do this\n2. Then that\n3. Done';
    const endPos = editor.state.doc.content.size;
    editor.commands.insertContentAt(endPos, markdown);

    const json = getJson(editor);
    const listNode = json.content?.find((n) => n.type === 'orderedList');
    expect(listNode).toBeDefined();
    expect(listNode!.content!.length).toBe(3);
  });
});

describe('Mixed Markdown Content (SSE simulation)', () => {
  it('should parse a document with headings, tables, and lists', () => {
    const markdown = [
      '# Stakeholders',
      '',
      '| Stakeholder | Role |',
      '|-------------|------|',
      '| Product Owner | Accountable |',
      '| Tech Lead | Responsible |',
      '',
      '## Requirements',
      '',
      '- FR-001: Must allow registration',
      '- FR-002: Must validate email',
      '',
      '## Steps',
      '',
      '1. Sign up',
      '2. Verify email',
      '3. Login',
    ].join('\n');

    editor = createTestEditor(markdown);
    const json = getJson(editor);
    const types = json.content?.map((n) => n.type) ?? [];

    expect(types).toContain('heading');
    expect(types).toContain('table');
    expect(types).toContain('bulletList');
    expect(types).toContain('orderedList');
  });

  it('should handle large SSE markdown payload with tables', () => {
    // Simulate the actual SSE payload format from the bug report
    const markdown = [
      '# Sample Spec: User Authentication System',
      '',
      '**Feature Number**: 001',
      '',
      '---',
      '',
      '## Stakeholders',
      '',
      '| Stakeholder | Role | Interest | Input Needed | Review Point |',
      '|-------------|------|----------|-------------|-------------|',
      '| Product Owner | Accountable for feature | Reduce churn, improve UX | Define priority tradeoffs | Spec review |',
      '| Tech Lead | Responsible for architecture | Security, scalability | Validate technical approach | Pre-plan review |',
      '| End User | Primary beneficiary | Easy, secure access | User testing feedback | Acceptance test |',
      '',
      '## User Scenarios',
      '',
      '### User Story 1 — Sign Up with Email (Priority: P1)',
      '',
      '**Acceptance Scenarios**:',
      '',
      '1. **Given** a visitor on the sign-up page, **When** they enter credentials, **Then** account is created',
      '2. **Given** a visitor enters an already-registered email, **When** they submit, **Then** they see an error',
      '3. **Given** a visitor enters a weak password, **When** they submit, **Then** they see feedback',
    ].join('\n');

    editor = createTestEditor(markdown);
    const json = getJson(editor);
    const types = json.content?.map((n) => n.type) ?? [];

    // Verify table is parsed (not plain text)
    expect(types).toContain('table');

    // Verify ordered list is parsed
    expect(types).toContain('orderedList');

    // Verify the table has correct structure
    const tableNode = json.content?.find((n) => n.type === 'table');
    expect(tableNode).toBeDefined();
    // Header + 3 data rows
    expect(tableNode!.content!.length).toBe(4);
    // 5 columns in header
    expect(tableNode!.content![0]!.content!.length).toBe(5);
  });
});

describe('Save/Load Roundtrip (JSON persistence)', () => {
  it('should preserve table structure through getJSON → setContent cycle', () => {
    const markdown = [
      '| Name | Role |',
      '|------|------|',
      '| Alice | Engineer |',
      '| Bob | Designer |',
    ].join('\n');

    // Step 1: Parse markdown (simulates SSE insert)
    editor = createTestEditor(markdown);
    const savedJson = getJson(editor);

    // Verify table node exists in saved JSON
    const tableInSaved = savedJson.content?.find((n) => n.type === 'table');
    expect(tableInSaved).toBeDefined();
    expect(tableInSaved!.content!.length).toBe(3);

    // Step 2: Reload from saved JSON (simulates page reload)
    editor2 = createTestEditor(savedJson as Content);
    const reloadedJson = getJson(editor2);

    // Verify table survives roundtrip
    const tableInReloaded = reloadedJson.content?.find((n) => n.type === 'table');
    expect(tableInReloaded).toBeDefined();
    expect(tableInReloaded!.content!.length).toBe(3);

    // Verify header cells preserved
    const headerRow = tableInReloaded!.content![0]!;
    expect(headerRow.type).toBe('tableRow');
    expect(headerRow.content![0]!.type).toBe('tableHeader');

    // Verify cell text content preserved
    const firstHeaderCell = headerRow.content![0]!;
    const cellText = firstHeaderCell.content?.[0]?.content?.[0]?.text;
    expect(cellText).toBe('Name');
  });

  it('should preserve bullet list through getJSON → setContent cycle', () => {
    const markdown = '- Alpha\n- Beta\n- Gamma';

    editor = createTestEditor(markdown);
    const savedJson = getJson(editor);

    editor2 = createTestEditor(savedJson as Content);
    const reloadedJson = getJson(editor2);

    const list = reloadedJson.content?.find((n) => n.type === 'bulletList');
    expect(list).toBeDefined();
    expect(list!.content!.length).toBe(3);

    // Verify text content
    const firstItemText = list!.content![0]!.content?.[0]?.content?.[0]?.text;
    expect(firstItemText).toBe('Alpha');
  });

  it('should preserve ordered list through getJSON → setContent cycle', () => {
    const markdown = '1. First\n2. Second\n3. Third';

    editor = createTestEditor(markdown);
    const savedJson = getJson(editor);

    editor2 = createTestEditor(savedJson as Content);
    const reloadedJson = getJson(editor2);

    const list = reloadedJson.content?.find((n) => n.type === 'orderedList');
    expect(list).toBeDefined();
    expect(list!.content!.length).toBe(3);
  });

  it('should preserve mixed content (heading + table + lists) through roundtrip', () => {
    const markdown = [
      '# Team',
      '',
      '| Name | Role |',
      '|------|------|',
      '| Alice | Lead |',
      '',
      '## Tasks',
      '',
      '- Design',
      '- Build',
      '',
      '1. Plan',
      '2. Execute',
    ].join('\n');

    editor = createTestEditor(markdown);
    const savedJson = getJson(editor);

    editor2 = createTestEditor(savedJson as Content);
    const reloadedJson = getJson(editor2);
    const types = reloadedJson.content?.map((n) => n.type) ?? [];

    expect(types).toContain('heading');
    expect(types).toContain('table');
    expect(types).toContain('bulletList');
    expect(types).toContain('orderedList');
  });

  it('should handle insertContentAt followed by getJSON roundtrip', () => {
    // Simulates: existing note → AI appends table via SSE → save → reload
    editor = createTestEditor('# Existing Note\n\nSome content here.');

    // AI inserts a table at the end (SSE content_update path)
    const tableMarkdown = [
      '| Status | Count |',
      '|--------|-------|',
      '| Done | 5 |',
      '| Pending | 3 |',
    ].join('\n');
    const endPos = editor.state.doc.content.size;
    editor.commands.insertContentAt(endPos, tableMarkdown);

    // Save
    const savedJson = getJson(editor);
    const tableInSaved = savedJson.content?.find((n) => n.type === 'table');
    expect(tableInSaved).toBeDefined();

    // Reload
    editor2 = createTestEditor(savedJson as Content);
    const reloadedJson = getJson(editor2);
    const tableInReloaded = reloadedJson.content?.find((n) => n.type === 'table');
    expect(tableInReloaded).toBeDefined();
    expect(tableInReloaded!.content!.length).toBe(3);
  });
});
