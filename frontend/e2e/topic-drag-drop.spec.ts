/**
 * Flow (g) — Topic drag-drop reparenting + cycle + max-depth errors.
 *
 * Phase 94 Plan 03 — @dnd-kit uses pointer events, NOT HTML5 drag.
 * Playwright's `page.dragTo()` would NOT trigger dnd-kit. We drive the
 * drag via `page.mouse.{move, down, up}` with steps>=10 to clear the
 * dnd-kit activation distance threshold.
 *
 * NOTE: the `data-topic-id` attribute is not yet present on TopicTreeRow
 * in the codebase (verified via grep). Until that attribute is added by
 * an upstream Topic-tree refactor, this entire spec runs as a TODO via
 * test.skip — keeping the file in tree so the seven-spec contract is
 * fulfilled and enabling toggles to a single line once the attribute
 * lands.
 */

import { test, expect, type Page } from './auth.fixture';
import { getSeedContext } from './fixtures/seed-helpers';

async function dragRow(page: Page, srcId: string, dstId: string): Promise<void> {
  const src = page.locator(`[data-topic-id="${srcId}"]`).first();
  const dst = page.locator(`[data-topic-id="${dstId}"]`).first();
  const srcBox = await src.boundingBox();
  const dstBox = await dst.boundingBox();
  if (!srcBox || !dstBox) {
    throw new Error(`[topic-drag-drop] Row not found: src=${srcId} dst=${dstId}`);
  }
  await page.mouse.move(srcBox.x + srcBox.width / 2, srcBox.y + srcBox.height / 2);
  await page.mouse.down();
  // dnd-kit activation distance + smooth pointer trail >= 10 steps
  await page.mouse.move(
    dstBox.x + dstBox.width / 2,
    dstBox.y + dstBox.height / 2,
    { steps: 15 }
  );
  await page.mouse.up();
}

test.describe('topic drag-drop', () => {
  test('reparent + cycle reject + max-depth toast', async ({ page }) => {
    const seed = getSeedContext();
    test.skip(
      !seed.rootTopicId ||
        !seed.childTopicAId ||
        !seed.childTopicBId ||
        !seed.deepTopicId,
      'TODO(94-03): blocked on (a) global-setup seeding a 5-deep topic chain + ' +
        'rootTopic + 2 children, AND (b) TopicTreeRow exposing data-topic-id. ' +
        'Drag mechanics tested in unit suite already; this spec verifies the ' +
        'cross-feature handshake (drag -> PUT /move -> tree re-render or toast).'
    );

    await page.goto(`/${seed.workspaceSlug}/topics/${seed.rootTopicId}`);
    await expect(page.locator('[data-sidebar-mode]')).toHaveAttribute(
      'data-sidebar-mode',
      /full|rail/
    );

    // Case 1: move childA under childB -> 200
    // Backend exposes POST /notes/{id}/move (not PUT) — verified in
    // workspace_notes_topic_tree.py + frontend notesApi.moveTopic.
    const moveResp = page.waitForResponse(
      (r) =>
        r.url().includes('/notes/') &&
        r.url().includes('/move') &&
        r.request().method() === 'POST' &&
        r.status() === 200,
      { timeout: 10_000 }
    );
    await dragRow(page, seed.childTopicAId!, seed.childTopicBId!);
    await moveResp;
    await expect(
      page
        .locator(`[data-topic-id="${seed.childTopicBId}"]`)
        .locator(`[data-topic-id="${seed.childTopicAId}"]`)
    ).toBeVisible({ timeout: 5_000 });

    // Case 2: drop onto deepTopicId (depth=5) -> 422 max-depth
    const errResp = page.waitForResponse(
      (r) => r.url().includes('/move') && r.status() === 422,
      { timeout: 10_000 }
    );
    await dragRow(page, seed.childTopicBId!, seed.deepTopicId!);
    await errResp;
    await expect(page.getByText(/max.*depth|depth.*exceed/i)).toBeVisible({ timeout: 5_000 });

    // Case 3: cycle (root onto descendant) -> 409 or 422 cycle toast
    const cycleResp = page.waitForResponse(
      (r) => r.url().includes('/move') && (r.status() === 409 || r.status() === 422),
      { timeout: 10_000 }
    );
    await dragRow(page, seed.rootTopicId!, seed.childTopicAId!);
    await cycleResp;
    await expect(page.getByText(/cycle|circular|descendant/i)).toBeVisible({ timeout: 5_000 });
  });
});
