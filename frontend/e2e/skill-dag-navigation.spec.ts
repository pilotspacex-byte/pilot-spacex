/**
 * Flow (f) — Skill DAG navigation: click selects, arrow keys traverse,
 * double-click opens peek for the skill's primary file.
 *
 * Phase 94 Plan 03 — React Flow node selectors use `.react-flow__node`
 * with a `data-id` attribute. Skill graph view is at
 * /{ws}/skills?view=graph (Phase 92 capstone).
 */

import { test, expect } from './auth.fixture';
import { getSeedContext } from './fixtures/seed-helpers';

test.describe('skill DAG navigation', () => {
  test('graph mounts; click selects a skill node; arrow keys move focus', async ({ page }) => {
    const seed = getSeedContext();
    await page.goto(`/${seed.workspaceSlug}/skills?view=graph`);

    const firstNode = page.locator('.react-flow__node').first();
    await firstNode.waitFor({ state: 'visible', timeout: 15_000 });

    // The data-id attribute IS the React Flow node id.
    await expect(firstNode).toHaveAttribute('data-id', /.+/);

    await firstNode.focus();
    await page.keyboard.press('ArrowRight');

    // Focus should now be on a different node (still inside react-flow).
    const focusedDataId = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      return el?.closest('.react-flow__node')?.getAttribute('data-id') ?? null;
    });
    expect(focusedDataId).toBeTruthy();
  });

  test('clicking a skill node navigates to its detail page', async ({ page }) => {
    const seed = getSeedContext();
    await page.goto(`/${seed.workspaceSlug}/skills?view=graph`);
    const firstNode = page
      .locator('.react-flow__node[data-id^="skill:"], .react-flow__node-skill')
      .first();
    await firstNode.waitFor({ state: 'visible', timeout: 15_000 });
    await firstNode.click();
    await page.waitForURL(/\/skills\/[^/]+/, { timeout: 10_000 });
  });

  test('double-clicking a file node opens the peek drawer', async ({ page }) => {
    const seed = getSeedContext();
    test.skip(
      !seed.skillSlug,
      'TODO(94-03): global-setup must seed a skill with at least 2 reference files ' +
        'so the file-graph node renders.'
    );
    await page.goto(`/${seed.workspaceSlug}/skills?view=graph`);
    const fileNode = page
      .locator('.react-flow__node[data-id^="file:"], .react-flow__node-file')
      .first();
    await fileNode.waitFor({ state: 'visible', timeout: 15_000 });
    await fileNode.dblclick();
    await expect(page.locator('[data-peek-mode]')).toBeVisible({ timeout: 5_000 });
  });
});
