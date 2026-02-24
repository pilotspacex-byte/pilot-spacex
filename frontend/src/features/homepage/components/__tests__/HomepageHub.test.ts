/**
 * HomepageHub contextual prompt generation tests.
 *
 * T014: Tests buildContextualPrompts logic for deriving
 * contextual prompts from digest category groups,
 * and fallback to static prompts when no digest data exists.
 */

import { describe, it, expect } from 'vitest';
import { buildContextualPrompts } from '../HomepageHub';
import type { DigestCategoryGroup } from '../../hooks/useWorkspaceDigest';
import type { DigestSuggestion } from '../../types';

// ---------------------------------------------------------------------------
// Helper to create suggestion stubs
// ---------------------------------------------------------------------------

function makeSuggestion(category: DigestSuggestion['category'], id: string): DigestSuggestion {
  return {
    id,
    category,
    title: `Title ${id}`,
    description: `Description ${id}`,
    entityId: `entity-${id}`,
    entityType: 'issue',
    entityIdentifier: `PS-${id}`,
    projectId: null,
    projectName: null,
    actionType: 'navigate',
    actionLabel: 'View',
    actionUrl: `/issues/${id}`,
    relevanceScore: 0.5,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('buildContextualPrompts', () => {
  it('returns fallback prompts when no groups are available', () => {
    const prompts = buildContextualPrompts([]);

    expect(prompts).toEqual([
      'What should I focus on today?',
      'Summarize my in-progress work',
      'Generate my daily standup update',
      'Find stale issues that need attention',
    ]);
  });

  it('generates stale issues prompt with correct count', () => {
    const groups: DigestCategoryGroup[] = [
      {
        category: 'stale_issues',
        items: [makeSuggestion('stale_issues', '1'), makeSuggestion('stale_issues', '2')],
      },
    ];

    const prompts = buildContextualPrompts(groups);
    expect(prompts[0]).toBe('Review 2 stale issues needing attention');
  });

  it('generates singular form for single stale issue', () => {
    const groups: DigestCategoryGroup[] = [
      { category: 'stale_issues', items: [makeSuggestion('stale_issues', '1')] },
    ];

    const prompts = buildContextualPrompts(groups);
    expect(prompts[0]).toBe('Review 1 stale issue needing attention');
  });

  it('generates cycle risk prompt', () => {
    const groups: DigestCategoryGroup[] = [
      { category: 'cycle_risk', items: [makeSuggestion('cycle_risk', '1')] },
    ];

    const prompts = buildContextualPrompts(groups);
    expect(prompts[0]).toBe('Sprint ends soon — prioritize remaining items?');
  });

  it('generates blocked dependencies prompt with plural form', () => {
    const groups: DigestCategoryGroup[] = [
      {
        category: 'blocked_dependencies',
        items: [
          makeSuggestion('blocked_dependencies', '1'),
          makeSuggestion('blocked_dependencies', '2'),
          makeSuggestion('blocked_dependencies', '3'),
        ],
      },
    ];

    const prompts = buildContextualPrompts(groups);
    expect(prompts[0]).toContain('3 items are blocked');
  });

  it('generates singular blocked dependency prompt', () => {
    const groups: DigestCategoryGroup[] = [
      { category: 'blocked_dependencies', items: [makeSuggestion('blocked_dependencies', '1')] },
    ];

    const prompts = buildContextualPrompts(groups);
    expect(prompts[0]).toContain('1 item is blocked');
  });

  it('generates unlinked notes prompt', () => {
    const groups: DigestCategoryGroup[] = [
      {
        category: 'unlinked_notes',
        items: [makeSuggestion('unlinked_notes', '1'), makeSuggestion('unlinked_notes', '2')],
      },
    ];

    const prompts = buildContextualPrompts(groups);
    expect(prompts[0]).toContain('2 notes have extractable issues');
  });

  it('generates overdue items prompt', () => {
    const groups: DigestCategoryGroup[] = [
      { category: 'overdue_items', items: [makeSuggestion('overdue_items', '1')] },
    ];

    const prompts = buildContextualPrompts(groups);
    expect(prompts[0]).toBe('1 overdue item need attention');
  });

  it('generates unassigned priority prompt', () => {
    const groups: DigestCategoryGroup[] = [
      {
        category: 'unassigned_priority',
        items: [
          makeSuggestion('unassigned_priority', '1'),
          makeSuggestion('unassigned_priority', '2'),
        ],
      },
    ];

    const prompts = buildContextualPrompts(groups);
    expect(prompts[0]).toContain('2 priority items are unassigned');
  });

  it('combines multiple categories and pads with fallbacks to reach 4', () => {
    const groups: DigestCategoryGroup[] = [
      { category: 'stale_issues', items: [makeSuggestion('stale_issues', '1')] },
      { category: 'blocked_dependencies', items: [makeSuggestion('blocked_dependencies', '1')] },
    ];

    const prompts = buildContextualPrompts(groups);

    expect(prompts).toHaveLength(4);
    expect(prompts[0]).toContain('stale issue');
    expect(prompts[1]).toContain('blocked');
    // Remaining 2 should be from fallback pool
    expect(typeof prompts[2]).toBe('string');
    expect(typeof prompts[3]).toBe('string');
  });

  it('limits to 4 prompts even with many categories', () => {
    const groups: DigestCategoryGroup[] = [
      { category: 'stale_issues', items: [makeSuggestion('stale_issues', '1')] },
      { category: 'unlinked_notes', items: [makeSuggestion('unlinked_notes', '1')] },
      { category: 'cycle_risk', items: [makeSuggestion('cycle_risk', '1')] },
      { category: 'blocked_dependencies', items: [makeSuggestion('blocked_dependencies', '1')] },
      { category: 'overdue_items', items: [makeSuggestion('overdue_items', '1')] },
    ];

    const prompts = buildContextualPrompts(groups);
    expect(prompts).toHaveLength(4);
  });
});
