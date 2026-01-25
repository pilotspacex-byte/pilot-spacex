/**
 * E2E tests for cycle/sprint workflow.
 *
 * Tests cycle creation, adding issues, velocity chart,
 * burndown chart, and completing cycles.
 */

import { test, expect } from '@playwright/test';

test.describe('Cycle Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to cycles - auth state is pre-loaded via storageState
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.click('[data-testid="nav-cycles"]');
  });

  test.describe('Create Cycle', () => {
    test('should create a new cycle', async ({ page }) => {
      await page.click('[data-testid="create-cycle-button"]');

      // Fill cycle form
      await page.fill('[data-testid="cycle-name-input"]', 'Sprint 1');
      await page.fill('[data-testid="cycle-start-date"]', '2026-02-01');
      await page.fill('[data-testid="cycle-end-date"]', '2026-02-14');

      await page.click('[data-testid="submit-cycle-button"]');

      // Cycle should be created
      await expect(page.locator('[data-testid="cycle-card"]')).toContainText('Sprint 1');
    });

    test('should validate cycle dates', async ({ page }) => {
      await page.click('[data-testid="create-cycle-button"]');

      // Set end date before start date
      await page.fill('[data-testid="cycle-start-date"]', '2026-02-14');
      await page.fill('[data-testid="cycle-end-date"]', '2026-02-01');

      await page.click('[data-testid="submit-cycle-button"]');

      // Should show validation error
      await expect(page.locator('[data-testid="date-error"]')).toBeVisible();
    });
  });

  test.describe('Add Issues to Cycle', () => {
    test('should add issues to cycle via drag and drop', async ({ page }) => {
      // Navigate to cycle detail
      await page.click('[data-testid="cycle-card"]:first-child');

      // Drag issue from backlog to cycle
      const backlogIssue = page.locator('[data-testid="backlog-issue"]:first-child');
      const cycleDropzone = page.locator('[data-testid="cycle-dropzone"]');

      await backlogIssue.dragTo(cycleDropzone);

      // Issue should be in cycle
      await expect(page.locator('[data-testid="cycle-issue"]')).toBeVisible();
    });

    test('should add issues via modal', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');
      await page.click('[data-testid="add-issues-button"]');

      // Select issues in modal
      await page.click('[data-testid="issue-checkbox"]:nth-child(1)');
      await page.click('[data-testid="issue-checkbox"]:nth-child(2)');
      await page.click('[data-testid="confirm-add-issues"]');

      // Issues should be added
      await expect(page.locator('[data-testid="cycle-issues-count"]')).toContainText('2');
    });

    test('should remove issue from cycle', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');

      // Right-click on issue
      await page.click('[data-testid="cycle-issue"]:first-child', { button: 'right' });
      await page.click('[data-testid="remove-from-cycle"]');

      // Issue should be removed
      await expect(page.locator('[data-testid="issue-removed-toast"]')).toBeVisible();
    });
  });

  test.describe('Velocity Chart', () => {
    test('should display velocity chart', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');
      await page.click('[data-testid="velocity-tab"]');

      await expect(page.locator('[data-testid="velocity-chart"]')).toBeVisible();
    });

    test('should show velocity trend', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');
      await page.click('[data-testid="velocity-tab"]');

      // Should show velocity bars for past cycles
      await expect(page.locator('[data-testid="velocity-bar"]')).toHaveCount.greaterThan(0);
    });

    test('should show velocity average line', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');
      await page.click('[data-testid="velocity-tab"]');

      await expect(page.locator('[data-testid="velocity-average-line"]')).toBeVisible();
    });
  });

  test.describe('Burndown Chart', () => {
    test('should display burndown chart', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');
      await page.click('[data-testid="burndown-tab"]');

      await expect(page.locator('[data-testid="burndown-chart"]')).toBeVisible();
    });

    test('should show ideal vs actual burndown', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');
      await page.click('[data-testid="burndown-tab"]');

      await expect(page.locator('[data-testid="ideal-line"]')).toBeVisible();
      await expect(page.locator('[data-testid="actual-line"]')).toBeVisible();
    });

    test('should update burndown when issue completed', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');

      // Complete an issue
      await page.click('[data-testid="cycle-issue"]:first-child [data-testid="state-dropdown"]');
      await page.click('[data-testid="state-done"]');

      // Switch to burndown
      await page.click('[data-testid="burndown-tab"]');

      // Burndown should reflect completion
      await expect(page.locator('[data-testid="points-completed"]')).not.toContainText('0');
    });
  });

  test.describe('Complete Cycle', () => {
    test('should complete cycle', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');
      await page.click('[data-testid="complete-cycle-button"]');

      // Confirm completion
      await page.click('[data-testid="confirm-complete-button"]');

      // Cycle should be marked complete
      await expect(page.locator('[data-testid="cycle-status"]')).toContainText('Completed');
    });

    test('should show cycle summary on completion', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');
      await page.click('[data-testid="complete-cycle-button"]');
      await page.click('[data-testid="confirm-complete-button"]');

      // Should show summary modal
      await expect(page.locator('[data-testid="cycle-summary-modal"]')).toBeVisible();
      await expect(page.locator('[data-testid="completed-points"]')).toBeVisible();
      await expect(page.locator('[data-testid="incomplete-count"]')).toBeVisible();
    });

    test('should move incomplete issues to next cycle', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');
      await page.click('[data-testid="complete-cycle-button"]');

      // Select to move incomplete issues
      await page.click('[data-testid="move-incomplete-checkbox"]');
      await page.click('[data-testid="confirm-complete-button"]');

      // Navigate to next cycle
      await page.click('[data-testid="next-cycle-link"]');

      // Should have moved issues
      await expect(page.locator('[data-testid="cycle-issue"]')).toBeVisible();
    });
  });

  test.describe('Cycle Views', () => {
    test('should switch between list and board view', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');

      // Switch to board view
      await page.click('[data-testid="view-board"]');
      await expect(page.locator('[data-testid="kanban-board"]')).toBeVisible();

      // Switch back to list view
      await page.click('[data-testid="view-list"]');
      await expect(page.locator('[data-testid="issue-list"]')).toBeVisible();
    });

    test('should filter issues by assignee in cycle', async ({ page }) => {
      await page.click('[data-testid="cycle-card"]:first-child');
      await page.click('[data-testid="filter-assignee"]');
      await page.click('[data-testid="assignee-option"]:first-child');

      // Should filter issues
      await expect(page.locator('[data-testid="filtered-count"]')).toBeVisible();
    });
  });
});
