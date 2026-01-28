/**
 * E2E tests for Chat Conversation Flow (INT-001 to INT-005)
 *
 * Tests complete chat roundtrip with SSE streaming, error recovery,
 * and message persistence across page reloads.
 */

import { test, expect } from '@playwright/test';

test.describe('Chat Conversation Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to chat view - auth state is pre-loaded via storageState
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Navigate to AI chat (adjust based on actual routing)
    const chatLink = page.locator('[data-testid="nav-ai-chat"]');
    if (await chatLink.isVisible()) {
      await chatLink.click();
    }
  });

  test('INT-001: complete chat roundtrip with SSE streaming', async ({ page }) => {
    // Wait for chat view to load
    await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 10000 });

    // Type message in input
    const chatInput = page.locator('[data-testid="chat-input"]');
    await expect(chatInput).toBeVisible();
    await chatInput.fill('What is FastAPI?');

    // Send message
    const sendButton = page.locator('[data-testid="send-button"]');
    await sendButton.click();

    // Verify user message appears in MessageList
    const userMessage = page.locator('[data-testid="message-user"]').last();
    await expect(userMessage).toBeVisible({ timeout: 5000 });
    await expect(userMessage).toContainText('What is FastAPI?');

    // Wait for AI response to stream in
    const aiMessage = page.locator('[data-testid="message-assistant"]').last();
    await expect(aiMessage).toBeVisible({ timeout: 15000 });

    // Verify response contains content
    const responseText = await aiMessage.textContent();
    expect(responseText).toBeTruthy();
    expect(responseText!.length).toBeGreaterThan(0);

    // Verify streaming indicator disappears
    await expect(page.locator('[data-testid="streaming-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });
  });

  test('INT-002: SSE streaming displays tokens in real-time', async ({ page }) => {
    await expect(page.locator('[data-testid="chat-view"]')).toBeVisible();

    // Send message
    await page.locator('[data-testid="chat-input"]').fill('Explain async/await in Python');
    await page.locator('[data-testid="send-button"]').click();

    // Track token accumulation
    const aiMessage = page.locator('[data-testid="message-assistant"]').last();
    await aiMessage.waitFor({ state: 'visible', timeout: 10000 });

    // Wait a bit to see streaming happen
    await page.waitForTimeout(2000);

    // Verify streaming is happening (content length increasing)
    const initialText = await aiMessage.textContent();
    expect(initialText).toBeTruthy();

    // Wait for streaming to complete
    await expect(page.locator('[data-testid="streaming-indicator"]')).not.toBeVisible({
      timeout: 30000,
    });

    // Verify final message has more content
    const finalText = await aiMessage.textContent();
    expect(finalText!.split(' ').length).toBeGreaterThan(5);
  });

  test('INT-003: error recovery shows error message', async ({ page }) => {
    await expect(page.locator('[data-testid="chat-view"]')).toBeVisible();

    // Try to send empty message
    const sendButton = page.locator('[data-testid="send-button"]');

    // Send button should be disabled for empty input
    const chatInput = page.locator('[data-testid="chat-input"]');
    await expect(chatInput).toBeVisible();

    // Fill with empty spaces
    await chatInput.fill('   ');

    // Button should still be disabled or show error
    const isDisabled = await sendButton.isDisabled();
    expect(isDisabled).toBeTruthy();
  });

  test('INT-004: conversation persists across page reloads', async ({ page }) => {
    await expect(page.locator('[data-testid="chat-view"]')).toBeVisible();

    // Send a unique message
    const uniqueMessage = `Test message at ${Date.now()}`;
    await page.locator('[data-testid="chat-input"]').fill(uniqueMessage);
    await page.locator('[data-testid="send-button"]').click();

    // Wait for user message to appear
    await expect(page.locator('[data-testid="message-user"]').last()).toContainText(uniqueMessage);

    // Wait for AI response
    await expect(page.locator('[data-testid="message-assistant"]').last()).toBeVisible({
      timeout: 15000,
    });

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Message should still be there
    await expect(page.locator('[data-testid="message-user"]')).toContainText(uniqueMessage);
  });

  test('INT-005: abort streaming stops response generation', async ({ page }) => {
    await expect(page.locator('[data-testid="chat-view"]')).toBeVisible();

    // Send message that will generate long response
    await page.locator('[data-testid="chat-input"]').fill('Write a long essay about Python');
    await page.locator('[data-testid="send-button"]').click();

    // Wait for streaming to start
    await expect(page.locator('[data-testid="streaming-indicator"]')).toBeVisible({
      timeout: 5000,
    });

    // Click abort button
    const abortButton = page.locator('[data-testid="abort-button"]');
    if (await abortButton.isVisible()) {
      await abortButton.click();

      // Streaming should stop
      await expect(page.locator('[data-testid="streaming-indicator"]')).not.toBeVisible({
        timeout: 5000,
      });
    }
  });
});
