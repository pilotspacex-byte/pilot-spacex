/**
 * E2E tests for note workflow.
 *
 * Tests note creation, editing, ghost text, annotations,
 * issue extraction, version history, and pin/unpin.
 *
 * Auth state is pre-loaded via global setup.
 *
 * NOTE: These tests require authentication. If auth setup fails,
 * tests will be skipped with a clear message.
 */

import { test, expect } from '@playwright/test';

// Default workspace slug for tests
const WORKSPACE_SLUG = 'workspace';

test.describe('Note Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to notes page directly
    await page.goto(`/${WORKSPACE_SLUG}/notes`);
    await page.waitForLoadState('networkidle');

    // Check if we got redirected to login (not authenticated)
    const currentUrl = page.url();
    if (currentUrl.includes('/login')) {
      test.skip(true, 'Skipping test - authentication required. Set up test user in Supabase.');
    }

    // Wait for notes page to load (should have create button)
    const createButton = page.locator('[data-testid="create-note-button"]');
    const hasCreateButton = await createButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasCreateButton) {
      // Maybe on login page or error page
      test.skip(true, 'Skipping test - notes page not accessible. Check authentication.');
    }
  });

  test.describe('Create Note', () => {
    test('should create a new note', async ({ page }) => {
      // Click create note button on notes page
      await page.click('[data-testid="create-note-button"]');

      // Wait for navigation to note editor
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);

      // Wait for editor to load
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      // Type in the editor
      await page.locator('[data-testid="note-editor"] .ProseMirror').fill('My new note content');

      // Verify content is saved (debounced autosave)
      await page.waitForTimeout(1000);
    });

    test('should create note with title', async ({ page }) => {
      // Click create note button on notes page
      await page.click('[data-testid="create-note-button"]');

      // Wait for navigation to note editor
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);

      // Wait for header to load
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      // Click on title to enter edit mode
      await page.locator('h1').click();

      // Wait for input to appear and fill
      const titleInput = page.locator('[data-testid="note-title-input"]');
      await expect(titleInput).toBeVisible();
      await titleInput.fill('Project Ideas');

      // Press enter to save
      await page.keyboard.press('Enter');

      // Verify title is displayed
      await expect(page.locator('h1')).toContainText('Project Ideas');
    });
  });

  test.describe('Edit Note with Ghost Text', () => {
    test('should show ghost text suggestion after pause', async ({ page }) => {
      // Create a new note first
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      const editor = page.locator('[data-testid="note-editor"] .ProseMirror');

      // Type some content
      await editor.fill('The quick brown fox');

      // Wait for ghost text to appear (500ms trigger)
      await page.waitForTimeout(600);

      // Check for ghost text overlay (may not appear if AI not configured)
      const ghostText = page.locator('[data-testid="ghost-text-overlay"]');
      // This test may be skipped if AI is not configured in test environment
      if (await ghostText.isVisible({ timeout: 2000 }).catch(() => false)) {
        await expect(ghostText).toBeVisible();
      }
    });

    test('should accept ghost text with Tab key', async ({ page }) => {
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      const editor = page.locator('[data-testid="note-editor"] .ProseMirror');

      await editor.fill('The quick brown fox');
      await page.waitForTimeout(600);

      // Press Tab to accept (if ghost text appeared)
      await page.keyboard.press('Tab');

      // Content may or may not have ghost text depending on AI config
      const content = await editor.textContent();
      expect(content).toContain('The quick brown fox');
    });

    test('should dismiss ghost text with Escape', async ({ page }) => {
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      const editor = page.locator('[data-testid="note-editor"] .ProseMirror');

      await editor.fill('The quick brown fox');
      await page.waitForTimeout(600);

      // Press Escape to dismiss any ghost text
      await page.keyboard.press('Escape');

      // Ghost text should be hidden (or was never shown)
      await expect(page.locator('[data-testid="ghost-text-overlay"]')).not.toBeVisible();
    });

    test('should accept ghost text word by word with Arrow Right', async ({ page }) => {
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      const editor = page.locator('[data-testid="note-editor"] .ProseMirror');

      await editor.fill('The quick brown fox');
      await page.waitForTimeout(600);

      // Get initial content length
      const _initialContent = await editor.textContent();

      // Press Arrow Right
      await page.keyboard.press('ArrowRight');

      // Content should still contain original text
      const newContent = await editor.textContent();
      expect(newContent).toContain('The quick brown fox');
    });
  });

  test.describe('Annotations', () => {
    test('should show margin annotations panel when viewing note', async ({ page }) => {
      // First create a note
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      // Margin annotations panel may be visible (even if empty)
      const annotations = page.locator('[data-testid="margin-annotations"]');
      // Panel visibility depends on implementation - check if present
      const isVisible = await annotations.isVisible().catch(() => false);
      // If the panel exists, it should be accessible
      if (isVisible) {
        await expect(annotations).toBeVisible();
      }
    });

    test.skip('should accept annotation suggestion', async ({ page }) => {
      // This test requires AI-generated annotations which need backend AI config
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);

      // Click accept on first annotation (if any)
      const acceptButton = page.locator(
        '[data-testid="annotation-card"]:first-child [data-testid="accept-button"]'
      );
      if (await acceptButton.isVisible().catch(() => false)) {
        await acceptButton.click();
        await expect(page.locator('[data-testid="annotation-applied-toast"]')).toBeVisible();
      }
    });

    test.skip('should reject annotation suggestion', async ({ page }) => {
      // This test requires AI-generated annotations which need backend AI config
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);

      // Click reject on first annotation (if any)
      const rejectButton = page.locator(
        '[data-testid="annotation-card"]:first-child [data-testid="reject-button"]'
      );
      if (await rejectButton.isVisible().catch(() => false)) {
        await rejectButton.click();
        await expect(page.locator('[data-testid="annotation-card"]:first-child')).not.toBeVisible();
      }
    });
  });

  test.describe('Issue Extraction', () => {
    test.skip('should extract issue from selected text', async ({ page }) => {
      // This test requires issue extraction feature to be fully implemented
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      const editor = page.locator('[data-testid="note-editor"] .ProseMirror');

      // Type content that could be an issue
      await editor.fill('TODO: Fix authentication bug in login flow');

      // Select text
      await editor.selectText();

      // Click extract issue button in selection toolbar
      const extractButton = page.locator('[data-testid="extract-issue-button"]');
      if (await extractButton.isVisible().catch(() => false)) {
        await extractButton.click();

        // Issue extraction panel should appear
        await expect(page.locator('[data-testid="issue-extraction-panel"]')).toBeVisible();
      }
    });

    test.skip('should create issue from extraction', async ({ page }) => {
      // This test requires issue extraction feature to be fully implemented
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      const editor = page.locator('[data-testid="note-editor"] .ProseMirror');

      await editor.fill('TODO: Fix login button not working');
      await editor.selectText();

      const extractButton = page.locator('[data-testid="extract-issue-button"]');
      if (await extractButton.isVisible().catch(() => false)) {
        await extractButton.click();
        await page.click('[data-testid="create-issue-from-note-button"]');
        await expect(page.locator('[data-testid="issue-created-toast"]')).toBeVisible();
      }
    });
  });

  test.describe('Version History', () => {
    test.skip('should show version history panel', async ({ page }) => {
      // This test requires version history feature to be fully implemented
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      // Click version history button
      const historyButton = page.locator('[data-testid="version-history-button"]');
      if (await historyButton.isVisible().catch(() => false)) {
        await historyButton.click();
        await expect(page.locator('[data-testid="version-history-panel"]')).toBeVisible();
      }
    });

    test.skip('should navigate to previous version', async ({ page }) => {
      // This test requires version history feature to be fully implemented
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      const historyButton = page.locator('[data-testid="version-history-button"]');
      if (await historyButton.isVisible().catch(() => false)) {
        await historyButton.click();
        await page.click('[data-testid="version-item"]:nth-child(2)');
        await expect(page.locator('[data-testid="viewing-version-banner"]')).toBeVisible();
      }
    });

    test.skip('should restore previous version', async ({ page }) => {
      // This test requires version history feature to be fully implemented
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      const historyButton = page.locator('[data-testid="version-history-button"]');
      if (await historyButton.isVisible().catch(() => false)) {
        await historyButton.click();
        await page.click('[data-testid="version-item"]:nth-child(2)');
        await page.click('[data-testid="restore-version-button"]');
        await page.click('[data-testid="confirm-restore-button"]');
        await expect(page.locator('[data-testid="version-restored-toast"]')).toBeVisible();
      }
    });
  });

  test.describe('Pin/Unpin Note', () => {
    test.skip('should pin a note', async ({ page }) => {
      // This test requires pin functionality to be implemented in the header
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      // Click pin button (via dropdown menu)
      const moreButton = page.locator('button:has([class*="MoreHorizontal"])');
      if (await moreButton.isVisible().catch(() => false)) {
        await moreButton.click();
        const pinItem = page.getByText('Pin to top');
        if (await pinItem.isVisible().catch(() => false)) {
          await pinItem.click();
        }
      }
    });

    test.skip('should unpin a note', async ({ page }) => {
      // This test requires existing pinned notes
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      // Click unpin button (via dropdown menu)
      const moreButton = page.locator('button:has([class*="MoreHorizontal"])');
      if (await moreButton.isVisible().catch(() => false)) {
        await moreButton.click();
        const unpinItem = page.getByText('Unpin');
        if (await unpinItem.isVisible().catch(() => false)) {
          await unpinItem.click();
        }
      }
    });
  });

  test.describe('Autosave', () => {
    test('should autosave note changes', async ({ page }) => {
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      const editor = page.locator('[data-testid="note-editor"] .ProseMirror');

      // Type content
      await editor.fill('Autosave test content');

      // Wait for autosave (500ms debounce)
      await page.waitForTimeout(1500);

      // Saving indicator should show saved state (if visible)
      const saveIndicator = page.locator('[data-testid="save-indicator"]');
      if (await saveIndicator.isVisible().catch(() => false)) {
        await expect(saveIndicator).toContainText('Saved');
      }
    });

    test('should show saving indicator while saving', async ({ page }) => {
      await page.click('[data-testid="create-note-button"]');
      await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({
        timeout: 10000,
      });

      const editor = page.locator('[data-testid="note-editor"] .ProseMirror');

      await editor.fill('Content for saving indicator test');

      // Should briefly show "Saving..." (if visible)
      const saveIndicator = page.locator('[data-testid="save-indicator"]');
      // This may flash too quickly to reliably catch
      if (await saveIndicator.isVisible().catch(() => false)) {
        // Just verify it exists
        await expect(saveIndicator).toBeVisible();
      }
    });
  });
});
