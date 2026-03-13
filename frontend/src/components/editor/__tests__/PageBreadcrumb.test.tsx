/**
 * Tests for PageBreadcrumb component
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

// ---------------------------------------------------------------------------
// Import component
// ---------------------------------------------------------------------------

import { PageBreadcrumb } from '../PageBreadcrumb';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PageBreadcrumb', () => {
  const defaultProps = {
    ancestors: [
      { id: 'a1', title: 'Engineering' },
      { id: 'a2', title: 'Backend' },
    ],
    currentTitle: 'API Design',
    workspaceSlug: 'workspace',
  };

  it('Test 4: renders ancestor chain with chevron separators and clickable links', () => {
    render(<PageBreadcrumb {...defaultProps} />);
    expect(screen.getByRole('link', { name: 'Engineering' })).toHaveAttribute(
      'href',
      '/workspace/notes/a1'
    );
    expect(screen.getByRole('link', { name: 'Backend' })).toHaveAttribute(
      'href',
      '/workspace/notes/a2'
    );
    expect(screen.getByText('API Design')).toBeInTheDocument();
    // Current title is NOT a link
    expect(screen.queryByRole('link', { name: 'API Design' })).toBeNull();
  });

  it('Test 5: renders just current page title when no ancestors (root page)', () => {
    render(<PageBreadcrumb ancestors={[]} currentTitle="Root Page" workspaceSlug="workspace" />);
    expect(screen.getByText('Root Page')).toBeInTheDocument();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('Test 6: includes nav aria-label for accessibility', () => {
    render(<PageBreadcrumb {...defaultProps} />);
    expect(screen.getByRole('navigation', { name: /breadcrumb/i })).toBeInTheDocument();
  });
});
