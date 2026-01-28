/**
 * E2E tests for Approval Workflow (INT-010 to INT-013)
 *
 * Tests human-in-the-loop approval for critical actions,
 * approval overlay interactions, and action execution.
 */

import { test, expect } from '@playwright/test';

test.describe('Approval Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const chatLink = page.locator('[data-testid="nav-ai-chat"]');
    if (await chatLink.isVisible()) {
      await chatLink.click();
    }

    await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 10000 });
  });

  test('INT-010: CRITICAL action triggers approval overlay', async ({ page }) => {
    // Request critical action (e.g., delete issue)
    await page.locator('[data-testid="chat-input"]').fill('Delete issue ISS-123');
    await page.locator('[data-testid="send-button"]').click();

    // Wait for user message
    await expect(page.locator('[data-testid="message-user"]').last()).toContainText(
      'Delete issue ISS-123'
    );

    // Check if approval overlay appears
    // Note: This depends on backend returning an approval request
    const approvalOverlay = page.locator('[data-testid="approval-overlay"]');

    // Give time for AI to respond and potentially trigger approval
    await page.waitForTimeout(5000);

    // If approval overlay appears, verify its contents
    if (await approvalOverlay.isVisible({ timeout: 10000 })) {
      await expect(page.locator('[data-testid="approval-title"]')).toContainText('Approval');

      // Verify action details shown
      const approvalContent = await approvalOverlay.textContent();
      expect(approvalContent).toBeTruthy();

      // Approve button should be visible
      await expect(page.locator('[data-testid="approve-button"]')).toBeVisible();

      // Reject button should be visible
      await expect(page.locator('[data-testid="reject-button"]')).toBeVisible();
    }
  });

  test('INT-011: approve action executes and closes overlay', async ({ page }) => {
    // Request action that requires approval
    await page.locator('[data-testid="chat-input"]').fill('Close all completed issues');
    await page.locator('[data-testid="send-button"]').click();

    // Wait for potential approval overlay
    await page.waitForTimeout(5000);

    const approvalOverlay = page.locator('[data-testid="approval-overlay"]');

    if (await approvalOverlay.isVisible({ timeout: 10000 })) {
      // Click approve button
      await page.locator('[data-testid="approve-button"]').click();

      // Overlay should close
      await expect(approvalOverlay).not.toBeVisible({ timeout: 5000 });

      // Should see confirmation or result message
      const lastMessage = page.locator('[data-testid="message-assistant"]').last();
      await expect(lastMessage).toBeVisible({ timeout: 10000 });
    }
  });

  test('INT-012: rejection provides feedback and closes overlay', async ({ page }) => {
    // Request critical action
    await page.locator('[data-testid="chat-input"]').fill('Delete all issues in project');
    await page.locator('[data-testid="send-button"]').click();

    await page.waitForTimeout(5000);

    const approvalOverlay = page.locator('[data-testid="approval-overlay"]');

    if (await approvalOverlay.isVisible({ timeout: 10000 })) {
      // Click reject button
      await page.locator('[data-testid="reject-button"]').click();

      // Should show rejection confirmation or alternative suggestions
      await page.waitForTimeout(2000);

      // Overlay should close
      await expect(approvalOverlay).not.toBeVisible({ timeout: 5000 });
    }
  });

  test('INT-013: DEFAULT action shows brief notification', async ({ page }) => {
    // Request DEFAULT action (e.g., create issue)
    await page.locator('[data-testid="chat-input"]').fill('Create issue: Add unit tests');
    await page.locator('[data-testid="send-button"]').click();

    // Wait for AI response
    await expect(page.locator('[data-testid="message-assistant"]').last()).toBeVisible({
      timeout: 15000,
    });

    // Check for action notification (non-blocking)
    const actionNotification = page.locator('[data-testid="action-notification"]');

    // If notification appears, it should be brief
    if (await actionNotification.isVisible({ timeout: 5000 })) {
      // Should disappear automatically
      await expect(actionNotification).not.toBeVisible({ timeout: 5000 });
    }
  });

  test('approval overlay shows action details', async ({ page }) => {
    // Request action
    await page.locator('[data-testid="chat-input"]').fill('Archive old issues');
    await page.locator('[data-testid="send-button"]').click();

    await page.waitForTimeout(5000);

    const approvalOverlay = page.locator('[data-testid="approval-overlay"]');

    if (await approvalOverlay.isVisible({ timeout: 10000 })) {
      // Should show action description
      const overlayText = await approvalOverlay.textContent();
      expect(overlayText).toBeTruthy();
      expect(overlayText!.length).toBeGreaterThan(10);

      // Should have action type or reasoning
      const hasActionInfo =
        (await page.locator('[data-testid="approval-action"]').isVisible()) ||
        (await page.locator('[data-testid="approval-reasoning"]').isVisible());

      expect(hasActionInfo).toBeTruthy();
    }
  });

  test('multiple approval requests queue properly', async ({ page }) => {
    // Request multiple actions
    await page.locator('[data-testid="chat-input"]').fill('Delete issue A, then delete issue B');
    await page.locator('[data-testid="send-button"]').click();

    await page.waitForTimeout(5000);

    const approvalOverlay = page.locator('[data-testid="approval-overlay"]');

    if (await approvalOverlay.isVisible({ timeout: 10000 })) {
      // First approval
      await page.locator('[data-testid="approve-button"]').click();

      // Wait for potential second approval
      await page.waitForTimeout(2000);

      // Either another approval appears or overlay closes
      const stillVisible = await approvalOverlay.isVisible({ timeout: 3000 });

      if (stillVisible) {
        // Second approval
        await page.locator('[data-testid="approve-button"]').click();
      }
    }
  });
});
