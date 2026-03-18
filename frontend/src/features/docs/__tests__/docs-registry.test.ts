import { describe, it, expect } from 'vitest';
import { docsNavigation, docsBySlug, defaultDocSlug } from '../lib/docs-registry';

describe('docs-registry', () => {
  it('should have at least one navigation group', () => {
    expect(docsNavigation.length).toBeGreaterThan(0);
  });

  it('should have unique slugs across all groups', () => {
    const slugs = docsNavigation.flatMap((g) => g.items.map((i) => i.slug));
    const uniqueSlugs = new Set(slugs);
    expect(uniqueSlugs.size).toBe(slugs.length);
  });

  it('should populate docsBySlug map from navigation', () => {
    const totalDocs = docsNavigation.reduce((sum, g) => sum + g.items.length, 0);
    expect(docsBySlug.size).toBe(totalDocs);
  });

  it('should have a valid default doc slug', () => {
    expect(docsBySlug.has(defaultDocSlug)).toBe(true);
  });

  it('each doc entry should have required fields', () => {
    for (const [slug, doc] of docsBySlug) {
      expect(slug).toBeTruthy();
      expect(doc.title).toBeTruthy();
      expect(doc.description).toBeTruthy();
      expect(doc.file).toBeTruthy();
    }
  });
});
