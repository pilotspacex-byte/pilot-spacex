import type { ExtendedPMBlockType, PMBlockMarker, PMBlockType } from '../types';
import { getRegisteredBlockTypes } from '../../plugins/registry/PluginRegistry';

/** Matches opening ```pm:type markers. */
export const PM_BLOCK_REGEX = /^```pm:(\w[\w-]*)$/;

/** Matches closing ``` markers (exact line). */
export const PM_BLOCK_CLOSE_REGEX = /^```$/;

/** All valid PM block types. */
export const PM_BLOCK_TYPES: readonly PMBlockType[] = [
  'decision',
  'raci',
  'risk',
  'dependency',
  'timeline',
  'sprint-board',
  'dashboard',
  'form',
  'release-notes',
  'capacity-plan',
] as const;

const PM_BLOCK_TYPE_SET = new Set<string>(PM_BLOCK_TYPES);

/**
 * Check whether a PM block type is valid.
 * Returns true for built-in types AND plugin-registered block types.
 */
export function isValidPMBlockType(type: string): boolean {
  if (PM_BLOCK_TYPE_SET.has(type)) return true;
  return getRegisteredBlockTypes().some((bt) => bt.type === type);
}

/**
 * Parse PM block markers from markdown text.
 *
 * Scans for fenced code blocks with `pm:` language identifiers,
 * extracts the JSON content between markers, and returns structured
 * PMBlockMarker objects with 1-based line numbers.
 *
 * Invalid PM block types are silently skipped.
 * Malformed JSON results in `data: null` with the raw string preserved.
 */
export function parsePMBlockMarkers(text: string): PMBlockMarker[] {
  const lines = text.split('\n');
  const markers: PMBlockMarker[] = [];

  let i = 0;
  while (i < lines.length) {
    const line = lines[i] as string;
    const openMatch = PM_BLOCK_REGEX.exec(line);
    if (openMatch) {
      const type = openMatch[1] as string;
      const startLine = i + 1; // 1-based

      // Validate type is a known PM block type (built-in or plugin-registered)
      if (!isValidPMBlockType(type)) {
        i++;
        continue;
      }

      // Accumulate content until closing ```
      const contentLines: string[] = [];
      i++;
      while (i < lines.length && !PM_BLOCK_CLOSE_REGEX.test(lines[i] as string)) {
        contentLines.push(lines[i] as string);
        i++;
      }

      const endLine = i + 1; // 1-based line of closing ```
      const raw = contentLines.join('\n');

      let data: Record<string, unknown> | null = null;
      if (raw.trim().length > 0) {
        try {
          data = JSON.parse(raw) as Record<string, unknown>;
        } catch {
          data = null;
        }
      }

      markers.push({
        type: type as ExtendedPMBlockType,
        startLine,
        endLine,
        data,
        raw,
      });
    }

    i++;
  }

  return markers;
}
