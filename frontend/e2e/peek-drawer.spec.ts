/**
 * Flow (b) — Peek drawer open / expand / close preserves chat scroll.
 *
 * Phase 94 Plan 03 Phase 2 — seed data (chatSessionId + artifactId) is now
 * written by global-setup via POST /api/v1/_test/seed/bootstrap.
 *
 * Remaining blocker: InlineArtifactCard does not emit `data-artifact-id`
 * on its root element, so the locator `[data-artifact-id="..."]` never
 * matches. Unskip after ArtifactCard/InlineArtifactCard adds that attribute.
 * TODO(94-03-phase3): add data-artifact-id to InlineArtifactCard root.
 */

import { test, expect } from './auth.fixture';
import { getSeedContext } from './fixtures/seed-helpers';

test.describe('peek drawer (artifact preview)', () => {
  test('open via inline artifact card, expand to focus, close preserves chat scroll', async ({
    page,
  }) => {
    const seed = getSeedContext();
    test.skip(
      !seed.chatSessionId || !seed.artifactId,
      'TODO(94-03-phase3): InlineArtifactCard does not render data-artifact-id — ' +
        'add that attribute to the component root before this spec can locate the card. ' +
        `Seed data available: chatSessionId=${seed.chatSessionId ?? 'null'} artifactId=${seed.artifactId ?? 'null'}`
    );

    await page.goto(
      `/${seed.workspaceSlug}/chat?session=${seed.chatSessionId}`
    );

    // Click the inline artifact card to open the peek drawer.
    const artifactCard = page
      .locator(`[data-artifact-id="${seed.artifactId}"]`)
      .first();
    await artifactCard.waitFor({ state: 'visible', timeout: 10_000 });

    // Capture scroll baseline on the chat feed (role="log" is the
    // standard ARIA role for live-updating message lists).
    const feed = page.getByRole('log').first();
    await feed.evaluate((el) => {
      el.scrollTop = 200;
    });
    const initialScroll = await feed.evaluate((el) => el.scrollTop);

    await artifactCard.click();
    const drawer = page.locator('[data-peek-mode]');
    await expect(drawer).toBeVisible();
    await expect(drawer).toHaveAttribute('data-peek-mode', /side|bottom-sheet/);

    // Expand to focus pane via Cmd+. shortcut — Phase 86 Plan 04.
    await page.keyboard.press('Meta+.');
    await expect(
      page.locator('[data-focus-pane="open"], [data-state="expanded"]')
    ).toBeVisible({ timeout: 5_000 });

    // Demote back to peek.
    await page.keyboard.press('Meta+.');
    await expect(drawer).toBeVisible();

    // Close.
    await page.keyboard.press('Escape');
    await expect(drawer).toBeHidden();

    const finalScroll = await feed.evaluate((el) => el.scrollTop);
    expect(Math.abs(finalScroll - initialScroll)).toBeLessThanOrEqual(20);
  });
});
