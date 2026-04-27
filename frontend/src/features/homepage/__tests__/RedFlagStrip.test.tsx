/**
 * Phase 88 Plan 03 — Task 2: RedFlagStrip (RED).
 * E-02 Path B revision — empty state now renders a calm 32px dashed
 * placeholder instead of `return null`, so the launchpad keeps its
 * rhythm even when there are no flags.
 *
 * Component contract per UI-SPEC §4 + E-02:
 *  - Empty (zero flags) AND not loading AND not error -> renders the
 *    `red-flag-strip-empty` placeholder (role="status").
 *  - 1+ flags -> <section role="region" aria-label="Workspace alerts">
 *    containing N <a href={flag.href}> banners.
 *  - Per-flag visual contract: icon + amber/rose/violet accent + correct href.
 *  - Loading state -> single skeleton banner (data-testid="red-flag-skeleton").
 *  - Error state (and no flags) -> renders nothing (silent fail).
 *
 * The hook is mocked at module boundary so we can drive every branch
 * without TanStack Query setup.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import type { RedFlag, UseRedFlagsResult } from '../hooks/use-red-flags';

// ─── Mocks ──────────────────────────────────────────────────────────────────

const hookMock: UseRedFlagsResult = {
  flags: [],
  isLoading: false,
  isError: false,
};

vi.mock('../hooks/use-red-flags', async () => {
  // Re-export real RedFlag type alongside mocked hook.
  return {
    useRedFlags: () => hookMock,
  };
});

// next/link is auto-mocked by Next test environment, but we need a simple
// passthrough so we can assert href + aria-label on the underlying <a>.
vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [k: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

import { RedFlagStrip } from '../components/RedFlagStrip';

const STALE: RedFlag = {
  kind: 'stale',
  label: '12 stale tasks',
  href: '/workspace/tasks?filter=stale',
  ariaLabel: '12 stale tasks. Open.',
};
const SPRINT: RedFlag = {
  kind: 'sprint',
  label: 'Sprint Q2-W3 at risk',
  href: '/workspace/projects',
  ariaLabel: 'Sprint Q2-W3 at risk. Open.',
};
const DIGEST: RedFlag = {
  kind: 'digest',
  label: 'Daily digest ready',
  href: '/workspace/digest',
  ariaLabel: 'Daily digest ready. Open.',
};

beforeEach(() => {
  hookMock.flags = [];
  hookMock.isLoading = false;
  hookMock.isError = false;
  cleanup();
});

// ─── Tests ──────────────────────────────────────────────────────────────────

describe('RedFlagStrip (Phase 88 Plan 03)', () => {
  describe('empty state (E-02 Path B placeholder)', () => {
    it('renders the empty-state placeholder when flags is empty and not loading/erroring', () => {
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);

      // Placeholder is present and labelled for SR consumers.
      const placeholder = screen.getByTestId('red-flag-strip-empty');
      expect(placeholder).toBeInTheDocument();
      expect(placeholder).toHaveAttribute('role', 'status');
      expect(placeholder.textContent).toMatch(/no flags right now/i);

      // Banner region landmark must NOT render in the empty state — that
      // landmark is reserved for actual flag content.
      expect(screen.queryByRole('region', { name: 'Workspace alerts' })).toBeNull();
    });

    it('uses dashed border + muted text for the placeholder', () => {
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);
      const placeholder = screen.getByTestId('red-flag-strip-empty');
      expect(placeholder.className).toMatch(/border-dashed/);
      expect(placeholder.className).toMatch(/text-neutral-500/);
      // Same 32px footprint as a populated banner so vertical rhythm holds.
      expect(placeholder.className).toMatch(/h-8/);
    });
  });

  describe('error state', () => {
    it('renders nothing when isError is true', () => {
      hookMock.isError = true;
      const { container } = render(
        <RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />,
      );
      expect(container.firstChild).toBeNull();
    });
  });

  describe('loading state', () => {
    it('renders one skeleton banner when isLoading and no flags yet', () => {
      hookMock.isLoading = true;
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);

      const skeleton = screen.getByTestId('red-flag-skeleton');
      expect(skeleton).toBeInTheDocument();
      // Skeleton lives inside the region wrapper.
      const region = screen.getByRole('region', { name: 'Workspace alerts' });
      expect(region).toContainElement(skeleton);
    });
  });

  describe('one stale flag', () => {
    beforeEach(() => {
      hookMock.flags = [STALE];
    });

    it('renders a single banner inside the region', () => {
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);
      const region = screen.getByRole('region', { name: 'Workspace alerts' });
      expect(region).toBeInTheDocument();

      const links = screen.getAllByRole('link');
      expect(links).toHaveLength(1);
    });

    it('uses the stale ariaLabel and href verbatim', () => {
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);
      const link = screen.getByRole('link', { name: '12 stale tasks. Open.' });
      expect(link).toHaveAttribute('href', '/workspace/tasks?filter=stale');
    });

    it('applies an amber accent class to the stale banner', () => {
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);
      const link = screen.getByRole('link', { name: '12 stale tasks. Open.' });
      // The accent bar is a child element with a kind-specific class.
      const accent = link.querySelector('[data-flag-accent]');
      expect(accent).not.toBeNull();
      expect(accent!.className).toMatch(/amber/);
    });

    it('renders the AlertTriangle lucide icon for stale', () => {
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);
      const link = screen.getByRole('link', { name: '12 stale tasks. Open.' });
      // lucide v0.562 renamed AlertTriangle -> TriangleAlert internally; the
      // alias re-exports the same icon so the canonical class is
      // `lucide-triangle-alert`.
      const icon = link.querySelector('svg.lucide-triangle-alert');
      expect(icon).not.toBeNull();
    });
  });

  describe('three flags', () => {
    beforeEach(() => {
      hookMock.flags = [STALE, SPRINT, DIGEST];
    });

    it('renders three banners in order: stale, sprint, digest', () => {
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);
      const links = screen.getAllByRole('link');
      expect(links).toHaveLength(3);
      expect(links[0]!.getAttribute('aria-label')).toBe('12 stale tasks. Open.');
      expect(links[1]!.getAttribute('aria-label')).toBe('Sprint Q2-W3 at risk. Open.');
      expect(links[2]!.getAttribute('aria-label')).toBe('Daily digest ready. Open.');
    });

    it('applies amber/rose/violet accent classes in the correct order', () => {
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);
      const links = screen.getAllByRole('link');
      const accents = links.map(
        (link) => link.querySelector('[data-flag-accent]')!.className,
      );
      expect(accents[0]).toMatch(/amber/);
      expect(accents[1]).toMatch(/rose/);
      expect(accents[2]).toMatch(/violet/);
    });

    it('renders the matching lucide icon for each kind', () => {
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);
      const links = screen.getAllByRole('link');
      // See note in "one stale flag" test re: TriangleAlert canonical class.
      expect(links[0]!.querySelector('svg.lucide-triangle-alert')).not.toBeNull();
      expect(links[1]!.querySelector('svg.lucide-activity')).not.toBeNull();
      expect(links[2]!.querySelector('svg.lucide-sparkles')).not.toBeNull();
    });

    it('routes each banner to its prescribed href', () => {
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);
      const links = screen.getAllByRole('link');
      expect(links[0]!.getAttribute('href')).toBe('/workspace/tasks?filter=stale');
      expect(links[1]!.getAttribute('href')).toBe('/workspace/projects');
      expect(links[2]!.getAttribute('href')).toBe('/workspace/digest');
    });
  });

  describe('icons are aria-hidden (color is not the sole signal)', () => {
    it('marks every icon as aria-hidden so screen readers rely on text', () => {
      hookMock.flags = [STALE, SPRINT, DIGEST];
      render(<RedFlagStrip workspaceId="ws-1" workspaceSlug="workspace" />);
      const links = screen.getAllByRole('link');
      for (const link of links) {
        const icon = link.querySelector('svg.lucide');
        expect(icon).not.toBeNull();
        expect(icon!.getAttribute('aria-hidden')).toBe('true');
      }
    });
  });
});
