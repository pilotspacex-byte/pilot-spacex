/**
 * Flow (e) — Quote-to-chat: select text in artifact body -> pill ->
 * pre-fill chat composer with citation.
 *
 * Phase 94 Plan 03 — depends on a seeded artifactId (NOTE) rendered in
 * a peek-able route. The QuoteToChatPill listens for window selection
 * and dispatches `pilot:quote-to-chat` events the chat composer drains
 * (verified via frontend/src/features/ai/ChatView/ChatInput/ChatInput.tsx).
 */

import { test, expect } from './auth.fixture';
import { getSeedContext } from './fixtures/seed-helpers';

test.describe('quote-to-chat', () => {
  test('selecting artifact text shows pill; clicking pre-fills composer with quote', async ({
    page,
  }) => {
    const seed = getSeedContext();
    test.skip(
      !seed.artifactId || !seed.chatSessionId,
      'TODO(94-03): global-setup must seed a NOTE artifact + chat session ' +
        'so the peek drawer renders with selectable body content.'
    );

    await page.goto(
      `/${seed.workspaceSlug}/chat?session=${seed.chatSessionId}&peek=note:${seed.artifactId}`
    );

    const drawer = page.locator('[data-peek-mode]');
    await expect(drawer).toBeVisible({ timeout: 10_000 });

    // Select text within drawer body via the Selection API + dispatch a
    // mouseup so the QuoteToChatPill watcher fires.
    const target = drawer.locator('p, .prose, [data-prose]').first();
    await target.evaluate((el) => {
      const range = document.createRange();
      range.selectNodeContents(el);
      const sel = window.getSelection();
      sel?.removeAllRanges();
      sel?.addRange(range);
      el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
    });

    const pill = page.getByRole('button', { name: /quote.*chat|quote/i }).first();
    await expect(pill).toBeVisible({ timeout: 5_000 });
    await pill.click();

    const chatInput = page.getByRole('textbox', { name: /message|chat input|ask|prompt/i }).first();
    await expect(chatInput).toBeVisible();
    // Pre-fill carries a `>` blockquote marker or a citation phrase.
    const value = await chatInput.evaluate((el: HTMLTextAreaElement | HTMLInputElement) => {
      if ('value' in el) return el.value;
      return (el as unknown as HTMLElement).textContent ?? '';
    });
    expect(value).toMatch(/>|cite|from|quote/i);
  });
});
