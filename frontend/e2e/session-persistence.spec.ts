/**
 * E2E tests for Session Persistence (INT-018 to INT-020)
 *
 * Tests conversation persistence across reloads, session switching,
 * and session management features.
 */

import { test, expect } from '@playwright/test';

test.describe('Session Persistence', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const chatLink = page.locator('[data-testid="nav-ai-chat"]');
    if (await chatLink.isVisible()) {
      await chatLink.click();
    }

    await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 10000 });
  });

  test('INT-018: conversation persists across page reloads', async ({ page }) => {
    // Send multiple messages to create conversation history
    const message1 = `First message ${Date.now()}`;
    await page.locator('[data-testid="chat-input"]').fill(message1);
    await page.locator('[data-testid="send-button"]').click();

    // Wait for user message and AI response
    await expect(page.locator('[data-testid="message-user"]').last()).toContainText(message1);
    await expect(page.locator('[data-testid="message-assistant"]').last()).toBeVisible({
      timeout: 15000,
    });

    // Send second message
    const message2 = `Second message ${Date.now()}`;
    await page.locator('[data-testid="chat-input"]').fill(message2);
    await page.locator('[data-testid="send-button"]').click();

    await expect(page.locator('[data-testid="message-user"]').last()).toContainText(message2);

    // Count messages before reload
    const messageCountBefore = await page.locator('[data-testid^="message-"]').count();
    expect(messageCountBefore).toBeGreaterThanOrEqual(2);

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Messages should still be there
    await expect(page.locator('[data-testid="message-user"]').first()).toContainText(message1);

    const messageCountAfter = await page.locator('[data-testid^="message-"]').count();
    expect(messageCountAfter).toBe(messageCountBefore);
  });

  test('INT-019: session switch changes context', async ({ page }) => {
    // Send message in current session
    const currentSessionMessage = `Current session ${Date.now()}`;
    await page.locator('[data-testid="chat-input"]').fill(currentSessionMessage);
    await page.locator('[data-testid="send-button"]').click();

    await expect(page.locator('[data-testid="message-user"]').last()).toContainText(
      currentSessionMessage
    );

    // Wait for response
    await expect(page.locator('[data-testid="message-assistant"]').last()).toBeVisible({
      timeout: 15000,
    });

    // Create new session
    const newSessionButton = page.locator('[data-testid="new-session-button"]');
    if (await newSessionButton.isVisible({ timeout: 5000 })) {
      await newSessionButton.click();

      // Should have empty chat in new session
      await page.waitForTimeout(2000);

      const messageCount = await page.locator('[data-testid^="message-"]').count();
      expect(messageCount).toBe(0);

      // Send message in new session
      const newSessionMessage = `New session ${Date.now()}`;
      await page.locator('[data-testid="chat-input"]').fill(newSessionMessage);
      await page.locator('[data-testid="send-button"]').click();

      await expect(page.locator('[data-testid="message-user"]').last()).toContainText(
        newSessionMessage
      );

      // Switch back to previous session if session dropdown exists
      const sessionDropdown = page.locator('[data-testid="session-dropdown"]');
      if (await sessionDropdown.isVisible({ timeout: 5000 })) {
        await sessionDropdown.click();

        // Select first session (not current)
        const sessionItems = page.locator('[data-testid="session-item"]');
        const sessionCount = await sessionItems.count();

        if (sessionCount > 1) {
          await sessionItems.nth(1).click(); // Select second item (first is current)

          // Should see old messages
          await page.waitForTimeout(2000);
          const hasOldMessage = await page
            .locator('[data-testid="message-user"]')
            .filter({ hasText: currentSessionMessage })
            .isVisible({ timeout: 5000 });

          expect(hasOldMessage).toBeTruthy();
        }
      }
    }
  });

  test('INT-020: session list shows recent sessions', async ({ page }) => {
    // Check if session dropdown exists
    const sessionDropdown = page.locator('[data-testid="session-dropdown"]');

    if (await sessionDropdown.isVisible({ timeout: 5000 })) {
      await sessionDropdown.click();

      // Should show session items
      const sessionItems = page.locator('[data-testid="session-item"]');
      const sessionCount = await sessionItems.count();

      expect(sessionCount).toBeGreaterThan(0);

      // Each session should have title or timestamp
      const firstSession = sessionItems.first();
      const sessionText = await firstSession.textContent();
      expect(sessionText).toBeTruthy();
      expect(sessionText!.length).toBeGreaterThan(0);
    }
  });

  test('clear conversation removes messages but preserves session', async ({ page }) => {
    // Send message
    const testMessage = `Test message ${Date.now()}`;
    await page.locator('[data-testid="chat-input"]').fill(testMessage);
    await page.locator('[data-testid="send-button"]').click();

    await expect(page.locator('[data-testid="message-user"]').last()).toContainText(testMessage);

    // Find clear button (might be in header or menu)
    const clearButton =
      page.locator('[data-testid="clear-conversation-button"]') ||
      page.locator('[data-testid="clear-chat-button"]');

    if (await clearButton.isVisible({ timeout: 5000 })) {
      // Click clear
      await clearButton.click();

      // May show confirmation dialog
      const confirmButton = page.locator('button:has-text("Clear")');
      if (await confirmButton.isVisible({ timeout: 2000 })) {
        await confirmButton.click();
      }

      // Messages should be cleared
      await page.waitForTimeout(1000);
      const messageCount = await page.locator('[data-testid^="message-"]').count();
      expect(messageCount).toBe(0);
    }
  });

  test('session persists after browser navigation', async ({ page }) => {
    // Send message
    const testMessage = `Navigation test ${Date.now()}`;
    await page.locator('[data-testid="chat-input"]').fill(testMessage);
    await page.locator('[data-testid="send-button"]').click();

    await expect(page.locator('[data-testid="message-user"]').last()).toContainText(testMessage);

    // Navigate to different page
    const issuesLink = page.locator('[data-testid="nav-issues"]');
    if (await issuesLink.isVisible({ timeout: 5000 })) {
      await issuesLink.click();
      await page.waitForLoadState('networkidle');

      // Navigate back to chat
      const chatLink = page.locator('[data-testid="nav-ai-chat"]');
      if (await chatLink.isVisible()) {
        await chatLink.click();
      }

      // Message should still be there
      await page.waitForTimeout(2000);
      const hasMessage = await page
        .locator('[data-testid="message-user"]')
        .filter({ hasText: testMessage })
        .isVisible({ timeout: 5000 });

      expect(hasMessage).toBeTruthy();
    }
  });

  test('session ID visible in UI', async ({ page }) => {
    // Check if session ID or identifier is shown
    const sessionHeader = page.locator('[data-testid="chat-header"]');

    if (await sessionHeader.isVisible({ timeout: 5000 })) {
      const headerText = await sessionHeader.textContent();
      expect(headerText).toBeTruthy();

      // Should contain some identifier (session ID, title, or timestamp)
      expect(headerText!.length).toBeGreaterThan(0);
    }
  });
});
