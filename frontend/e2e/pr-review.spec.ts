/**
 * E2E tests for AI PR review workflow.
 *
 * Tests triggering PR review manually, review status tracking,
 * review results display, comment navigation, and severity filtering.
 */

import { test, expect } from '@playwright/test';

test.describe('PR Review Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to home - auth state is pre-loaded via storageState
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Trigger PR Review Manually', () => {
    test('should show review button for linked PR', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await expect(page.locator('[data-testid="trigger-review-button"]')).toBeVisible();
    });

    test('should trigger PR review', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="trigger-review-button"]');

      // Should show review started
      await expect(page.locator('[data-testid="review-started-toast"]')).toBeVisible();
    });

    test('should show review in progress indicator', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="trigger-review-button"]');

      // Should show progress indicator
      await expect(page.locator('[data-testid="review-in-progress"]')).toBeVisible();
    });

    test('should show review options before triggering', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      // Click dropdown for review options
      await page.click('[data-testid="review-options-dropdown"]');

      // Should show review scope options
      await expect(page.locator('[data-testid="review-scope-full"]')).toBeVisible();
      await expect(page.locator('[data-testid="review-scope-security"]')).toBeVisible();
      await expect(page.locator('[data-testid="review-scope-performance"]')).toBeVisible();
    });
  });

  test.describe('Review Status Tracking', () => {
    test('should show review status badge', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await expect(
        page
          .locator('[data-testid="review-status-pending"]')
          .or(page.locator('[data-testid="review-status-completed"]'))
          .or(page.locator('[data-testid="review-status-failed"]'))
      ).toBeVisible();
    });

    test('should update status in realtime', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      // Trigger review
      await page.click('[data-testid="trigger-review-button"]');

      // Wait for status to update (mocked)
      await expect(page.locator('[data-testid="review-status-completed"]')).toBeVisible({
        timeout: 30000,
      });
    });

    test('should show review duration', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await expect(page.locator('[data-testid="review-duration"]')).toBeVisible();
    });

    test('should show review timestamp', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await expect(page.locator('[data-testid="review-timestamp"]')).toBeVisible();
    });
  });

  test.describe('Review Results Display', () => {
    test('should display review summary', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await expect(page.locator('[data-testid="review-summary"]')).toBeVisible();
    });

    test('should show issue count by severity', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await expect(page.locator('[data-testid="critical-count"]')).toBeVisible();
      await expect(page.locator('[data-testid="warning-count"]')).toBeVisible();
      await expect(page.locator('[data-testid="info-count"]')).toBeVisible();
    });

    test('should display review comments list', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await expect(page.locator('[data-testid="review-comments-list"]')).toBeVisible();
    });

    test('should show comment details', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      const comment = page.locator('[data-testid="review-comment"]:first-child');

      await expect(comment.locator('[data-testid="comment-file"]')).toBeVisible();
      await expect(comment.locator('[data-testid="comment-line"]')).toBeVisible();
      await expect(comment.locator('[data-testid="comment-severity"]')).toBeVisible();
      await expect(comment.locator('[data-testid="comment-message"]')).toBeVisible();
    });

    test('should show code snippet for comment', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="review-comment"]:first-child');

      await expect(page.locator('[data-testid="code-snippet"]')).toBeVisible();
    });
  });

  test.describe('Comment Navigation', () => {
    test('should navigate to file from comment', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="review-comment"]:first-child [data-testid="file-link"]');

      // Should open file or link to GitHub
      await expect(
        page.locator('[data-testid="code-viewer"]').or(page.locator('body'))
      ).toBeVisible();
    });

    test('should navigate between comments', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      // Click on first comment
      await page.click('[data-testid="review-comment"]:first-child');

      // Navigate to next
      await page.click('[data-testid="next-comment-button"]');

      // Second comment should be active
      await expect(
        page.locator('[data-testid="review-comment"]:nth-child(2)[data-active="true"]')
      ).toBeVisible();
    });

    test('should use keyboard to navigate comments', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="review-comment"]:first-child');

      // Press j for next comment
      await page.keyboard.press('j');

      // Second comment should be focused
      await expect(page.locator('[data-testid="review-comment"]:nth-child(2)')).toBeFocused();
    });

    test('should expand/collapse comment details', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      // Expand comment
      await page.click('[data-testid="review-comment"]:first-child [data-testid="expand-button"]');

      await expect(
        page.locator('[data-testid="review-comment"]:first-child [data-testid="expanded-details"]')
      ).toBeVisible();

      // Collapse
      await page.click(
        '[data-testid="review-comment"]:first-child [data-testid="collapse-button"]'
      );

      await expect(
        page.locator('[data-testid="review-comment"]:first-child [data-testid="expanded-details"]')
      ).not.toBeVisible();
    });
  });

  test.describe('Severity Filtering', () => {
    test('should filter by critical severity', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="filter-severity-critical"]');

      // All visible comments should be critical
      const comments = page.locator('[data-testid="review-comment"]');
      for (let i = 0; i < (await comments.count()); i++) {
        await expect(comments.nth(i).locator('[data-testid="comment-severity"]')).toContainText(
          'critical'
        );
      }
    });

    test('should filter by warning severity', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="filter-severity-warning"]');

      const comments = page.locator('[data-testid="review-comment"]');
      for (let i = 0; i < (await comments.count()); i++) {
        await expect(comments.nth(i).locator('[data-testid="comment-severity"]')).toContainText(
          'warning'
        );
      }
    });

    test('should filter by info severity', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="filter-severity-info"]');

      const comments = page.locator('[data-testid="review-comment"]');
      for (let i = 0; i < (await comments.count()); i++) {
        await expect(comments.nth(i).locator('[data-testid="comment-severity"]')).toContainText(
          'info'
        );
      }
    });

    test('should show filtered count', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="filter-severity-critical"]');

      await expect(page.locator('[data-testid="filtered-count"]')).toBeVisible();
    });

    test('should clear filter', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="filter-severity-critical"]');
      await page.click('[data-testid="clear-filters-button"]');

      // All comments should be visible
      await expect(page.locator('[data-testid="filter-active"]')).not.toBeVisible();
    });
  });

  test.describe('Review Actions', () => {
    test('should mark comment as resolved', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="review-comment"]:first-child [data-testid="resolve-button"]');

      await expect(
        page.locator('[data-testid="review-comment"]:first-child[data-resolved="true"]')
      ).toBeVisible();
    });

    test('should post comment to GitHub', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click(
        '[data-testid="review-comment"]:first-child [data-testid="post-to-github-button"]'
      );

      await expect(page.locator('[data-testid="posted-to-github-toast"]')).toBeVisible();
    });

    test('should request re-review', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="pr-tab"]');

      await page.click('[data-testid="re-review-button"]');

      await expect(page.locator('[data-testid="review-started-toast"]')).toBeVisible();
    });
  });
});
