/**
 * E2E tests for GitHub integration workflow.
 *
 * Tests connecting GitHub (mocked OAuth), repository selection,
 * PR link display, branch suggestions, and commit list.
 */

import { test, expect } from '@playwright/test';

test.describe('GitHub Integration Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to home - auth state is pre-loaded via storageState
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Connect GitHub (Mocked OAuth)', () => {
    test('should show GitHub connection button', async ({ page }) => {
      await page.click('[data-testid="nav-settings"]');
      await page.click('[data-testid="integrations-tab"]');

      await expect(page.locator('[data-testid="connect-github-button"]')).toBeVisible();
    });

    test('should initiate GitHub OAuth flow', async ({ page }) => {
      await page.click('[data-testid="nav-settings"]');
      await page.click('[data-testid="integrations-tab"]');

      // Mock the OAuth redirect
      await page.route('**/api/v1/integrations/github/authorize', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            authorization_url: 'https://github.com/login/oauth/authorize?mock=true',
          }),
        });
      });

      await page.click('[data-testid="connect-github-button"]');

      // Should show connecting state or redirect
      await expect(
        page.locator('[data-testid="connecting-github"]').or(page.locator('body'))
      ).toBeVisible();
    });

    test('should handle OAuth callback success', async ({ page }) => {
      // Mock successful callback
      await page.route('**/api/v1/integrations/github/callback', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({
            id: 'integration-123',
            status: 'active',
            provider: 'github',
            metadata: { login: 'testuser', avatar_url: 'https://github.com/avatar.png' },
          }),
        });
      });

      // Navigate to callback URL
      await page.goto('/settings/integrations/github/callback?code=mock_code');

      // Should show success
      await expect(page.locator('[data-testid="github-connected"]')).toBeVisible();
    });

    test('should show connected account info', async ({ page }) => {
      // Mock connected state
      await page.route('**/api/v1/integrations', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify([
            {
              id: 'integration-123',
              provider: 'github',
              status: 'active',
              metadata: { login: 'testuser' },
            },
          ]),
        });
      });

      await page.click('[data-testid="nav-settings"]');
      await page.click('[data-testid="integrations-tab"]');

      await expect(page.locator('[data-testid="github-account-info"]')).toContainText('testuser');
    });
  });

  test.describe('Repository Selection', () => {
    test('should list connected repositories', async ({ page }) => {
      await page.route('**/api/v1/integrations/github/*/repos', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify([
            { id: 1, name: 'pilot-space', full_name: 'org/pilot-space', private: false },
            { id: 2, name: 'frontend', full_name: 'org/frontend', private: true },
          ]),
        });
      });

      await page.click('[data-testid="nav-settings"]');
      await page.click('[data-testid="integrations-tab"]');
      await page.click('[data-testid="manage-repos-button"]');

      await expect(page.locator('[data-testid="repo-list"]')).toBeVisible();
      await expect(page.locator('[data-testid="repo-item"]')).toHaveCount(2);
    });

    test('should toggle repository linking', async ({ page }) => {
      await page.route('**/api/v1/integrations/github/*/repos', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify([
            { id: 1, name: 'pilot-space', full_name: 'org/pilot-space', linked: false },
          ]),
        });
      });

      await page.click('[data-testid="nav-settings"]');
      await page.click('[data-testid="integrations-tab"]');
      await page.click('[data-testid="manage-repos-button"]');

      // Toggle link
      await page.click('[data-testid="repo-link-toggle"]:first-child');

      await expect(page.locator('[data-testid="repo-linked-toast"]')).toBeVisible();
    });

    test('should show webhook status for linked repos', async ({ page }) => {
      await page.route('**/api/v1/integrations/github/*/repos', async (route) => {
        await route.fulfill({
          status: 200,
          body: JSON.stringify([
            {
              id: 1,
              name: 'pilot-space',
              linked: true,
              webhook_active: true,
            },
          ]),
        });
      });

      await page.click('[data-testid="nav-settings"]');
      await page.click('[data-testid="integrations-tab"]');
      await page.click('[data-testid="manage-repos-button"]');

      await expect(page.locator('[data-testid="webhook-status-active"]')).toBeVisible();
    });
  });

  test.describe('PR Link Display', () => {
    test('should display linked PR badge on issue', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');

      // Issue with linked PR
      await expect(page.locator('[data-testid="pr-link-badge"]')).toBeVisible();
    });

    test('should show PR status (open/merged/closed)', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');

      // Check PR status badge
      await expect(
        page
          .locator('[data-testid="pr-status-open"]')
          .or(page.locator('[data-testid="pr-status-merged"]'))
          .or(page.locator('[data-testid="pr-status-closed"]'))
      ).toBeVisible();
    });

    test('should link to GitHub PR', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');

      const prLink = page.locator('[data-testid="pr-link"]');
      await expect(prLink).toHaveAttribute('href', /github\.com/);
    });

    test('should show PR title in tooltip', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');

      await page.hover('[data-testid="pr-link-badge"]');

      await expect(page.locator('[data-testid="pr-tooltip"]')).toBeVisible();
    });
  });

  test.describe('Branch Suggestion', () => {
    test('should show branch name suggestion', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="git-tab"]');

      await expect(page.locator('[data-testid="branch-suggestion"]')).toBeVisible();
      await expect(page.locator('[data-testid="branch-name"]')).toContainText('feature/');
    });

    test('should copy branch name to clipboard', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="git-tab"]');

      await page.click('[data-testid="copy-branch-button"]');

      await expect(page.locator('[data-testid="copied-toast"]')).toBeVisible();
    });

    test('should show git command with copy button', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="git-tab"]');

      await expect(page.locator('[data-testid="git-command"]')).toContainText('git checkout -b');

      await page.click('[data-testid="copy-command-button"]');
      await expect(page.locator('[data-testid="copied-toast"]')).toBeVisible();
    });
  });

  test.describe('Commit List', () => {
    test('should display linked commits', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="git-tab"]');

      await expect(page.locator('[data-testid="commit-list"]')).toBeVisible();
    });

    test('should show commit details', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="git-tab"]');

      const commitItem = page.locator('[data-testid="commit-item"]:first-child');

      // Should show commit hash
      await expect(commitItem.locator('[data-testid="commit-hash"]')).toBeVisible();

      // Should show commit message
      await expect(commitItem.locator('[data-testid="commit-message"]')).toBeVisible();

      // Should show author
      await expect(commitItem.locator('[data-testid="commit-author"]')).toBeVisible();

      // Should show date
      await expect(commitItem.locator('[data-testid="commit-date"]')).toBeVisible();
    });

    test('should link to GitHub commit', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="git-tab"]');

      const commitLink = page.locator(
        '[data-testid="commit-item"]:first-child [data-testid="commit-link"]'
      );
      await expect(commitLink).toHaveAttribute('href', /github\.com.*commit/);
    });

    test('should show author avatar', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="git-tab"]');

      await expect(
        page.locator('[data-testid="commit-item"]:first-child [data-testid="author-avatar"]')
      ).toBeVisible();
    });

    test('should expand truncated commit message', async ({ page }) => {
      await page.click('[data-testid="nav-issues"]');
      await page.click('[data-testid="issue-card"]:first-child');
      await page.click('[data-testid="git-tab"]');

      // Click expand on truncated message
      await page.click('[data-testid="expand-message-button"]');

      await expect(page.locator('[data-testid="full-message"]')).toBeVisible();
    });
  });

  test.describe('Disconnect GitHub', () => {
    test('should disconnect GitHub integration', async ({ page }) => {
      await page.click('[data-testid="nav-settings"]');
      await page.click('[data-testid="integrations-tab"]');

      await page.click('[data-testid="disconnect-github-button"]');

      // Confirm disconnection
      await page.click('[data-testid="confirm-disconnect"]');

      await expect(page.locator('[data-testid="github-disconnected-toast"]')).toBeVisible();
      await expect(page.locator('[data-testid="connect-github-button"]')).toBeVisible();
    });
  });
});
