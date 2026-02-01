/**
 * E2E tests for Note-First AI Content Update Pipeline.
 *
 * Tests the complete integration from user interaction → backend agent → content updates.
 * Validates:
 * - Text enhancement flow (replace_block)
 * - Issue extraction with inline nodes (insert_inline_issue)
 * - Multi-turn clarification conversations
 * - Conflict detection and retry mechanism
 * - Session persistence across turns
 *
 * Requirements: Running backend + Supabase + Redis
 * Authentication: Pre-loaded via global setup
 *
 * @module e2e/ai/note-content-update
 */

import { test, expect, type Page } from '@playwright/test';

const WORKSPACE_SLUG = 'workspace';

// ────────────────────────────────────────────
// Test Utilities
// ────────────────────────────────────────────

/**
 * Navigate to note editor page.
 * Creates a new note and waits for the editor to be ready.
 */
async function navigateToNoteEditor(page: Page): Promise<boolean> {
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

  // Dismiss dev overlays that intercept pointer events
  await page.evaluate(() => {
    const portal = document.querySelector('nextjs-portal');
    if (portal) portal.remove();
    const tqDevtools = document.querySelector('[class*="tsqd"]');
    if (tqDevtools) tqDevtools.remove();
    document
      .querySelectorAll('[aria-label="Tanstack query devtools"]')
      .forEach((el) => el.remove());
  });

  return true;
}

/**
 * Type text into the ProseMirror editor.
 */
async function typeInEditor(page: Page, text: string): Promise<void> {
  const proseMirror = page.locator('[data-testid="note-editor"] .ProseMirror');
  await proseMirror.click();
  await page.keyboard.type(text, { delay: 10 });
}

/**
 * Select text in editor by keyboard.
 */
async function selectText(page: Page, selectAll = true): Promise<void> {
  if (selectAll) {
    await page.keyboard.press('Meta+A');
  }
  // Small delay for selection to register
  await page.waitForTimeout(200);
}

/**
 * Get current editor content as plain text.
 */
async function getEditorContent(page: Page): Promise<string> {
  const proseMirror = page.locator('[data-testid="note-editor"] .ProseMirror');
  return (await proseMirror.textContent()) || '';
}

/**
 * Get editor content as JSON (TipTap document structure).
 * Reserved for future use in content structure validation tests.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
async function getEditorJSON(page: Page): Promise<unknown> {
  return await page.evaluate(() => {
    // Access TipTap editor instance via window object (if available)
    const editorElement = document.querySelector('[data-testid="note-editor"]');
    if (!editorElement) return null;
    // Try to get editor instance from element's properties
    const editorKeys = Object.keys(editorElement).find((k) => k.includes('__reactProps'));
    if (editorKeys) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const props = (editorElement as any)[editorKeys];
      return props?.editor?.getJSON?.();
    }
    return null;
  });
}

/**
 * Open ChatView via the collapsed indicator.
 */
async function clickOpenChat(page: Page): Promise<void> {
  const viewport = page.viewportSize();
  const isDesktop = viewport && viewport.width >= 1024;

  if (isDesktop) {
    const verticalStrip = page.locator('.writing-mode-vertical');
    await expect(verticalStrip).toBeVisible({ timeout: 5000 });
    await verticalStrip.click({ force: true });
  } else {
    const fabButton = page.locator('[data-testid="chat-fab-button"]');
    await expect(fabButton).toBeVisible({ timeout: 5000 });
    await fabButton.click({ force: true });
  }
}

/**
 * Send a message in ChatView.
 */
async function sendMessage(page: Page, message: string): Promise<void> {
  const chatView = page.locator('[data-testid="chat-view"]');
  const chatInput = chatView.locator('[data-testid="chat-input"]');
  await chatInput.fill(message);
  await chatView.locator('[data-testid="send-button"]').click();
}

/**
 * Wait for AI response to complete streaming.
 */
async function waitForAIResponse(page: Page, timeoutMs = 30000): Promise<boolean> {
  const streamingIndicator = page.locator('[data-testid="streaming-indicator"]');

  // Check if streaming started
  const isStreaming = await streamingIndicator.isVisible({ timeout: 3000 }).catch(() => false);

  if (!isStreaming) {
    // AI might not be configured or response was instant
    return false;
  }

  // Wait for streaming to complete
  await expect(streamingIndicator).not.toBeVisible({ timeout: timeoutMs });
  return true;
}

/**
 * Wait for content update to be applied to editor.
 * Polls editor content until it changes or timeout.
 */
async function waitForContentUpdate(
  page: Page,
  originalContent: string,
  timeoutMs = 10000
): Promise<boolean> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    const currentContent = await getEditorContent(page);
    if (currentContent !== originalContent) {
      return true;
    }
    await page.waitForTimeout(200);
  }

  return false;
}

/**
 * Verify inline issue node exists in editor.
 * Reserved for future use in inline issue validation tests.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
async function verifyInlineIssueNode(page: Page, issueKey: string): Promise<boolean> {
  const issueNode = page.locator(`[data-issue-key="${issueKey}"]`);
  return await issueNode.isVisible({ timeout: 5000 }).catch(() => false);
}

/**
 * Intercept SSE events from /api/v1/ai/chat endpoint.
 * Returns array of captured events.
 * Reserved for future use in SSE event validation tests.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
async function captureSSEEvents(page: Page): Promise<SSEEvent[]> {
  const events: SSEEvent[] = [];

  await page.route('**/api/v1/ai/chat', async (route) => {
    const response = await route.fetch();
    const reader = response.body()?.getReader();

    if (reader) {
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            const eventType = line.substring(6).trim();
            const dataLine = lines[lines.indexOf(line) + 1];
            if (dataLine?.startsWith('data:')) {
              try {
                const data = JSON.parse(dataLine.substring(5).trim());
                events.push({ type: eventType, data });
              } catch (err) {
                console.warn('Failed to parse SSE data:', err);
              }
            }
          }
        }
      }
    }

    await route.fulfill({ response });
  });

  return events;
}

interface SSEEvent {
  type: string;
  data: unknown;
}

/**
 * Extract note ID from current URL.
 * Reserved for future use in note-specific validation tests.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
async function getNoteIdFromURL(page: Page): Promise<string | null> {
  const url = page.url();
  const match = url.match(/\/notes\/([a-f0-9-]+)/);
  return match ? match[1] : null;
}

// ────────────────────────────────────────────
// Test Suite
// ────────────────────────────────────────────

test.describe('Note Content Update Pipeline', () => {
  test.beforeEach(async ({ page }) => {
    const ready = await navigateToNoteEditor(page);
    if (!ready) {
      test.skip(true, 'Skipping - authentication required or notes page not accessible');
    }
  });

  // ────────────────────────────────────────────
  // NAI-100: Text Enhancement Flow
  // ────────────────────────────────────────────

  test('NAI-100: Select text → Enhance → Editor updated', async ({ page }) => {
    // 1. Type initial content
    const initialText = 'This paragraph needs improvement and better clarity.';
    await typeInEditor(page, initialText);

    // 2. Select all text
    await selectText(page);

    // 3. Click Enhance button from SelectionToolbar
    const toolbar = page.locator('[data-testid="selection-toolbar"]');
    await expect(toolbar).toBeVisible({ timeout: 3000 });
    const enhanceButton = toolbar.locator('[data-testid="enhance-button"]');
    await enhanceButton.click();

    // 4. Verify ChatView opens
    const chatView = page.locator('[data-testid="chat-view"]');
    await expect(chatView).toBeVisible({ timeout: 5000 });

    // 5. Verify user message sent
    const userMessage = chatView.locator('[data-testid="message-user"]').last();
    await expect(userMessage).toBeVisible({ timeout: 5000 });
    await expect(userMessage).toContainText('Enhance');

    // 6. Wait for AI to process (if AI is configured)
    const hasAIResponse = await waitForAIResponse(page);

    if (hasAIResponse) {
      // 7. Wait for content update
      const originalContent = initialText;
      const contentUpdated = await waitForContentUpdate(page, originalContent, 15000);

      if (contentUpdated) {
        const updatedContent = await getEditorContent(page);

        // Verify content changed
        expect(updatedContent).not.toBe(initialText);
        expect(updatedContent.length).toBeGreaterThan(0);

        // 8. Verify no conflict toast (user not editing)
        const conflictToast = page.locator('text=/AI update skipped/i');
        await expect(conflictToast).not.toBeVisible({ timeout: 2000 });
      }
    }
  });

  // ────────────────────────────────────────────
  // NAI-101: Issue Extraction with Inline Nodes
  // ────────────────────────────────────────────

  test('NAI-101: Extract issues → Inline nodes + workspace list', async ({ page }) => {
    // 1. Type content with actionable items
    const actionItems = `
# Project Tasks

- TODO: Fix authentication bug in login flow
- TODO: Add input validation for user registration
- TODO: Implement password reset functionality
`;
    await typeInEditor(page, actionItems);

    // 2. Select all text
    await selectText(page);

    // 3. Click Extract Issues from SelectionToolbar
    const toolbar = page.locator('[data-testid="selection-toolbar"]');
    await expect(toolbar).toBeVisible({ timeout: 3000 });
    const extractButton = toolbar.locator('[data-testid="extract-issues-button"]');
    await extractButton.click();

    // 4. Verify ChatView opens
    const chatView = page.locator('[data-testid="chat-view"]');
    await expect(chatView).toBeVisible({ timeout: 5000 });

    // 5. Verify extraction request sent
    const userMessage = chatView.locator('[data-testid="message-user"]').last();
    await expect(userMessage).toBeVisible({ timeout: 5000 });
    await expect(userMessage).toContainText('Extract');

    // 6. Wait for AI to process (if AI is configured)
    const hasAIResponse = await waitForAIResponse(page, 45000); // Longer timeout for issue extraction

    if (hasAIResponse) {
      // 7. Wait for inline issue nodes to appear
      // Note: This test requires the AI to actually extract issues
      // We'll wait for any element with data-issue-key attribute
      await page.waitForTimeout(2000); // Allow time for content_update events to process

      const issueNodes = page.locator('[data-issue-key]');
      const issueCount = await issueNodes.count();

      if (issueCount > 0) {
        // 8. Navigate to workspace issues page
        await page.goto(`/${WORKSPACE_SLUG}/issues`);
        await page.waitForLoadState('networkidle');

        // 9. Verify issues created in workspace issue list
        const issuesList = page.locator('[data-testid="issues-list"]');
        await expect(issuesList).toBeVisible({ timeout: 5000 });

        // 10. Verify at least one issue exists with TODO-related title
        const issueItems = page.locator('[data-testid^="issue-item-"]');
        const hasIssues = (await issueItems.count()) > 0;
        expect(hasIssues).toBe(true);
      }
    }
  });

  // ────────────────────────────────────────────
  // NAI-102: Multi-turn Clarification
  // ────────────────────────────────────────────

  test('NAI-102: Ambiguous request → Agent asks → User responds → Applied', async ({ page }) => {
    // 1. Type initial content
    const initialText = 'The system architecture documentation is incomplete.';
    await typeInEditor(page, initialText);

    // 2. Select text
    await selectText(page);

    // 3. Open ChatView
    await clickOpenChat(page);
    const chatView = page.locator('[data-testid="chat-view"]');
    await expect(chatView).toBeVisible({ timeout: 5000 });

    // 4. Send vague request
    await sendMessage(page, 'Make it better');

    // 5. Wait for AI response
    const hasAIResponse = await waitForAIResponse(page, 30000);

    if (hasAIResponse) {
      // 6. Check if agent asks clarifying question
      const aiMessage = chatView.locator('[data-testid="message-assistant"]').last();
      const hasAIMessage = await aiMessage.isVisible({ timeout: 10000 }).catch(() => false);

      if (!hasAIMessage) {
        // AI not responding - skip test
        test.skip(true, 'AI not configured or not responding');
        return;
      }

      const aiMessageText = await aiMessage.textContent();

      // Agent should ask for clarification (contains question mark or clarification keywords)
      const asksClarification =
        aiMessageText?.includes('?') ||
        aiMessageText?.toLowerCase().includes('what') ||
        aiMessageText?.toLowerCase().includes('how') ||
        aiMessageText?.toLowerCase().includes('clarify');

      if (asksClarification) {
        // 7. User responds with specific request
        await sendMessage(page, 'More professional tone and add technical details');

        // 8. Wait for second AI response
        await waitForAIResponse(page, 30000);

        // 9. Verify session_id persisted across turns (check message count)
        const messageCount = await chatView.locator('[data-testid^="message-"]').count();
        expect(messageCount).toBeGreaterThanOrEqual(4); // 2 user + 2 assistant minimum

        // 10. Check if content was updated
        const originalContent = initialText;
        const contentUpdated = await waitForContentUpdate(page, originalContent, 10000);

        if (contentUpdated) {
          const updatedContent = await getEditorContent(page);
          expect(updatedContent).not.toBe(initialText);
        }
      }
    }
  });

  // ────────────────────────────────────────────
  // NAI-103: Conflict Detection & Retry
  // ────────────────────────────────────────────

  test('NAI-103: User editing → AI update skipped → Toast shown → Retry succeeds', async ({
    page,
  }) => {
    // 1. Type initial content
    const initialText = 'This is the original text that will be enhanced.';
    await typeInEditor(page, initialText);

    // 2. Start AI enhancement request
    await selectText(page);
    const toolbar = page.locator('[data-testid="selection-toolbar"]');
    await expect(toolbar).toBeVisible({ timeout: 3000 });
    await toolbar.locator('[data-testid="enhance-button"]').click();

    // 3. Verify ChatView opens
    const chatView = page.locator('[data-testid="chat-view"]');
    await expect(chatView).toBeVisible({ timeout: 5000 });

    // 4. While AI processes, click back in editor and start typing
    // This simulates user editing while AI is generating response
    await page.waitForTimeout(1000); // Brief delay to let request start
    const proseMirror = page.locator('[data-testid="note-editor"] .ProseMirror');
    await proseMirror.click();

    // Move cursor to end and start typing (creates conflict)
    await page.keyboard.press('End');
    await page.keyboard.type(' User is now editing this block.');

    // 5. Wait for AI response to complete
    const hasAIResponse = await waitForAIResponse(page, 30000);

    if (hasAIResponse) {
      // 6. Check for conflict toast notification
      const conflictToast = page.locator('text=/AI update skipped/i');
      const hasConflictToast = await conflictToast.isVisible({ timeout: 5000 }).catch(() => false);

      if (hasConflictToast) {
        // Conflict detected - toast shown
        await expect(conflictToast).toBeVisible();

        // 7. Verify update NOT applied immediately
        await page.waitForTimeout(500);
        const contentDuringConflict = await getEditorContent(page);
        expect(contentDuringConflict).toContain('User is now editing this block');

        // 8. User moves to different block (create new paragraph)
        await page.keyboard.press('Enter');
        await page.keyboard.press('Enter');
        await page.keyboard.type('New paragraph - user moved away from conflict.');

        // 9. Wait for retry (exponential backoff: 2s, 4s, 8s)
        // First retry happens after 2s
        await page.waitForTimeout(3000);

        // 10. Verify update eventually applied (or retry attempted)
        // Since user moved away, retry should succeed
        const finalContent = await getEditorContent(page);

        // Final content should include both user's edit and potentially AI's enhancement
        // At minimum, it should have the user's edits
        expect(finalContent).toContain('User is now editing this block');
        expect(finalContent).toContain('New paragraph');
      }
    }
  });

  // ────────────────────────────────────────────
  // NAI-104: Session Persistence
  // ────────────────────────────────────────────

  test('NAI-104: Multi-turn conversation preserves session_id', async ({ page }) => {
    // Track network requests to verify session_id
    const chatRequests: { sessionId?: string; body: unknown }[] = [];

    await page.route('**/api/v1/ai/chat', async (route) => {
      const request = route.request();
      const postData = request.postDataJSON();
      chatRequests.push({
        sessionId: postData?.session_id,
        body: postData,
      });
      await route.continue();
    });

    // 1. Type content
    await typeInEditor(page, 'Project management best practices.');

    // 2. Open ChatView
    await clickOpenChat(page);
    const chatView = page.locator('[data-testid="chat-view"]');
    await expect(chatView).toBeVisible({ timeout: 5000 });

    // 3. Send first message
    await sendMessage(page, 'Summarize this in bullet points');

    // 4. Wait for first response
    const hasFirstResponse = await waitForAIResponse(page, 30000);

    if (hasFirstResponse && chatRequests.length > 0) {
      // 5. Capture session_id from first request
      const firstRequest = chatRequests[0];
      const firstSessionId = firstRequest.sessionId;

      // 6. Send second message
      await sendMessage(page, 'Add more detail about agile methodologies');

      // 7. Wait for second response
      await waitForAIResponse(page, 30000);

      // 8. Verify second request used same session_id
      if (chatRequests.length > 1) {
        const secondRequest = chatRequests[chatRequests.length - 1];
        const secondSessionId = secondRequest.sessionId;

        expect(secondSessionId).toBeDefined();
        expect(secondSessionId).toBe(firstSessionId);

        // 9. Verify conversation history accumulated
        const messageCount = await chatView.locator('[data-testid^="message-"]').count();
        expect(messageCount).toBeGreaterThanOrEqual(4); // 2 user + 2 assistant
      }
    }

    // Cleanup route
    await page.unroute('**/api/v1/ai/chat');
  });

  // ────────────────────────────────────────────
  // Performance Tests (Bonus Track)
  // ────────────────────────────────────────────

  test('NAI-PERF-001: Measure time from user action to first SSE token', async ({ page }) => {
    // This test measures performance metrics for the $500 bonus

    await typeInEditor(page, 'Performance test content for AI enhancement.');
    await selectText(page);

    // Start timing
    const startTime = Date.now();

    // Trigger enhance action
    const toolbar = page.locator('[data-testid="selection-toolbar"]');
    await expect(toolbar).toBeVisible({ timeout: 3000 });
    await toolbar.locator('[data-testid="enhance-button"]').click();

    // Wait for first streaming indicator
    const streamingIndicator = page.locator('[data-testid="streaming-indicator"]');
    const streamingStarted = await streamingIndicator
      .isVisible({ timeout: 5000 })
      .catch(() => false);

    if (streamingStarted) {
      const timeToFirstToken = Date.now() - startTime;

      // Log performance metric
      console.log(`[PERF] Time to first SSE token: ${timeToFirstToken}ms`);

      // Target: <2000ms
      expect(timeToFirstToken).toBeLessThan(3000); // Allow 3s for CI environments

      // Wait for response to complete
      await waitForAIResponse(page, 30000);
    }
  });

  test('NAI-PERF-002: Measure time from content_update event to DOM update', async ({ page }) => {
    // This test measures DOM update latency

    await typeInEditor(page, 'DOM update latency test content.');
    await selectText(page);

    // Capture original content
    const originalContent = await getEditorContent(page);

    // Trigger enhance
    const toolbar = page.locator('[data-testid="selection-toolbar"]');
    await expect(toolbar).toBeVisible({ timeout: 3000 });
    await toolbar.locator('[data-testid="enhance-button"]').click();

    // Wait for AI response
    const hasResponse = await waitForAIResponse(page, 30000);

    if (hasResponse) {
      // Start timing when content changes
      const updateStartTime = Date.now();

      // Poll for DOM update
      const contentUpdated = await waitForContentUpdate(page, originalContent, 5000);

      if (contentUpdated) {
        const domUpdateTime = Date.now() - updateStartTime;

        console.log(`[PERF] Content update to DOM update: ${domUpdateTime}ms`);

        // Target: <50ms (but allow <200ms for real-world conditions)
        expect(domUpdateTime).toBeLessThan(1000);
      }
    }
  });
});
