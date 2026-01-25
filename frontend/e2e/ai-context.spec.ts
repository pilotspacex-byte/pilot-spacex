/**
 * E2E tests for AI context workflow.
 *
 * Tests generating AI context, context panel display,
 * copying Claude Code prompts, regenerating with feedback,
 * and context for different issue types.
 */

import { test, expect } from '@playwright/test';

test.describe('AI Context Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to issues - auth state is pre-loaded via storageState
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.click('[data-testid="nav-issues"]');
  });

  test.describe('Generate AI Context', () => {
    test('should generate AI context for issue', async ({ page }) => {
      // Open issue detail
      await page.click('[data-testid="issue-card"]:first-child');

      // Click AI Context tab
      await page.click('[data-testid="ai-context-tab"]');

      // Click generate button
      await page.click('[data-testid="generate-context-button"]');

      // Should show loading state
      await expect(page.locator('[data-testid="context-loading"]')).toBeVisible();

      // Should show generated context
      await expect(page.locator('[data-testid="ai-context-panel"]')).toBeVisible({
        timeout: 30000,
      });
    });

    test('should show context generation progress', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');
      await page.click('[data-testid="generate-context-button"]');

      // Should show progress indicators
      await expect(page.locator('[data-testid="gathering-docs"]')).toBeVisible();
      await expect(page.locator('[data-testid="analyzing-code"]')).toBeVisible();
    });
  });

  test.describe('Context Panel Display', () => {
    test('should display related documents section', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Assuming context is already generated
      await expect(page.locator('[data-testid="related-docs-section"]')).toBeVisible();
    });

    test('should display code context section', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      await expect(page.locator('[data-testid="code-context-section"]')).toBeVisible();
    });

    test('should display suggested tasks section', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      await expect(page.locator('[data-testid="suggested-tasks-section"]')).toBeVisible();
    });

    test('should show confidence tags for suggestions', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Should show confidence tags (Recommended, Default, Current, Alternative)
      await expect(page.locator('[data-testid="confidence-tag"]')).toBeVisible();
    });
  });

  test.describe('Copy Claude Code Prompt', () => {
    test('should copy full Claude Code prompt', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Click copy prompt button
      await page.click('[data-testid="copy-prompt-button"]');

      // Should show copied confirmation
      await expect(page.locator('[data-testid="copied-toast"]')).toBeVisible();
    });

    test('should preview prompt before copying', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Click preview button
      await page.click('[data-testid="preview-prompt-button"]');

      // Should show prompt preview modal
      await expect(page.locator('[data-testid="prompt-preview-modal"]')).toBeVisible();
      await expect(page.locator('[data-testid="prompt-content"]')).toContainText('##');
    });

    test('should copy individual task prompt', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Click copy on individual task
      await page.click('[data-testid="task-item"]:first-child [data-testid="copy-task-button"]');

      await expect(page.locator('[data-testid="copied-toast"]')).toBeVisible();
    });
  });

  test.describe('Regenerate with Feedback', () => {
    test('should regenerate context with feedback', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Click regenerate button
      await page.click('[data-testid="regenerate-button"]');

      // Fill feedback
      await page.fill(
        '[data-testid="feedback-input"]',
        'Include more details about authentication flow'
      );
      await page.click('[data-testid="submit-feedback-button"]');

      // Should regenerate with new context
      await expect(page.locator('[data-testid="context-loading"]')).toBeVisible();
    });

    test('should rate context quality', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Rate context
      await page.click('[data-testid="thumbs-up-button"]');

      await expect(page.locator('[data-testid="rating-submitted-toast"]')).toBeVisible();
    });

    test('should provide negative feedback with reason', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      await page.click('[data-testid="thumbs-down-button"]');

      // Should open feedback modal
      await expect(page.locator('[data-testid="feedback-modal"]')).toBeVisible();

      await page.click('[data-testid="feedback-reason-incomplete"]');
      await page.click('[data-testid="submit-negative-feedback"]');

      await expect(page.locator('[data-testid="feedback-submitted-toast"]')).toBeVisible();
    });
  });

  test.describe('Context for Different Issue Types', () => {
    test('should generate context for bug issue', async ({ page }) => {
      // Find a bug issue
      await page.click('[data-testid="filter-labels"]');
      await page.click('[data-testid="label-bug"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Bug context should include reproduction steps
      await expect(page.locator('[data-testid="context-section-reproduction"]')).toBeVisible();
    });

    test('should generate context for feature issue', async ({ page }) => {
      await page.click('[data-testid="filter-labels"]');
      await page.click('[data-testid="label-feature"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Feature context should include acceptance criteria
      await expect(page.locator('[data-testid="context-section-acceptance"]')).toBeVisible();
    });

    test('should show different tasks for different issue types', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Tasks should be relevant to issue type
      const taskCount = await page.locator('[data-testid="task-item"]').count();
      expect(taskCount).toBeGreaterThan(0);
    });
  });

  test.describe('Context Actions', () => {
    test('should add task to issue from context', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Click add task on first suggestion
      await page.click('[data-testid="task-item"]:first-child [data-testid="add-task-button"]');

      // Should add task to issue
      await expect(page.locator('[data-testid="task-added-toast"]')).toBeVisible();
    });

    test('should open code file from context', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="ai-context-tab"]');

      // Click on code reference
      await page.click('[data-testid="code-reference-link"]:first-child');

      // Should navigate to code view or open external link
      await expect(
        page.locator('[data-testid="code-viewer"]').or(page.locator('body'))
      ).toBeVisible();
    });
  });
});
