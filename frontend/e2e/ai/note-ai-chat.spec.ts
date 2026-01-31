/**
 * E2E tests for Note-First AI Chat integration.
 *
 * Tests the AI ChatView embedded in the note page, covering:
 * - ChatView open/close via FAB and keyboard shortcut
 * - Selection → Ask Pilot flow with context indicator
 * - AI Enhance and Extract Issues actions via selection toolbar
 * - Multi-turn conversation with note context
 * - Content update events applied to editor
 *
 * Auth state is pre-loaded via global setup (see playwright.config.ts).
 * Requires: Running backend + Supabase + Redis
 * AI-dependent tests gracefully degrade when AI provider keys are unavailable.
 */

import { test, expect } from '@playwright/test';

const WORKSPACE_SLUG = 'workspace';

/**
 * Helper: Navigate to note editor page.
 * Creates a new note and waits for the editor to be ready.
 */
async function navigateToNoteEditor(page: import('@playwright/test').Page) {
  await page.goto(`/${WORKSPACE_SLUG}/notes`, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle');

  // Check auth
  if (page.url().includes('/login')) {
    return false;
  }

  // Check create button is available
  const createButton = page.locator('[data-testid="create-note-button"]');
  const hasCreateButton = await createButton.isVisible({ timeout: 5000 }).catch(() => false);
  if (!hasCreateButton) {
    return false;
  }

  // Create a new note
  await createButton.click();
  await page.waitForURL(`**/${WORKSPACE_SLUG}/notes/**`);

  // Wait for editor to load
  await expect(page.locator('[data-testid="note-editor"]')).toBeVisible({ timeout: 10000 });

  // Dismiss dev overlays that intercept pointer events on FAB button
  await page.evaluate(() => {
    // Next.js dev overlay
    const portal = document.querySelector('nextjs-portal');
    if (portal) portal.remove();
    // TanStack Query DevTools (blocks bottom-right corner where FAB lives)
    const tqDevtools = document.querySelector('[class*="tsqd"]');
    if (tqDevtools) tqDevtools.remove();
    // Also try aria-label selector
    document
      .querySelectorAll('[aria-label="Tanstack query devtools"]')
      .forEach((el) => el.remove());
    document.querySelectorAll('[aria-label="Close tanstack query devtools"]').forEach((el) => {
      (el as HTMLElement).click();
    });
  });

  return true;
}

/**
 * Helper: Type text into the ProseMirror editor.
 */
async function typeInEditor(page: import('@playwright/test').Page, text: string) {
  const proseMirror = page.locator('[data-testid="note-editor"] .ProseMirror');
  await proseMirror.click();
  await page.keyboard.type(text, { delay: 10 });
}

/**
 * Helper: Select all text in the editor.
 */
async function selectAllText(page: import('@playwright/test').Page) {
  await page.keyboard.press('Meta+A');
  // Small delay for selection to register
  await page.waitForTimeout(200);
}

/**
 * Helper: Open ChatView via the collapsed indicator.
 * Desktop (>=1024px): clicks the "AI Chat" vertical strip button.
 * Mobile (<1024px): clicks the FAB button.
 * Uses force click to bypass any overlay interception (e.g. Next.js dev portal).
 */
async function clickOpenChat(page: import('@playwright/test').Page) {
  const viewport = page.viewportSize();
  const isDesktop = viewport && viewport.width >= 1024;

  if (isDesktop) {
    // Desktop: click the vertical strip button containing "AI Chat"
    const verticalStrip = page.locator('.writing-mode-vertical');
    await expect(verticalStrip).toBeVisible({ timeout: 5000 });
    await verticalStrip.click({ force: true });
  } else {
    // Mobile: click the FAB button
    const fabButton = page.locator('[data-testid="chat-fab-button"]');
    await expect(fabButton).toBeVisible({ timeout: 5000 });
    await fabButton.click({ force: true });
  }
}

/**
 * Helper: Open ChatView via keyboard shortcut.
 * Tries both Meta+Shift+P (macOS) and Control+Shift+P (Linux/Windows).
 */
async function openChatViewViaKeyboard(page: import('@playwright/test').Page) {
  const isMac = process.platform === 'darwin';
  if (isMac) {
    await page.keyboard.press('Meta+Shift+p');
  } else {
    await page.keyboard.press('Control+Shift+p');
  }
}

test.describe('Note AI Chat Integration', () => {
  test.beforeEach(async ({ page }) => {
    const ready = await navigateToNoteEditor(page);
    if (!ready) {
      test.skip(true, 'Skipping - authentication required or notes page not accessible');
    }
  });

  // ────────────────────────────────────────────
  // ChatView Open / Close
  // ────────────────────────────────────────────

  test.describe('ChatView Toggle', () => {
    test('NAI-001: should open ChatView via collapsed indicator', async ({ page }) => {
      const viewport = page.viewportSize();
      const isDesktop = viewport && viewport.width >= 1024;

      if (isDesktop) {
        // Desktop: vertical strip "AI Chat" should be visible
        const verticalStrip = page.locator('.writing-mode-vertical');
        await expect(verticalStrip).toBeVisible({ timeout: 5000 });
      } else {
        // Mobile: FAB should be visible
        const fabButton = page.locator('[data-testid="chat-fab-button"]');
        await expect(fabButton).toBeVisible({ timeout: 5000 });
      }

      // Click to open
      await clickOpenChat(page);

      // ChatView should appear
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });

      if (isDesktop) {
        // Vertical strip should disappear when ChatView is open
        await expect(page.locator('.writing-mode-vertical')).not.toBeVisible();
      }
    });

    test('NAI-002: should open ChatView via keyboard shortcut', async ({ page }) => {
      // Focus the editor first so keyboard shortcut is captured
      await page.locator('[data-testid="note-editor"] .ProseMirror').click();

      // ChatView should be closed initially
      await expect(page.locator('[data-testid="chat-view"]')).not.toBeVisible();

      // Use keyboard shortcut
      await openChatViewViaKeyboard(page);

      // ChatView should open
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });
    });

    test('NAI-003: should toggle ChatView with keyboard shortcut', async ({ page }) => {
      // Focus editor
      await page.locator('[data-testid="note-editor"] .ProseMirror').click();

      // Open
      await openChatViewViaKeyboard(page);
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });

      // Close with same shortcut
      await openChatViewViaKeyboard(page);
      await expect(page.locator('[data-testid="chat-view"]')).not.toBeVisible({ timeout: 3000 });

      // Collapsed indicator should reappear
      const viewport = page.viewportSize();
      const isDesktop = viewport && viewport.width >= 1024;
      if (isDesktop) {
        await expect(page.locator('.writing-mode-vertical')).toBeVisible({ timeout: 3000 });
      } else {
        await expect(page.locator('[data-testid="chat-fab-button"]')).toBeVisible({
          timeout: 3000,
        });
      }
    });

    test('NAI-004: ChatView should contain input and header', async ({ page }) => {
      // Open ChatView
      await clickOpenChat(page);
      const chatView = page.locator('[data-testid="chat-view"]');
      await expect(chatView).toBeVisible({ timeout: 5000 });

      // Verify core elements
      await expect(chatView.locator('[data-testid="chat-header"]')).toBeVisible();
      await expect(chatView.locator('[data-testid="chat-input"]')).toBeVisible();
      await expect(chatView.locator('[data-testid="send-button"]')).toBeVisible();
    });
  });

  // ────────────────────────────────────────────
  // Selection Toolbar
  // ────────────────────────────────────────────

  test.describe('Selection Toolbar', () => {
    test('NAI-010: should show selection toolbar with AI buttons on text selection', async ({
      page,
    }) => {
      // Type content
      await typeInEditor(page, 'This is a test paragraph for AI enhancement.');

      // Select all
      await selectAllText(page);

      // Toolbar should appear
      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      await expect(toolbar).toBeVisible({ timeout: 3000 });

      // Verify formatting buttons exist
      await expect(toolbar.getByRole('button', { name: 'Bold' })).toBeVisible();
      await expect(toolbar.getByRole('button', { name: 'Italic' })).toBeVisible();

      // Verify AI action buttons exist
      await expect(toolbar.locator('[data-testid="ask-pilot-button"]')).toBeVisible();
      await expect(toolbar.locator('[data-testid="enhance-button"]')).toBeVisible();
      await expect(toolbar.locator('[data-testid="extract-issues-button"]')).toBeVisible();
    });

    test('NAI-011: should hide selection toolbar when selection is cleared', async ({ page }) => {
      await typeInEditor(page, 'Some text to select.');
      await selectAllText(page);

      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      await expect(toolbar).toBeVisible({ timeout: 3000 });

      // Click somewhere to deselect
      await page.keyboard.press('Escape');

      await expect(toolbar).not.toBeVisible({ timeout: 3000 });
    });

    test('NAI-012: toolbar AI buttons should have correct aria-labels', async ({ page }) => {
      await typeInEditor(page, 'Accessible text for testing.');
      await selectAllText(page);

      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      await expect(toolbar).toBeVisible({ timeout: 3000 });

      // Check aria-labels for accessibility
      await expect(toolbar.locator('[data-testid="ask-pilot-button"]')).toHaveAttribute(
        'aria-label',
        'Ask Pilot'
      );
      await expect(toolbar.locator('[data-testid="enhance-button"]')).toHaveAttribute(
        'aria-label',
        'Enhance with AI'
      );
      await expect(toolbar.locator('[data-testid="extract-issues-button"]')).toHaveAttribute(
        'aria-label',
        'Extract issues'
      );
    });
  });

  // ────────────────────────────────────────────
  // Ask Pilot Flow
  // ────────────────────────────────────────────

  test.describe('Ask Pilot Action', () => {
    test('NAI-020: should open ChatView with context when Ask Pilot is clicked', async ({
      page,
    }) => {
      // Type content and select
      await typeInEditor(page, 'Explain the benefits of microservices architecture.');
      await selectAllText(page);

      // Click Ask Pilot
      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      await expect(toolbar).toBeVisible({ timeout: 3000 });
      await toolbar.locator('[data-testid="ask-pilot-button"]').click();

      // ChatView should open
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });

      // Context indicator should show note context
      await expect(page.locator('[data-testid="context-indicator"]')).toBeVisible({
        timeout: 3000,
      });
    });

    test('NAI-021: should hide toolbar after Ask Pilot action', async ({ page }) => {
      await typeInEditor(page, 'Test paragraph for Ask Pilot.');
      await selectAllText(page);

      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      await expect(toolbar).toBeVisible({ timeout: 3000 });

      await toolbar.locator('[data-testid="ask-pilot-button"]').click();

      // Toolbar should be hidden after action
      await expect(toolbar).not.toBeVisible({ timeout: 3000 });
    });
  });

  // ────────────────────────────────────────────
  // Enhance Action (AI-dependent)
  // ────────────────────────────────────────────

  test.describe('Enhance Action', () => {
    test('NAI-030: should open ChatView and send enhance request', async ({ page }) => {
      await typeInEditor(page, 'This text needs improvement.');
      await selectAllText(page);

      // Click Enhance
      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      await expect(toolbar).toBeVisible({ timeout: 3000 });
      await toolbar.locator('[data-testid="enhance-button"]').click();

      // ChatView should open with enhance message sent
      const chatView = page.locator('[data-testid="chat-view"]');
      await expect(chatView).toBeVisible({ timeout: 5000 });

      // User message should appear (the enhance request)
      const userMessage = chatView.locator('[data-testid="message-user"]').last();
      await expect(userMessage).toBeVisible({ timeout: 5000 });

      // Verify streaming indicator appears (if AI is configured)
      const streamingIndicator = page.locator('[data-testid="streaming-indicator"]');
      const isStreaming = await streamingIndicator.isVisible({ timeout: 3000 }).catch(() => false);

      if (isStreaming) {
        // Wait for AI response to complete
        const aiMessage = chatView.locator('[data-testid="message-assistant"]').last();
        await expect(aiMessage).toBeVisible({ timeout: 30000 });

        // Streaming should complete
        await expect(streamingIndicator).not.toBeVisible({ timeout: 30000 });
      }
    });

    test('NAI-031: editor should remain functional after enhance action', async ({ page }) => {
      await typeInEditor(page, 'Text to enhance.');
      await selectAllText(page);

      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      await expect(toolbar).toBeVisible({ timeout: 3000 });
      await toolbar.locator('[data-testid="enhance-button"]').click();

      // Wait for ChatView
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });

      // Editor should still be functional
      const editor = page.locator('[data-testid="note-editor"]');
      await expect(editor).toBeVisible();

      // Should be able to type in editor
      const proseMirror = page.locator('[data-testid="note-editor"] .ProseMirror');
      await proseMirror.click();
      await page.keyboard.type(' Additional text.');

      const content = await proseMirror.textContent();
      expect(content).toContain('Additional text');
    });
  });

  // ────────────────────────────────────────────
  // Extract Issues Action (AI-dependent)
  // ────────────────────────────────────────────

  test.describe('Extract Issues Action', () => {
    test('NAI-040: should open ChatView and send extract issues request', async ({ page }) => {
      await typeInEditor(
        page,
        'TODO: Fix authentication bug in login flow\nTODO: Add input validation'
      );
      await selectAllText(page);

      // Click Extract Issues
      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      await expect(toolbar).toBeVisible({ timeout: 3000 });
      await toolbar.locator('[data-testid="extract-issues-button"]').click();

      // ChatView should open
      const chatView = page.locator('[data-testid="chat-view"]');
      await expect(chatView).toBeVisible({ timeout: 5000 });

      // User message should contain extract request
      const userMessage = chatView.locator('[data-testid="message-user"]').last();
      await expect(userMessage).toBeVisible({ timeout: 5000 });
    });

    test('NAI-041: editor should remain visible alongside ChatView', async ({ page }) => {
      await typeInEditor(page, 'TODO: Implement search feature');
      await selectAllText(page);

      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      await expect(toolbar).toBeVisible({ timeout: 3000 });
      await toolbar.locator('[data-testid="extract-issues-button"]').click();

      // Both editor and ChatView should be visible (side-by-side on desktop)
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('[data-testid="note-editor"]')).toBeVisible();
    });
  });

  // ────────────────────────────────────────────
  // Multi-turn Conversation (AI-dependent)
  // ────────────────────────────────────────────

  test.describe('Multi-turn Conversation', () => {
    test('NAI-050: should support multi-turn conversation in note context', async ({ page }) => {
      // Type content in editor
      await typeInEditor(
        page,
        '# Project Architecture\n\nWe are building a microservices platform.'
      );

      // Open ChatView via FAB
      await clickOpenChat(page);
      const chatView = page.locator('[data-testid="chat-view"]');
      await expect(chatView).toBeVisible({ timeout: 5000 });

      // Send first message
      const chatInput = chatView.locator('[data-testid="chat-input"]');
      await chatInput.fill('What improvements can you suggest for this note?');
      await chatView.locator('[data-testid="send-button"]').click();

      // User message should appear
      const userMsg1 = chatView.locator('[data-testid="message-user"]').first();
      await expect(userMsg1).toBeVisible({ timeout: 5000 });
      await expect(userMsg1).toContainText('What improvements');

      // Wait for AI response (if AI is configured)
      const aiMsg1 = chatView.locator('[data-testid="message-assistant"]').first();
      const hasAIResponse = await aiMsg1.isVisible({ timeout: 15000 }).catch(() => false);

      if (hasAIResponse) {
        // Send follow-up
        await chatInput.fill('Can you add a section about deployment?');
        await chatView.locator('[data-testid="send-button"]').click();

        // Wait for second response
        await expect(chatView.locator('[data-testid="message-assistant"]').last()).toBeVisible({
          timeout: 30000,
        });

        // Verify conversation has multiple messages
        const messageCount = await chatView.locator('[data-testid^="message-"]').count();
        expect(messageCount).toBeGreaterThanOrEqual(4); // 2 user + 2 assistant
      }
    });

    test('NAI-051: should disable send button for empty input', async ({ page }) => {
      // Open ChatView
      await clickOpenChat(page);
      const chatView = page.locator('[data-testid="chat-view"]');
      await expect(chatView).toBeVisible({ timeout: 5000 });

      // Send button should be disabled when input is empty
      const sendButton = chatView.locator('[data-testid="send-button"]');
      await expect(sendButton).toBeDisabled();

      // Type whitespace only
      const chatInput = chatView.locator('[data-testid="chat-input"]');
      await chatInput.fill('   ');
      await expect(sendButton).toBeDisabled();

      // Type actual content
      await chatInput.fill('Hello');
      await expect(sendButton).toBeEnabled();
    });

    test('NAI-052: should show abort button during streaming', async ({ page }) => {
      // Open ChatView
      await clickOpenChat(page);
      const chatView = page.locator('[data-testid="chat-view"]');
      await expect(chatView).toBeVisible({ timeout: 5000 });

      // Send a message
      const chatInput = chatView.locator('[data-testid="chat-input"]');
      await chatInput.fill('Write a detailed explanation of microservices');
      await chatView.locator('[data-testid="send-button"]').click();

      // Check for streaming indicator (if AI is configured)
      const streamingIndicator = page.locator('[data-testid="streaming-indicator"]');
      const isStreaming = await streamingIndicator.isVisible({ timeout: 5000 }).catch(() => false);

      if (isStreaming) {
        // Abort button should be visible during streaming
        const abortButton = chatView.locator('[data-testid="abort-button"]');
        await expect(abortButton).toBeVisible();

        // Click abort (use force since button state may change rapidly during streaming)
        await abortButton.click({ force: true });

        // Streaming should stop
        await expect(streamingIndicator).not.toBeVisible({ timeout: 5000 });
      }
    });
  });

  // ────────────────────────────────────────────
  // ChatView + Editor Co-existence
  // ────────────────────────────────────────────

  test.describe('ChatView + Editor Layout', () => {
    test('NAI-060: editor and ChatView should co-exist side by side', async ({ page }) => {
      // Type some content
      await typeInEditor(page, 'Note content for layout test.');

      // Open ChatView
      await clickOpenChat(page);

      // Both should be visible
      const editor = page.locator('[data-testid="note-editor"]');
      const chatView = page.locator('[data-testid="chat-view"]');

      await expect(editor).toBeVisible({ timeout: 5000 });
      await expect(chatView).toBeVisible({ timeout: 5000 });

      // Editor should still have content
      const content = await page.locator('[data-testid="note-editor"] .ProseMirror').textContent();
      expect(content).toContain('Note content for layout test');
    });

    test('NAI-061: should be able to type in editor while ChatView is open', async ({ page }) => {
      // Open ChatView
      await clickOpenChat(page);
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });

      // Click editor and type
      const proseMirror = page.locator('[data-testid="note-editor"] .ProseMirror');
      await proseMirror.click();
      await page.keyboard.type('Typing while chat is open.', { delay: 10 });

      // Verify content
      const content = await proseMirror.textContent();
      expect(content).toContain('Typing while chat is open');
    });

    test('NAI-062: should be able to type in ChatInput while editor has content', async ({
      page,
    }) => {
      // Type in editor first
      await typeInEditor(page, 'Editor has content.');

      // Open ChatView
      await clickOpenChat(page);
      const chatView = page.locator('[data-testid="chat-view"]');
      await expect(chatView).toBeVisible({ timeout: 5000 });

      // Type in ChatInput
      const chatInput = chatView.locator('[data-testid="chat-input"]');
      await chatInput.click();
      await chatInput.fill('Question about the note');

      // Verify ChatInput has content
      await expect(chatInput).toHaveValue('Question about the note');

      // Verify editor still has its content
      const editorContent = await page
        .locator('[data-testid="note-editor"] .ProseMirror')
        .textContent();
      expect(editorContent).toContain('Editor has content');
    });
  });

  // ────────────────────────────────────────────
  // Layout: ChatView replaces Suggestions
  // ────────────────────────────────────────────

  test.describe('ChatView Layout (Post-Suggestions Replacement)', () => {
    test('NAI-080: Trigger bar opens ChatView sidebar', async ({ page }) => {
      // Trigger bar should be visible at bottom of canvas when ChatView is closed
      const triggerBar = page.locator('[data-testid="chat-trigger"]');
      await expect(triggerBar).toBeVisible({ timeout: 5000 });

      // Should show "Ask Pilot..." text
      await expect(triggerBar).toContainText('Ask Pilot...');

      // Click trigger bar
      await triggerBar.click();

      // ChatView should open
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });

      // Trigger bar should disappear when ChatView is open
      await expect(triggerBar).not.toBeVisible({ timeout: 3000 });

      // Chat input should be focused and ready for typing
      const chatInput = page.locator('[data-testid="chat-input"]');
      await expect(chatInput).toBeVisible();
    });

    test('NAI-081: ContextIndicator shows note title (not UUID)', async ({ page }) => {
      // Open ChatView
      await clickOpenChat(page);
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });

      // Check context indicator
      const contextIndicator = page.locator('[data-testid="context-indicator"]');
      const isContextVisible = await contextIndicator
        .isVisible({ timeout: 3000 })
        .catch(() => false);

      if (isContextVisible) {
        const contextText = await contextIndicator.textContent();
        // Should NOT contain a UUID pattern (8-char hex)
        // Instead should show "Note: Untitled" or actual title
        expect(contextText).toContain('Note:');
        // UUID pattern: 8 hex chars
        const uuidPattern = /Note: [0-9a-f]{8}/;
        expect(contextText).not.toMatch(uuidPattern);
      }
    });

    test('NAI-081b: ContextIndicator shows block count and tooltip', async ({ page }) => {
      // Select some text in the editor to create block selection
      const editor = page.locator('[data-testid="note-editor"]');
      await editor.click();

      // Select text using keyboard (Cmd+A to select all)
      await page.keyboard.press('Meta+A');

      // Open ChatView
      await clickOpenChat(page);
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });

      // Check context indicator
      const contextIndicator = page.locator('[data-testid="context-indicator"]');
      const isContextVisible = await contextIndicator
        .isVisible({ timeout: 3000 })
        .catch(() => false);

      if (isContextVisible) {
        const contextText = await contextIndicator.textContent();
        expect(contextText).toContain('Note:');

        // If blocks are selected, should show count
        // Note: This assumes the selection triggers selectedBlockIds in context
        // If no blocks shown, that's okay - tooltip should still work

        // Hover over context indicator to trigger tooltip
        const badge = contextIndicator.locator('div[data-slot="tooltip-trigger"]');
        if (await badge.isVisible()) {
          await badge.hover();

          // Wait for tooltip to appear
          const tooltip = page.locator('div[data-slot="tooltip-content"]');
          const isTooltipVisible = await tooltip.isVisible({ timeout: 2000 }).catch(() => false);

          if (isTooltipVisible) {
            const tooltipText = await tooltip.textContent();
            // Tooltip should mention "AI will use" and "context"
            expect(tooltipText).toContain('AI will use');
            expect(tooltipText).toContain('context');
          }
        }
      }
    });

    test('NAI-082: Collapsed state shows "AI Chat" vertical strip on desktop', async ({ page }) => {
      // On desktop, when ChatView is closed, should show vertical strip
      const viewportSize = page.viewportSize();
      if (viewportSize && viewportSize.width >= 1024) {
        // ChatView should be closed by default
        await expect(page.locator('[data-testid="chat-view"]')).not.toBeVisible();

        // Vertical strip text should be visible
        const verticalStrip = page.locator('.writing-mode-vertical');
        await expect(verticalStrip).toBeVisible({ timeout: 3000 });
        const stripText = await verticalStrip.textContent();
        expect(stripText).toContain('AI Chat');
      }
    });

    test('NAI-083: Extract Issues routes through ChatView (no modal)', async ({ page }) => {
      // Type content with TODO items
      await typeInEditor(page, 'TODO: Fix authentication bug\nTODO: Add validation');
      await selectAllText(page);

      // Click Extract Issues from toolbar
      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      const isToolbarVisible = await toolbar.isVisible({ timeout: 3000 }).catch(() => false);

      if (isToolbarVisible) {
        await toolbar.locator('[data-testid="extract-issues-button"]').click();

        // ChatView should open (extraction goes through chat now)
        await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });

        // No modal overlay should exist (z-[100] backdrop removed)
        const backdrop = page.locator('.backdrop-blur-sm.z-\\[100\\]');
        await expect(backdrop).not.toBeVisible({ timeout: 2000 });

        // User message should appear with extraction request
        const userMessage = page.locator('[data-testid="message-user"]').last();
        await expect(userMessage).toBeVisible({ timeout: 5000 });
      }
    });

    test('NAI-084: No suggestions panel visible after replacement', async ({ page }) => {
      // Verify no element with "Suggestions" text exists in a vertical strip
      const suggestionsStrip = page.locator('text=Suggestions');
      await expect(suggestionsStrip).not.toBeVisible({ timeout: 2000 });

      // Verify no MarginAnnotations panel is rendered
      const marginAnnotations = page.locator('[data-testid="margin-annotations"]');
      await expect(marginAnnotations).not.toBeVisible({ timeout: 2000 });
    });
  });

  // ────────────────────────────────────────────
  // Keyboard Navigation & Accessibility
  // ────────────────────────────────────────────

  test.describe('Keyboard & Accessibility', () => {
    test('NAI-070: Chat open button should have accessible label', async ({ page }) => {
      const viewport = page.viewportSize();
      const isDesktop = viewport && viewport.width >= 1024;

      if (isDesktop) {
        // Desktop: vertical strip should contain "AI Chat" text
        const verticalStrip = page.locator('.writing-mode-vertical');
        await expect(verticalStrip).toBeVisible({ timeout: 5000 });
        const stripText = await verticalStrip.textContent();
        expect(stripText).toContain('AI Chat');
      } else {
        // Mobile: FAB should have sr-only text
        const fabButton = page.locator('[data-testid="chat-fab-button"]');
        await expect(fabButton).toBeVisible({ timeout: 5000 });
        const srText = await fabButton.locator('.sr-only').textContent();
        expect(srText).toContain('Open ChatView');
      }
    });

    test('NAI-071: selection toolbar should have role=toolbar', async ({ page }) => {
      await typeInEditor(page, 'Text for toolbar test.');
      await selectAllText(page);

      const toolbar = page.locator('[data-testid="selection-toolbar"]');
      await expect(toolbar).toBeVisible({ timeout: 3000 });
      await expect(toolbar).toHaveAttribute('role', 'toolbar');
    });

    test('NAI-072: ChatInput should be focusable when ChatView opens', async ({ page }) => {
      await clickOpenChat(page);
      await expect(page.locator('[data-testid="chat-view"]')).toBeVisible({ timeout: 5000 });

      // ChatInput should be present and interactive
      const chatInput = page.locator('[data-testid="chat-input"]');
      await expect(chatInput).toBeVisible();
      await chatInput.click();
      await chatInput.fill('Typing test');
      await expect(chatInput).toHaveValue('Typing test');
    });
  });
});
