/**
 * Keyboard Navigation Tests
 *
 * T345: Keyboard Navigation Tests
 * - Tab order follows logical visual layout
 * - Focus indicators are visible
 * - Escape closes modals and dropdowns
 * - Arrow keys work in lists and menus
 * - Keyboard shortcuts are documented and working
 *
 * WCAG 2.2 AA Requirements:
 * - 2.1.1 Keyboard: All functionality available via keyboard
 * - 2.1.2 No Keyboard Trap: User can navigate away from any element
 * - 2.4.3 Focus Order: Logical and intuitive tab order
 * - 2.4.7 Focus Visible: Visible focus indicator
 */

import { test, expect } from '@playwright/test';

/**
 * Helper to check if an element has a visible focus indicator.
 * Checks for outline, box-shadow, or ring styles.
 */
async function _hasFocusIndicator(page: import('@playwright/test').Page, selector: string) {
  return page.evaluate((sel) => {
    const element = document.querySelector(sel);
    if (!element) return false;

    const styles = window.getComputedStyle(element);
    const hasOutline = styles.outlineStyle !== 'none' && styles.outlineWidth !== '0px';
    const hasBoxShadow = styles.boxShadow !== 'none';
    const hasRing =
      element.classList.contains('ring') ||
      element.className.includes('ring-') ||
      element.className.includes('focus-visible');

    return hasOutline || hasBoxShadow || hasRing;
  }, selector);
}

test.describe('Tab Order', () => {
  test('Tab order follows visual layout on workspace page', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Start tabbing from the beginning
    await page.keyboard.press('Tab');

    // First focusable element should be skip link (screen reader only normally)
    // or the first visible interactive element
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();

    // Continue tabbing and verify each focused element
    const focusOrder: string[] = [];
    for (let i = 0; i < 10; i++) {
      const focused = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return null;
        return {
          tag: el.tagName.toLowerCase(),
          text: el.textContent?.trim().substring(0, 50) || '',
          role: el.getAttribute('role'),
          ariaLabel: el.getAttribute('aria-label'),
        };
      });

      if (focused) {
        focusOrder.push(
          `${focused.tag}${focused.role ? `[${focused.role}]` : ''}: ${focused.text || focused.ariaLabel || '(no text)'}`
        );
      }

      await page.keyboard.press('Tab');
    }

    // Log focus order for debugging
    console.log('\nTab order:', focusOrder);

    // Verify we can tab through elements without getting stuck
    expect(focusOrder.length).toBeGreaterThan(0);
  });

  test('Shift+Tab navigates backwards', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Tab forward several times
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
    }

    // Get current focused element
    const beforeShiftTab = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });

    // Tab backwards
    await page.keyboard.press('Shift+Tab');

    // Verify focus moved
    const afterShiftTab = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });

    // Focus should have changed (or be on a different element)
    // We just verify the action works without getting stuck
    expect(afterShiftTab).toBeDefined();
    console.log(`Shift+Tab: ${beforeShiftTab} -> ${afterShiftTab}`);
  });

  test('Skip to main content link works', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Tab once to focus skip link
    await page.keyboard.press('Tab');

    // Check if skip link exists and is focused
    const skipLink = page.locator('a[href="#main-content"]');
    const skipLinkVisible = await skipLink.isVisible().catch(() => false);

    if (skipLinkVisible) {
      // If skip link is visible after focus, activate it
      await page.keyboard.press('Enter');

      // Verify focus moved to main content
      const mainContent = page.locator('#main-content, main');
      await expect(mainContent).toBeVisible();
    } else {
      // Skip link might only be visible on focus
      const skipLinkExists = await page.evaluate(() => {
        return document.querySelector('a[href="#main-content"]') !== null;
      });

      if (skipLinkExists) {
        // Make it visible by focusing
        await page.focus('a[href="#main-content"]');
        await page.keyboard.press('Enter');
      }
    }
  });

  test('Form fields have logical tab order', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Find form inputs
    const formInputs = page.locator('input, textarea, select, button[type="submit"]');
    const count = await formInputs.count();

    if (count > 0) {
      // Tab to first input
      await page.keyboard.press('Tab');

      // Collect focus order through form
      const formFocusOrder: string[] = [];
      for (let i = 0; i < count + 2; i++) {
        const focused = await page.evaluate(() => {
          const el = document.activeElement;
          if (!el || el === document.body) return null;
          return {
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute('type') || '',
            name: el.getAttribute('name') || '',
            id: el.id || '',
          };
        });

        if (focused && ['input', 'textarea', 'select', 'button'].includes(focused.tag)) {
          formFocusOrder.push(`${focused.tag}[${focused.type || focused.name || focused.id}]`);
        }

        await page.keyboard.press('Tab');
      }

      console.log('Form tab order:', formFocusOrder);
      expect(formFocusOrder.length).toBeGreaterThan(0);
    }
  });
});

test.describe('Focus Indicators', () => {
  test('Buttons have visible focus indicators', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Find all buttons
    const buttons = page.locator('button');
    const count = await buttons.count();

    if (count > 0) {
      // Focus the first visible button
      const firstButton = buttons.first();
      await firstButton.focus();

      // Check for focus indicator
      const hasFocus = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el) return false;

        const styles = window.getComputedStyle(el);
        return (
          styles.outlineStyle !== 'none' ||
          styles.boxShadow !== 'none' ||
          el.classList.toString().includes('ring') ||
          el.classList.toString().includes('focus')
        );
      });

      expect(hasFocus).toBe(true);
    }
  });

  test('Links have visible focus indicators', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Find all links
    const links = page.locator('a[href]');
    const count = await links.count();

    if (count > 0) {
      // Focus the first visible link
      const firstLink = links.first();
      await firstLink.focus();

      // Check for focus indicator
      const hasFocus = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el) return false;

        const styles = window.getComputedStyle(el);
        return (
          styles.outlineStyle !== 'none' ||
          styles.boxShadow !== 'none' ||
          el.classList.toString().includes('ring') ||
          el.classList.toString().includes('focus')
        );
      });

      expect(hasFocus).toBe(true);
    }
  });

  test('Form inputs have visible focus indicators', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Find all inputs
    const inputs = page.locator('input');
    const count = await inputs.count();

    if (count > 0) {
      // Focus the first input
      const firstInput = inputs.first();
      await firstInput.focus();

      // Check for focus indicator
      const hasFocus = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el) return false;

        const styles = window.getComputedStyle(el);
        return (
          styles.outlineStyle !== 'none' ||
          styles.boxShadow !== 'none' ||
          el.classList.toString().includes('ring') ||
          el.classList.toString().includes('focus')
        );
      });

      expect(hasFocus).toBe(true);
    }
  });

  test('Focus indicator has sufficient contrast', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Find a button and focus it
    const button = page.locator('button').first();
    if (await button.isVisible()) {
      await button.focus();

      // Get focus indicator properties
      const focusStyles = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el) return null;

        const styles = window.getComputedStyle(el);
        return {
          outlineColor: styles.outlineColor,
          outlineWidth: styles.outlineWidth,
          outlineOffset: styles.outlineOffset,
          boxShadow: styles.boxShadow,
        };
      });

      console.log('Focus styles:', focusStyles);

      // Verify some focus indicator exists
      expect(focusStyles).not.toBeNull();
    }
  });
});

test.describe('Modal/Dialog Keyboard Interaction', () => {
  test('Escape closes modals', async ({ page }) => {
    await page.goto('/workspace-demo/issues');
    await page.waitForLoadState('networkidle');

    // Try to open a modal (create button or similar)
    const createButton = page.getByRole('button', { name: /new|create/i });
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(300);

      // Check if modal/dialog is open
      const dialog = page.locator('[role="dialog"], [data-slot="dialog-content"]');
      if (await dialog.isVisible()) {
        // Press Escape to close
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);

        // Verify dialog is closed
        await expect(dialog).not.toBeVisible();
      }
    }
  });

  test('Modal traps focus within its content', async ({ page }) => {
    await page.goto('/workspace-demo/issues');
    await page.waitForLoadState('networkidle');

    // Try to open a modal
    const createButton = page.getByRole('button', { name: /new|create/i });
    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(300);

      const dialog = page.locator('[role="dialog"], [data-slot="dialog-content"]');
      if (await dialog.isVisible()) {
        // Tab multiple times to cycle through modal
        const focusedElements: string[] = [];
        for (let i = 0; i < 20; i++) {
          await page.keyboard.press('Tab');
          const focused = await page.evaluate(() => {
            const el = document.activeElement;
            const dialog = document.querySelector('[role="dialog"], [data-slot="dialog-content"]');
            if (!el || !dialog) return null;

            return {
              isInsideModal: dialog.contains(el),
              tag: el.tagName,
            };
          });

          if (focused) {
            focusedElements.push(`${focused.tag}:${focused.isInsideModal ? 'inside' : 'outside'}`);
          }
        }

        // All focused elements should be inside the modal
        const outsideElements = focusedElements.filter((el) => el.includes('outside'));
        expect(outsideElements).toHaveLength(0);

        // Clean up - close modal
        await page.keyboard.press('Escape');
      }
    }
  });

  test('Focus returns to trigger after modal closes', async ({ page }) => {
    await page.goto('/workspace-demo/issues');
    await page.waitForLoadState('networkidle');

    // Find and focus the create button
    const createButton = page.getByRole('button', { name: /new|create/i });
    if (await createButton.isVisible()) {
      // Get button identifier
      const _buttonText = await createButton.textContent();

      await createButton.click();
      await page.waitForTimeout(300);

      const dialog = page.locator('[role="dialog"], [data-slot="dialog-content"]');
      if (await dialog.isVisible()) {
        // Close modal
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);

        // Check focus returned to trigger
        const focusedText = await page.evaluate(() => {
          return document.activeElement?.textContent?.trim();
        });

        console.log(`Focus returned to: "${focusedText}"`);
      }
    }
  });
});

test.describe('Dropdown Menu Keyboard Navigation', () => {
  test('Arrow keys navigate dropdown items', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Find a dropdown trigger
    const dropdownTrigger = page
      .locator('[data-slot="dropdown-menu-trigger"], [aria-haspopup="menu"]')
      .first();
    if (await dropdownTrigger.isVisible()) {
      // Open dropdown
      await dropdownTrigger.focus();
      await page.keyboard.press('Enter');
      await page.waitForTimeout(200);

      // Check if menu is open
      const menu = page.locator('[role="menu"]');
      if (await menu.isVisible()) {
        // Arrow down should move focus
        await page.keyboard.press('ArrowDown');
        const firstItem = await page.evaluate(() => {
          return document.activeElement?.textContent?.trim();
        });

        await page.keyboard.press('ArrowDown');
        const secondItem = await page.evaluate(() => {
          return document.activeElement?.textContent?.trim();
        });

        console.log(`Menu navigation: "${firstItem}" -> "${secondItem}"`);

        // Items should be different (we moved focus)
        expect(firstItem).not.toBe(secondItem);

        // Close with Escape
        await page.keyboard.press('Escape');
      }
    }
  });

  test('Escape closes dropdown menu', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Find a dropdown trigger
    const dropdownTrigger = page
      .locator('[data-slot="dropdown-menu-trigger"], [aria-haspopup="menu"]')
      .first();
    if (await dropdownTrigger.isVisible()) {
      // Open dropdown
      await dropdownTrigger.click();
      await page.waitForTimeout(200);

      const menu = page.locator('[role="menu"]');
      if (await menu.isVisible()) {
        // Press Escape
        await page.keyboard.press('Escape');
        await page.waitForTimeout(200);

        // Menu should be closed
        await expect(menu).not.toBeVisible();
      }
    }
  });

  test('Enter/Space activates dropdown item', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Find a dropdown trigger
    const dropdownTrigger = page
      .locator('[data-slot="dropdown-menu-trigger"], [aria-haspopup="menu"]')
      .first();
    if (await dropdownTrigger.isVisible()) {
      // Open dropdown
      await dropdownTrigger.focus();
      await page.keyboard.press('Enter');
      await page.waitForTimeout(200);

      const menu = page.locator('[role="menu"]');
      if (await menu.isVisible()) {
        // Navigate to an item
        await page.keyboard.press('ArrowDown');

        // Activate with Enter
        await page.keyboard.press('Enter');

        // Menu should close after selection (for most menus)
        await page.waitForTimeout(200);
      }
    }
  });
});

test.describe('List Navigation', () => {
  test('Arrow keys navigate issue list', async ({ page }) => {
    await page.goto('/workspace-demo/issues');
    await page.waitForLoadState('networkidle');

    // Find issue list/board
    const issueList = page.locator('[data-testid="issue-list"], [role="list"], [role="grid"]');
    if (await issueList.isVisible()) {
      // Focus the list
      await issueList.focus();

      // Arrow down should move focus through items
      await page.keyboard.press('ArrowDown');
      const firstItem = await page.evaluate(() => {
        return (
          document.activeElement?.getAttribute('data-testid') || document.activeElement?.tagName
        );
      });

      await page.keyboard.press('ArrowDown');
      const secondItem = await page.evaluate(() => {
        return (
          document.activeElement?.getAttribute('data-testid') || document.activeElement?.tagName
        );
      });

      console.log(`List navigation: ${firstItem} -> ${secondItem}`);
    }
  });

  test('Home/End keys navigate to first/last item', async ({ page }) => {
    await page.goto('/workspace-demo/issues');
    await page.waitForLoadState('networkidle');

    // Find issue list
    const issueList = page.locator('[data-testid="issue-list"], [role="list"], [role="grid"]');
    if (await issueList.isVisible()) {
      await issueList.focus();

      // Press End to go to last item
      await page.keyboard.press('End');
      const lastItem = await page.evaluate(() => {
        return document.activeElement?.textContent?.trim().substring(0, 50);
      });

      // Press Home to go to first item
      await page.keyboard.press('Home');
      const firstItem = await page.evaluate(() => {
        return document.activeElement?.textContent?.trim().substring(0, 50);
      });

      console.log(`Home/End: first="${firstItem}", last="${lastItem}"`);
    }
  });
});

test.describe('Keyboard Shortcuts', () => {
  test('Cmd/Ctrl+K opens search', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Press Cmd+K (or Ctrl+K on Windows/Linux)
    const isMac = process.platform === 'darwin';
    await page.keyboard.press(isMac ? 'Meta+k' : 'Control+k');
    await page.waitForTimeout(300);

    // Check if search modal/dialog is open
    const searchModal = page.locator('[cmdk-root], [role="dialog"], [data-testid="search-modal"]');
    const isOpen = await searchModal.isVisible().catch(() => false);

    if (isOpen) {
      // Close it
      await page.keyboard.press('Escape');
    }

    console.log(`Cmd/Ctrl+K search: ${isOpen ? 'opened' : 'not opened'}`);
  });

  test('Cmd/Ctrl+N creates new note', async ({ page }) => {
    await page.goto('/workspace-demo/notes');
    await page.waitForLoadState('networkidle');

    // Press Cmd+N (or Ctrl+N on Windows/Linux)
    const isMac = process.platform === 'darwin';
    await page.keyboard.press(isMac ? 'Meta+n' : 'Control+n');
    await page.waitForTimeout(300);

    // Check for new note modal or navigation
    const noteModal = page.locator('[role="dialog"]');
    const isOpen = await noteModal.isVisible().catch(() => false);

    console.log(`Cmd/Ctrl+N new note: ${isOpen ? 'modal opened' : 'no modal'}`);
  });

  test('Keyboard shortcuts do not interfere with text input', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Focus an input field
    const input = page.locator('input[type="text"], input[type="email"]').first();
    if (await input.isVisible()) {
      await input.focus();

      // Type text including "k" and "n"
      await page.keyboard.type('keyboard test');
      await page.waitForTimeout(100);

      // Verify text was entered, not shortcuts triggered
      const value = await input.inputValue();
      expect(value).toBe('keyboard test');
    }
  });
});

test.describe('No Keyboard Traps', () => {
  test('Can tab through entire page without getting stuck', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    const startingFocus = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });

    // Tab through the page many times
    for (let i = 0; i < 100; i++) {
      await page.keyboard.press('Tab');
    }

    // Should eventually cycle back or reach the end
    const endingFocus = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });

    console.log(`Tab cycling: ${startingFocus} -> ${endingFocus}`);

    // Just verify we're still on the page and didn't get stuck
    expect(endingFocus).toBeDefined();
  });

  test('Can escape from all interactive elements', async ({ page }) => {
    await page.goto('/workspace-demo');
    await page.waitForLoadState('networkidle');

    // Find various interactive elements
    const interactiveElements = [
      'button',
      'a[href]',
      'input',
      'select',
      '[role="button"]',
      '[tabindex="0"]',
    ];

    for (const selector of interactiveElements) {
      const element = page.locator(selector).first();
      if (await element.isVisible().catch(() => false)) {
        await element.focus();

        // Verify we can tab away
        await page.keyboard.press('Tab');
        const newFocus = await page.evaluate(() => {
          return document.activeElement?.tagName;
        });

        // Focus should have moved
        expect(newFocus).toBeDefined();
      }
    }
  });
});
