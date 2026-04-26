/**
 * a11y.ts — shared axe-core scan helper for accessibility.spec.ts.
 *
 * Phase 94 Plan 01 Task 3 — extracts the route-scan boilerplate into a
 * reusable fixture so the chat-first capstone surfaces (chat / skills /
 * topics / launchpad / peek-open / proposal-open) can each be scanned
 * with one line of test code.
 *
 * The helper mirrors the existing `runAccessibilityScan` in
 * accessibility.spec.ts (WCAG 2.2 AA tag set + critical/serious filter)
 * but accepts:
 *   - `excludeSelectors`: CSS selectors to exclude (e.g. third-party
 *     widgets the team explicitly opts out of).
 *   - `waitFor`: a selector to wait for before scanning, used to gate
 *     the scan until a dialog/drawer has finished mounting.
 *
 * Why open-state variants matter: Radix Dialog / Popover / Tooltip
 * portal their content outside the React tree at mount time, which means
 * you can ship correct aria attrs on the trigger and STILL ship a
 * violation on the portaled body. Scanning the route before opening
 * the dialog misses these. The `waitFor` arg is how callers say
 * "navigate to ?peek=note:abc, wait for [role=dialog], THEN scan".
 */

import { expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import type { AxeResults } from 'axe-core';

type AxeViolation = AxeResults['violations'][number];

/**
 * WCAG 2.2 AA tags — keep in sync with accessibility.spec.ts wcagTags.
 */
export const WCAG_TAGS = [
  'wcag2a',
  'wcag2aa',
  'wcag21a',
  'wcag21aa',
  'wcag22aa',
  'best-practice',
];

/** Critical + serious violations are gating; minor/moderate are advisory. */
export const CRITICAL_IMPACTS = ['critical', 'serious'] as const;

export interface ScanOptions {
  /** CSS selectors to exclude from the axe scan (third-party widgets, etc.). */
  excludeSelectors?: string[];
  /**
   * CSS selector to wait for before scanning. Use for dialogs/drawers
   * that mount asynchronously after the URL change.
   */
  waitFor?: string;
  /** Optional extra tags to include (e.g. 'cat.aria', 'cat.color'). */
  withTags?: string[];
}

export interface ScanResult {
  /** All violations returned by axe-core. */
  violations: AxeViolation[];
  /** Subset filtered to critical / serious impacts (gating). */
  criticalViolations: AxeViolation[];
}

/**
 * Format a single violation for console output. Matches accessibility.spec.ts.
 */
function formatViolation(violation: AxeViolation): string {
  const nodeDetails = violation.nodes
    .slice(0, 3)
    .map(
      (node, idx) =>
        `  ${idx + 1}. ${node.html.substring(0, 100)}${
          node.html.length > 100 ? '...' : ''
        }\n     Fix: ${node.failureSummary || 'See help URL'}`,
    )
    .join('\n');

  return `
[${violation.impact?.toUpperCase() || 'UNKNOWN'}] ${violation.id}
Description: ${violation.description}
Help: ${violation.helpUrl}
Affected elements (first 3):
${nodeDetails}
`;
}

/**
 * Navigate to `url`, optionally wait for a selector to appear, then run
 * an axe-core scan with WCAG 2.2 AA tags. Returns both the full
 * violation list and the critical/serious-filtered subset.
 *
 * The function does NOT assert internally — the caller decides how
 * strict to be (e.g. expect(criticalViolations).toHaveLength(0)).
 */
export async function scanRouteForA11y(
  page: Page,
  url: string,
  opts: ScanOptions = {},
): Promise<ScanResult> {
  await page.goto(url);
  await page.waitForLoadState('networkidle');

  if (opts.waitFor) {
    await page.waitForSelector(opts.waitFor, { state: 'visible', timeout: 5_000 });
  }

  // Allow late content render (animations, lazy-loaded panels) to settle
  // before snapshotting the DOM. 300ms mirrors the existing spec.
  await page.waitForTimeout(300);

  let builder = new AxeBuilder({ page }).withTags([
    ...WCAG_TAGS,
    ...(opts.withTags ?? []),
  ]);

  // Exclude data-a11y-skip elements by convention + caller-provided extras.
  builder = builder.exclude('[data-a11y-skip]');
  for (const selector of opts.excludeSelectors ?? []) {
    builder = builder.exclude(selector);
  }

  const results = await builder.analyze();

  // Surface non-critical issues to the test log so reviewers see them
  // even when the assertion passes. Skip if no violations.
  if (results.violations.length > 0) {
    // eslint-disable-next-line no-console
    console.log(`\n=== Accessibility Violations on ${url} ===`);
    for (const v of results.violations) {
      // eslint-disable-next-line no-console
      console.log(formatViolation(v));
    }
  }

  const criticalViolations = results.violations.filter((v) =>
    (CRITICAL_IMPACTS as readonly string[]).includes(v.impact ?? ''),
  );

  return { violations: results.violations, criticalViolations };
}

/**
 * Convenience assertion: zero critical/serious violations on `url`.
 * Wraps scanRouteForA11y + an `expect(...).toHaveLength(0)` so callers
 * can write a single-line test body.
 */
export async function expectNoCriticalA11yViolations(
  page: Page,
  url: string,
  opts: ScanOptions = {},
): Promise<void> {
  const { criticalViolations } = await scanRouteForA11y(page, url, opts);
  const summary = criticalViolations
    .map((v) => `- [${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} instances)`)
    .join('\n');
  expect(
    criticalViolations,
    `Critical accessibility violations found on ${url}:\n${summary}`,
  ).toHaveLength(0);
}
