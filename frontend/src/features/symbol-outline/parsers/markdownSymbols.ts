import { PM_BLOCK_REGEX } from '@/features/editor/markers/pmBlockMarkers';
import type { DocumentSymbol } from '../types';

/** Matches markdown headings: `# Title`, `## Section`, etc. */
const HEADING_REGEX = /^(#{1,6})\s+(.+)$/;

/**
 * Parse markdown content into a hierarchical DocumentSymbol tree.
 *
 * Extracts headings (H1-H6) and PM block markers, building a nested
 * hierarchy where H2 nests under preceding H1, H3 under H2, etc.
 * PM blocks nest under the most recent heading.
 *
 * Uses a stack-based approach: maintains a stack of (level, node) pairs
 * and pops until finding a parent with a lower level.
 */
export function parseMarkdownSymbols(content: string): DocumentSymbol[] {
  if (!content.trim()) return [];

  const lines = content.split('\n');
  const roots: DocumentSymbol[] = [];

  // Stack tracks the nesting path: each entry is [level, symbol]
  const stack: [number, DocumentSymbol][] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]!;
    const lineNumber = i + 1; // 1-based

    // Check for heading
    const headingMatch = HEADING_REGEX.exec(line);
    if (headingMatch) {
      const level = headingMatch[1]!.length;
      const name = headingMatch[2]!.trim();

      const symbol: DocumentSymbol = {
        name,
        kind: 'heading',
        line: lineNumber,
        level,
        children: [],
      };

      // Pop stack until we find a parent with lower level
      while (stack.length > 0 && stack[stack.length - 1]![0] >= level) {
        stack.pop();
      }

      if (stack.length === 0) {
        // Top-level symbol
        roots.push(symbol);
      } else {
        // Nest under parent
        stack[stack.length - 1]![1].children.push(symbol);
      }

      stack.push([level, symbol]);
      continue;
    }

    // Check for PM block opening
    const pmMatch = PM_BLOCK_REGEX.exec(line);
    if (pmMatch) {
      const blockType = pmMatch[1]!;

      const symbol: DocumentSymbol = {
        name: blockType,
        kind: 'pm-block',
        line: lineNumber,
        level: 0,
        children: [],
      };

      // Nest under most recent heading, or add to roots
      if (stack.length > 0) {
        stack[stack.length - 1]![1].children.push(symbol);
      } else {
        roots.push(symbol);
      }

      // Skip past the PM block content until closing backtick fence
      i++;
      while (i < lines.length && lines[i] !== '```') {
        i++;
      }
      // i now points at closing fence (or past end); loop increment advances past it
    }
  }

  return roots;
}
