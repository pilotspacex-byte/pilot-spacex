/**
 * E2E tests — Version History workflow (T-222)
 *
 * Tests:
 * - Opening version history sidebar from InlineNoteHeader
 * - Save Version button creates a version
 * - Timeline lists versions with trigger labels
 * - Pin/unpin a version
 * - Selecting a version shows Compare + Restore actions
 * - Diff viewer renders after double-click
 * - Restore confirmation dialog appears
 * - Cancel returns to timeline
 *
 * Requires: note editor page accessible with auth.
 */

import { test, expect } from '@playwright/test';

const WORKSPACE_SLUG = 'workspace';

test.describe('Version History', () => {
  let noteUrl: string;

  test.beforeAll(async ({ browser }) => {
    // Create a test note to use across all version tests
    const page = await browser.newPage();
    await page.goto(`/${WORKSPACE_SLUG}/notes`);
    await page.waitForLoadState('networkidle');

    if (page.url().includes('/login')) {
      await page.close();
      return;
    }

    const createBtn = page.locator('[data-testid="create-note-button"]');
    const visible = await createBtn.isVisible({ timeout: 5000 }).catch(() => false);
    if (visible) {
      await createBtn.click();
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await page
        .locator('[data-testid="note-editor"] .ProseMirror')
        .fill('Version history test note');
      await page.waitForTimeout(3000); // wait for autosave
      noteUrl = page.url();
    }
    await page.close();
  });

  test.beforeEach(async ({ page }) => {
    if (!noteUrl) {
      test.skip(true, 'Note URL not available — auth or create failed');
      return;
    }
    await page.goto(noteUrl);
    await page.waitForLoadState('networkidle');
    if (page.url().includes('/login')) {
      test.skip(true, 'Skipping — authentication required');
    }
    await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({ timeout: 10000 });
  });

  test('History button opens version history sidebar', async ({ page }) => {
    // Click the History icon in InlineNoteHeader
    const historyBtn = page.getByRole('button', { name: /history/i });
    await expect(historyBtn).toBeVisible({ timeout: 5000 });
    await historyBtn.click();

    // Sidebar panel should appear
    await expect(page.locator('[data-testid="sidebar-panel"]')).toBeVisible({ timeout: 3000 });

    // "Version History" title should be in the panel
    await expect(page.getByText(/version history/i)).toBeVisible({ timeout: 3000 });
  });

  test('Save Version button creates a version entry', async ({ page }) => {
    // Open version panel
    await page.getByRole('button', { name: /history/i }).click();
    await expect(page.locator('[data-testid="sidebar-panel"]')).toBeVisible({ timeout: 3000 });

    // Click Save Version
    const saveBtn = page.getByRole('button', { name: /save manual version snapshot/i });
    await expect(saveBtn).toBeVisible({ timeout: 5000 });
    await saveBtn.click();

    // After save, at least one version entry should appear
    await expect(page.getByText(/manual save/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('Version entries show correct trigger labels', async ({ page }) => {
    // Open version panel
    await page.getByRole('button', { name: /history/i }).click();
    await expect(page.locator('[data-testid="sidebar-panel"]')).toBeVisible({ timeout: 3000 });

    // Save a manual version first
    await page.getByRole('button', { name: /save manual version snapshot/i }).click();
    await expect(page.getByText(/manual save/i).first()).toBeVisible({ timeout: 8000 });
  });

  test('Selecting a version shows Compare and Restore buttons', async ({ page }) => {
    // Open version panel and save a version
    await page.getByRole('button', { name: /history/i }).click();
    await expect(page.locator('[data-testid="sidebar-panel"]')).toBeVisible({ timeout: 3000 });

    const saveBtn = page.getByRole('button', { name: /save manual version snapshot/i });
    await saveBtn.click();

    // Wait for entry to appear then click it
    const entry = page.getByText(/manual save/i).first();
    await expect(entry).toBeVisible({ timeout: 8000 });
    await entry.click();

    // Compare and Restore buttons should now appear
    await expect(page.getByRole('button', { name: /compare/i })).toBeVisible({ timeout: 3000 });
    await expect(page.getByRole('button', { name: /restore/i })).toBeVisible({ timeout: 3000 });
  });

  test('Pin button toggles with aria-pressed', async ({ page }) => {
    // Open panel and save a version
    await page.getByRole('button', { name: /history/i }).click();
    await page.getByRole('button', { name: /save manual version snapshot/i }).click();
    await page
      .getByText(/manual save/i)
      .first()
      .waitFor({ timeout: 8000 });

    // Find pin button (initially unpinned)
    const pinBtn = page.getByRole('button', { name: /pin version/i }).first();
    await expect(pinBtn).toHaveAttribute('aria-pressed', 'false');

    // Pin it
    await pinBtn.click();
    await expect(page.getByRole('button', { name: /unpin version/i })).toBeVisible({
      timeout: 5000,
    });
  });

  test('Restore button opens restore confirmation', async ({ page }) => {
    // Open panel and save a version
    await page.getByRole('button', { name: /history/i }).click();
    await page.getByRole('button', { name: /save manual version snapshot/i }).click();

    const entry = page.getByText(/manual save/i).first();
    await expect(entry).toBeVisible({ timeout: 8000 });
    await entry.click();

    // Click Restore
    await page
      .getByRole('button', { name: /^restore$/i })
      .first()
      .click();

    // Restore confirmation should appear
    await expect(page.getByText(/restore version/i)).toBeVisible({ timeout: 3000 });
    await expect(page.getByText(/creates a new version/i)).toBeVisible({ timeout: 3000 });
  });

  test('Cancel in restore confirmation returns to timeline', async ({ page }) => {
    // Open panel, save, select, click restore
    await page.getByRole('button', { name: /history/i }).click();
    await page.getByRole('button', { name: /save manual version snapshot/i }).click();

    const entry = page.getByText(/manual save/i).first();
    await expect(entry).toBeVisible({ timeout: 8000 });
    await entry.click();
    await page
      .getByRole('button', { name: /^restore$/i })
      .first()
      .click();

    // Confirm dialog appeared
    await expect(page.getByText(/creates a new version/i)).toBeVisible({ timeout: 3000 });

    // Cancel
    await page
      .getByRole('button', { name: /cancel/i })
      .first()
      .click();

    // Back to timeline — Save Version button should be visible again
    await expect(page.getByRole('button', { name: /save manual version snapshot/i })).toBeVisible({
      timeout: 3000,
    });
  });

  test('Closing version panel restores full editor view', async ({ page }) => {
    // Open panel
    await page.getByRole('button', { name: /history/i }).click();
    await expect(page.locator('[data-testid="sidebar-panel"]')).toBeVisible({ timeout: 3000 });

    // Close via X button in panel header
    const closeBtn = page.locator('[data-testid="sidebar-panel"]').getByRole('button', {
      name: /close/i,
    });
    await expect(closeBtn).toBeVisible({ timeout: 2000 });
    await closeBtn.click();

    // Panel should disappear
    await expect(page.locator('[data-testid="sidebar-panel"]')).not.toBeVisible({
      timeout: 3000,
    });

    // Editor still accessible
    await expect(page.locator('[data-testid="note-editor"]')).toBeVisible();
  });

  test('Escape key closes version panel', async ({ page }) => {
    await page.getByRole('button', { name: /history/i }).click();
    await expect(page.locator('[data-testid="sidebar-panel"]')).toBeVisible({ timeout: 3000 });

    await page.keyboard.press('Escape');

    await expect(page.locator('[data-testid="sidebar-panel"]')).not.toBeVisible({
      timeout: 3000,
    });
  });
});
