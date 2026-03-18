/**
 * Shared utilities for markdown heading extraction and slugification.
 *
 * Used by both DocsContent (heading IDs) and TableOfContents (TOC links)
 * to ensure consistent slug generation across components.
 */

export interface TocHeading {
  id: string;
  text: string;
  level: number;
}

/** Generate a URL-safe slug from heading text. */
export function slugifyHeading(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-');
}

/** Extract headings from raw markdown text, tracking code block boundaries. */
export function extractHeadings(markdown: string): TocHeading[] {
  const headings: TocHeading[] = [];
  const lines = markdown.split('\n');
  let activeFence: string | null = null;
  const slugCounts = new Map<string, number>();

  for (const line of lines) {
    const fenceMatch = line.trim().match(/^(`{3,}|~{3,})/);
    if (fenceMatch?.[1]) {
      const marker = fenceMatch[1][0] as string;
      if (activeFence === null) {
        activeFence = marker;
      } else if (marker === activeFence) {
        activeFence = null;
      }
      continue;
    }
    if (activeFence !== null) continue;

    const match = line.match(/^(#{1,4})\s+(.+)$/);
    if (match?.[1] && match[2]) {
      const level = match[1].length;
      const text = match[2].replace(/[`*_~]/g, '').trim();
      const base = slugifyHeading(text);
      const count = slugCounts.get(base) ?? 0;
      slugCounts.set(base, count + 1);
      const id = count === 0 ? base : `${base}-${count}`;
      headings.push({ id, text, level });
    }
  }

  return headings;
}
