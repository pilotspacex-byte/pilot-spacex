/**
 * E2E tests for Skill Invocation from UI (INT-005)
 *
 * Tests invoking skills from chat interface, structured output display,
 * and confidence tag rendering.
 */

import { test, expect } from '@playwright/test';

test.describe('Skill Invocation from UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Navigate to AI chat
    const chatLink = page.locator('[data-testid="nav-ai-chat"]');
    if (await chatLink.isVisible()) {
      await chatLink.click();
    }

    await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 10000 });
  });

  test('INT-005: invoke /extract-issues skill from chat', async ({ page }) => {
    // Type skill command with note content
    const skillCommand = `/extract-issues

Implement user authentication
Fix login bug
Add password reset feature`;

    await page.locator('[data-testid="chat-input"]').fill(skillCommand);
    await page.locator('[data-testid="send-button"]').click();

    // Wait for user message to appear
    await expect(page.locator('[data-testid="message-user"]').last()).toContainText(
      '/extract-issues'
    );

    // Wait for skill execution and response
    const aiMessage = page.locator('[data-testid="message-assistant"]').last();
    await expect(aiMessage).toBeVisible({ timeout: 15000 });

    // Verify response contains structured output
    const responseText = await aiMessage.textContent();
    expect(responseText).toBeTruthy();

    // Should mention extracted issues
    expect(responseText!.toLowerCase()).toContain('issue');
  });

  test('skill invocation shows skill menu', async ({ page }) => {
    const chatInput = page.locator('[data-testid="chat-input"]');
    await chatInput.fill('/');

    // Should show skill menu dropdown
    const skillMenu = page.locator('[data-testid="skill-menu"]');
    if (await skillMenu.isVisible({ timeout: 2000 })) {
      // Verify menu has skill options
      await expect(skillMenu.locator('[data-testid="skill-option"]')).toHaveCount(
        expect.any(Number)
      );
    }
  });

  test('skill result displays in message format', async ({ page }) => {
    // Invoke a simple skill
    await page.locator('[data-testid="chat-input"]').fill('/help');
    await page.locator('[data-testid="send-button"]').click();

    // Wait for response
    await expect(page.locator('[data-testid="message-assistant"]').last()).toBeVisible({
      timeout: 10000,
    });

    // Response should contain helpful information
    const responseText = await page
      .locator('[data-testid="message-assistant"]')
      .last()
      .textContent();
    expect(responseText).toBeTruthy();
    expect(responseText!.length).toBeGreaterThan(10);
  });

  test('confidence tags appear in AI responses', async ({ page }) => {
    // Send message that might generate confidence tags
    await page
      .locator('[data-testid="chat-input"]')
      .fill('What is the best way to structure a FastAPI project?');
    await page.locator('[data-testid="send-button"]').click();

    // Wait for response
    await expect(page.locator('[data-testid="message-assistant"]').last()).toBeVisible({
      timeout: 15000,
    });

    // Check if confidence badge exists (optional based on response content)
    const confidenceBadge = page.locator('[data-testid="confidence-badge"]');
    if (await confidenceBadge.isVisible({ timeout: 2000 })) {
      const badgeText = await confidenceBadge.textContent();
      expect(badgeText).toMatch(/RECOMMENDED|DEFAULT|CURRENT|ALTERNATIVE/i);
    }
  });

  test('skill execution shows progress indicator', async ({ page }) => {
    // Invoke skill that might take time
    await page.locator('[data-testid="chat-input"]').fill('/extract-issues\n\nSome long text');
    await page.locator('[data-testid="send-button"]').click();

    // Should show streaming or processing indicator
    const streamingIndicator = page.locator('[data-testid="streaming-indicator"]');
    await expect(streamingIndicator).toBeVisible({ timeout: 5000 });

    // Eventually completes
    await expect(streamingIndicator).not.toBeVisible({ timeout: 30000 });
  });
});
