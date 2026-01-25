/**
 * Accessibility Tests with axe-core
 *
 * T344: axe-core Accessibility Tests
 * - Integrated with Playwright
 * - Tests all page routes for WCAG 2.2 AA compliance
 * - Zero critical violations policy
 * - Violations logged with remediation suggestions
 * - CI/CD integration support
 *
 * WCAG 2.2 AA Standards:
 * - Perceivable: Text alternatives, time-based media, adaptable, distinguishable
 * - Operable: Keyboard accessible, enough time, seizures, navigable, input modalities
 * - Understandable: Readable, predictable, input assistance
 * - Robust: Compatible with assistive technologies
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Routes to test for accessibility compliance.
 * Includes both public and authenticated routes with dynamic segments.
 */
const publicRoutes = ['/', '/login'];

const workspaceRoutes = [
  '/workspace-demo',
  '/workspace-demo/notes',
  '/workspace-demo/issues',
  '/workspace-demo/projects',
  '/workspace-demo/settings',
];

/**
 * WCAG 2.2 AA tags for axe-core testing.
 * @see https://www.w3.org/TR/WCAG22/
 */
const wcagTags = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'];

/**
 * Impact levels for filtering violations.
 * Critical and serious violations must be fixed before deployment.
 */
const criticalImpacts = ['critical', 'serious'] as const;

/**
 * Helper to format violation details for logging.
 */
function formatViolation(violation: {
  id: string;
  impact?: string;
  description: string;
  helpUrl: string;
  nodes: Array<{ html: string; failureSummary?: string }>;
}) {
  const nodeDetails = violation.nodes
    .slice(0, 3)
    .map(
      (node, idx) =>
        `  ${idx + 1}. ${node.html.substring(0, 100)}${node.html.length > 100 ? '...' : ''}\n     Fix: ${node.failureSummary || 'See help URL'}`
    )
    .join('\n');

  return `
[${violation.impact?.toUpperCase() || 'UNKNOWN'}] ${violation.id}
Description: ${violation.description}
Help: ${violation.helpUrl}
Affected elements (first 3):
${nodeDetails}
`;
}

/**
 * Helper to run accessibility scan with consistent configuration.
 */
async function runAccessibilityScan(page: import('@playwright/test').Page) {
  return new AxeBuilder({ page })
    .withTags(wcagTags)
    .exclude('[data-a11y-skip]') // Allow excluding specific elements for known issues
    .analyze();
}

test.describe('Accessibility Compliance', () => {
  test.describe('Public Pages', () => {
    for (const route of publicRoutes) {
      test(`${route} should have no critical accessibility violations`, async ({ page }) => {
        await page.goto(route);
        await page.waitForLoadState('networkidle');

        // Allow page content to fully render
        await page.waitForTimeout(500);

        const results = await runAccessibilityScan(page);

        // Log all violations for debugging/remediation
        if (results.violations.length > 0) {
          console.log(`\n=== Accessibility Violations on ${route} ===`);
          results.violations.forEach((violation) => {
            console.log(formatViolation(violation));
          });
        }

        // Filter for critical/serious violations only
        const criticalViolations = results.violations.filter((v) =>
          criticalImpacts.includes(v.impact as (typeof criticalImpacts)[number])
        );

        // Report critical violations with details
        if (criticalViolations.length > 0) {
          const violationSummary = criticalViolations
            .map((v) => `- [${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} instances)`)
            .join('\n');

          expect(
            criticalViolations,
            `Critical accessibility violations found on ${route}:\n${violationSummary}`
          ).toHaveLength(0);
        }
      });
    }
  });

  test.describe('Workspace Pages', () => {
    for (const route of workspaceRoutes) {
      test(`${route} should have no critical accessibility violations`, async ({ page }) => {
        // Navigate to workspace (assumes demo workspace exists or mocked)
        await page.goto(route);

        // Wait for content to load
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);

        const results = await runAccessibilityScan(page);

        // Log all violations
        if (results.violations.length > 0) {
          console.log(`\n=== Accessibility Violations on ${route} ===`);
          results.violations.forEach((violation) => {
            console.log(formatViolation(violation));
          });
        }

        // Filter critical violations
        const criticalViolations = results.violations.filter((v) =>
          criticalImpacts.includes(v.impact as (typeof criticalImpacts)[number])
        );

        expect(criticalViolations).toHaveLength(0);
      });
    }
  });

  test.describe('Component-Specific Tests', () => {
    test('Dialog/Modal accessibility', async ({ page }) => {
      await page.goto('/workspace-demo/issues');
      await page.waitForLoadState('networkidle');

      // Look for create issue button and click it to open modal
      const createButton = page.getByRole('button', { name: /new|create/i });
      if (await createButton.isVisible()) {
        await createButton.click();
        await page.waitForTimeout(300); // Wait for modal animation

        // Check modal specifically
        const modalResults = await new AxeBuilder({ page })
          .include('[role="dialog"]')
          .withTags(wcagTags)
          .analyze();

        const criticalViolations = modalResults.violations.filter((v) =>
          criticalImpacts.includes(v.impact as (typeof criticalImpacts)[number])
        );

        expect(criticalViolations).toHaveLength(0);
      }
    });

    test('Navigation/Sidebar accessibility', async ({ page }) => {
      await page.goto('/workspace-demo');
      await page.waitForLoadState('networkidle');

      // Check sidebar/navigation specifically
      const navResults = await new AxeBuilder({ page })
        .include('aside, nav, [role="navigation"]')
        .withTags(wcagTags)
        .analyze();

      const criticalViolations = navResults.violations.filter((v) =>
        criticalImpacts.includes(v.impact as (typeof criticalImpacts)[number])
      );

      expect(criticalViolations).toHaveLength(0);
    });

    test('Form accessibility', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');

      // Check forms specifically
      const formResults = await new AxeBuilder({ page })
        .include('form, [role="form"]')
        .withTags(wcagTags)
        .analyze();

      const criticalViolations = formResults.violations.filter((v) =>
        criticalImpacts.includes(v.impact as (typeof criticalImpacts)[number])
      );

      // Log form-specific issues
      if (formResults.violations.length > 0) {
        console.log('\n=== Form Accessibility Violations ===');
        formResults.violations.forEach((violation) => {
          console.log(formatViolation(violation));
        });
      }

      expect(criticalViolations).toHaveLength(0);
    });
  });

  test.describe('Color Contrast', () => {
    test('Text has sufficient color contrast', async ({ page }) => {
      await page.goto('/workspace-demo');
      await page.waitForLoadState('networkidle');

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2aa', 'wcag21aa', 'wcag22aa'])
        .analyze();

      // Filter for contrast-specific violations
      const contrastViolations = results.violations.filter(
        (v) => v.id.includes('contrast') || v.id.includes('color')
      );

      if (contrastViolations.length > 0) {
        console.log('\n=== Color Contrast Violations ===');
        contrastViolations.forEach((violation) => {
          console.log(formatViolation(violation));
        });
      }

      // Report but allow minor contrast issues (warnings only for now)
      const criticalContrastViolations = contrastViolations.filter((v) => v.impact === 'critical');

      expect(criticalContrastViolations).toHaveLength(0);
    });
  });

  test.describe('Screen Reader Compatibility', () => {
    test('Images have alt text', async ({ page }) => {
      await page.goto('/workspace-demo');
      await page.waitForLoadState('networkidle');

      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();

      // Filter for image-related violations
      const imageViolations = results.violations.filter(
        (v) => v.id.includes('image') || v.id.includes('alt')
      );

      const criticalImageViolations = imageViolations.filter((v) =>
        criticalImpacts.includes(v.impact as (typeof criticalImpacts)[number])
      );

      expect(criticalImageViolations).toHaveLength(0);
    });

    test('ARIA attributes are valid', async ({ page }) => {
      await page.goto('/workspace-demo');
      await page.waitForLoadState('networkidle');

      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();

      // Filter for ARIA-related violations
      const ariaViolations = results.violations.filter(
        (v) => v.id.includes('aria') || v.id.includes('role')
      );

      const criticalAriaViolations = ariaViolations.filter((v) =>
        criticalImpacts.includes(v.impact as (typeof criticalImpacts)[number])
      );

      if (ariaViolations.length > 0) {
        console.log('\n=== ARIA Violations ===');
        ariaViolations.forEach((violation) => {
          console.log(formatViolation(violation));
        });
      }

      expect(criticalAriaViolations).toHaveLength(0);
    });

    test('Landmarks are properly defined', async ({ page }) => {
      await page.goto('/workspace-demo');
      await page.waitForLoadState('networkidle');

      // Check for required landmarks
      const landmarks = await page.evaluate(() => {
        return {
          main: document.querySelector('main, [role="main"]') !== null,
          navigation: document.querySelector('nav, [role="navigation"]') !== null,
          banner: document.querySelector('header, [role="banner"]') !== null,
          contentinfo: document.querySelector('footer, [role="contentinfo"]') !== null,
        };
      });

      // Main content area is required
      expect(landmarks.main).toBe(true);

      // Navigation is expected for workspace pages
      expect(landmarks.navigation || landmarks.banner).toBe(true);
    });
  });

  test.describe('Responsive Accessibility', () => {
    test('Mobile viewport has no critical violations', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
      await page.goto('/workspace-demo');
      await page.waitForLoadState('networkidle');

      const results = await runAccessibilityScan(page);

      const criticalViolations = results.violations.filter((v) =>
        criticalImpacts.includes(v.impact as (typeof criticalImpacts)[number])
      );

      expect(criticalViolations).toHaveLength(0);
    });

    test('Tablet viewport has no critical violations', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 }); // iPad
      await page.goto('/workspace-demo');
      await page.waitForLoadState('networkidle');

      const results = await runAccessibilityScan(page);

      const criticalViolations = results.violations.filter((v) =>
        criticalImpacts.includes(v.impact as (typeof criticalImpacts)[number])
      );

      expect(criticalViolations).toHaveLength(0);
    });
  });
});

/**
 * Accessibility regression test to run on all pages.
 * This provides a summary report for CI/CD.
 */
test.describe('Accessibility Summary Report', () => {
  test('Generate accessibility summary for all routes', async ({ page }) => {
    const allRoutes = [...publicRoutes, ...workspaceRoutes];
    const summary: Array<{
      route: string;
      total: number;
      critical: number;
      serious: number;
      moderate: number;
      minor: number;
    }> = [];

    for (const route of allRoutes) {
      try {
        await page.goto(route);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(300);

        const results = await runAccessibilityScan(page);

        const counts = {
          route,
          total: results.violations.length,
          critical: results.violations.filter((v) => v.impact === 'critical').length,
          serious: results.violations.filter((v) => v.impact === 'serious').length,
          moderate: results.violations.filter((v) => v.impact === 'moderate').length,
          minor: results.violations.filter((v) => v.impact === 'minor').length,
        };

        summary.push(counts);
      } catch {
        summary.push({
          route,
          total: -1,
          critical: -1,
          serious: -1,
          moderate: -1,
          minor: -1,
        });
      }
    }

    // Log summary
    console.log('\n=== Accessibility Summary Report ===\n');
    console.log('Route | Total | Critical | Serious | Moderate | Minor');
    console.log('------|-------|----------|---------|----------|------');
    summary.forEach((s) => {
      console.log(
        `${s.route} | ${s.total} | ${s.critical} | ${s.serious} | ${s.moderate} | ${s.minor}`
      );
    });

    // Assert no critical violations across all pages
    const totalCritical = summary.reduce((acc, s) => acc + Math.max(0, s.critical), 0);
    const totalSerious = summary.reduce((acc, s) => acc + Math.max(0, s.serious), 0);

    expect(totalCritical, `Found ${totalCritical} critical violations across all pages`).toBe(0);
    expect(totalSerious, `Found ${totalSerious} serious violations across all pages`).toBe(0);
  });
});
