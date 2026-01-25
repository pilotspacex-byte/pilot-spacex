/**
 * E2E tests for issue management workflow.
 *
 * Tests issue creation with AI enhancement, state transitions,
 * duplicate detection, bulk operations, calendar view, and trash/restore.
 */

import { test, expect } from '@playwright/test';

test.describe('Issue Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to issues - auth state is pre-loaded via storageState
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.click('[data-testid="nav-issues"]');
  });

  test.describe('Create Issue with AI Enhancement', () => {
    test('should create issue with AI enhancement', async ({ page }) => {
      await page.click('[data-testid="create-issue-button"]');

      // Fill issue form
      await page.fill('[data-testid="issue-title-input"]', 'Fix login button');
      await page.fill(
        '[data-testid="issue-description-input"]',
        'The login button is not working on mobile'
      );

      // Enable AI enhancement
      await page.click('[data-testid="enhance-with-ai-toggle"]');

      // Submit
      await page.click('[data-testid="submit-issue-button"]');

      // Wait for AI enhancement
      await expect(page.locator('[data-testid="ai-enhancing-indicator"]')).toBeVisible();

      // Issue should be created with AI metadata
      await expect(page.locator('[data-testid="issue-card"]')).toContainText('Fix login button');
      await expect(page.locator('[data-testid="ai-enhanced-badge"]')).toBeVisible();
    });

    test('should show AI suggestions during creation', async ({ page }) => {
      await page.click('[data-testid="create-issue-button"]');

      await page.fill('[data-testid="issue-title-input"]', 'Authentication error');

      // Wait for AI suggestions
      await page.waitForTimeout(500);

      // Should show suggested labels
      await expect(page.locator('[data-testid="ai-suggested-labels"]')).toBeVisible();
    });
  });

  test.describe('State Transitions via Dropdown', () => {
    test('should change issue state via dropdown', async ({ page }) => {
      // Click on first issue
      await page.click('[data-testid="issue-card"]:first-child');

      // Open state dropdown
      await page.click('[data-testid="issue-state-dropdown"]');

      // Select "In Progress"
      await page.click('[data-testid="state-option-in_progress"]');

      // Verify state changed
      await expect(page.locator('[data-testid="issue-state-badge"]')).toContainText('In Progress');
    });

    test('should show invalid transition warning', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="issue-state-dropdown"]');

      // Try to select invalid state
      await page.click('[data-testid="state-option-done"]');

      // Should show warning
      await expect(page.locator('[data-testid="invalid-transition-toast"]')).toBeVisible();
    });
  });

  test.describe('Duplicate Detection Alert', () => {
    test('should show duplicate detection alert', async ({ page }) => {
      await page.click('[data-testid="create-issue-button"]');

      // Type title similar to existing issue
      await page.fill('[data-testid="issue-title-input"]', 'Fix login button');

      // Wait for duplicate detection
      await page.waitForTimeout(500);

      // Should show duplicate alert
      await expect(page.locator('[data-testid="duplicate-detection-alert"]')).toBeVisible();
    });

    test('should link to similar issues', async ({ page }) => {
      await page.click('[data-testid="create-issue-button"]');
      await page.fill('[data-testid="issue-title-input"]', 'Fix login button');
      await page.waitForTimeout(500);

      // Click on similar issue link
      await page.click('[data-testid="similar-issue-link"]');

      // Should navigate to similar issue
      await expect(page.locator('[data-testid="issue-detail-panel"]')).toBeVisible();
    });
  });

  test.describe('Bulk Operations', () => {
    test('should select multiple issues', async ({ page }) => {
      // Enable selection mode
      await page.click('[data-testid="bulk-select-toggle"]');

      // Select multiple issues
      await page.click('[data-testid="issue-checkbox"]:nth-child(1)');
      await page.click('[data-testid="issue-checkbox"]:nth-child(2)');
      await page.click('[data-testid="issue-checkbox"]:nth-child(3)');

      // Should show bulk actions bar
      await expect(page.locator('[data-testid="bulk-actions-bar"]')).toBeVisible();
      await expect(page.locator('[data-testid="selected-count"]')).toContainText('3');
    });

    test('should bulk update state', async ({ page }) => {
      await page.click('[data-testid="bulk-select-toggle"]');
      await page.click('[data-testid="issue-checkbox"]:nth-child(1)');
      await page.click('[data-testid="issue-checkbox"]:nth-child(2)');

      // Click bulk state change
      await page.click('[data-testid="bulk-change-state"]');
      await page.click('[data-testid="bulk-state-todo"]');

      // Should show success
      await expect(page.locator('[data-testid="bulk-update-toast"]')).toBeVisible();
    });

    test('should bulk assign issues', async ({ page }) => {
      await page.click('[data-testid="bulk-select-toggle"]');
      await page.click('[data-testid="issue-checkbox"]:nth-child(1)');
      await page.click('[data-testid="issue-checkbox"]:nth-child(2)');

      await page.click('[data-testid="bulk-assign"]');
      await page.click('[data-testid="assignee-option"]:first-child');

      await expect(page.locator('[data-testid="bulk-update-toast"]')).toBeVisible();
    });
  });

  test.describe('Calendar View Interactions', () => {
    test('should switch to calendar view', async ({ page }) => {
      await page.click('[data-testid="view-calendar"]');

      await expect(page.locator('[data-testid="calendar-view"]')).toBeVisible();
    });

    test('should show issues on calendar by due date', async ({ page }) => {
      await page.click('[data-testid="view-calendar"]');

      // Issues with due dates should appear on calendar
      await expect(page.locator('[data-testid="calendar-issue-chip"]')).toBeVisible();
    });

    test('should drag issue to new date', async ({ page }) => {
      await page.click('[data-testid="view-calendar"]');

      const issueChip = page.locator('[data-testid="calendar-issue-chip"]:first-child');
      const targetDate = page.locator('[data-testid="calendar-day"]:nth-child(15)');

      await issueChip.dragTo(targetDate);

      // Issue due date should update
      await expect(page.locator('[data-testid="date-updated-toast"]')).toBeVisible();
    });
  });

  test.describe('Trash and Restore', () => {
    test('should move issue to trash', async ({ page }) => {
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="issue-menu-button"]');
      await page.click('[data-testid="delete-issue-option"]');

      // Confirm deletion
      await page.click('[data-testid="confirm-delete-button"]');

      // Issue should be removed from list
      await expect(page.locator('[data-testid="issue-deleted-toast"]')).toBeVisible();
    });

    test('should view trash', async ({ page }) => {
      await page.click('[data-testid="trash-button"]');

      await expect(page.locator('[data-testid="trash-view"]')).toBeVisible();
    });

    test('should restore issue from trash', async ({ page }) => {
      await page.click('[data-testid="trash-button"]');
      await page.click('[data-testid="trash-issue-card"]:first-child');
      await page.click('[data-testid="restore-issue-button"]');

      await expect(page.locator('[data-testid="issue-restored-toast"]')).toBeVisible();
    });
  });

  test.describe('Filtering and Search', () => {
    test('should filter issues by state', async ({ page }) => {
      await page.click('[data-testid="filter-state"]');
      await page.click('[data-testid="filter-state-in_progress"]');

      // Only in-progress issues should be visible
      const cards = page.locator('[data-testid="issue-card"]');
      for (let i = 0; i < (await cards.count()); i++) {
        await expect(cards.nth(i).locator('[data-testid="issue-state-badge"]')).toContainText(
          'In Progress'
        );
      }
    });

    test('should search issues by title', async ({ page }) => {
      await page.fill('[data-testid="search-input"]', 'login');

      await page.waitForTimeout(300); // Debounce

      // Should filter to matching issues
      await expect(page.locator('[data-testid="issue-card"]')).toContainText('login');
    });
  });
});
