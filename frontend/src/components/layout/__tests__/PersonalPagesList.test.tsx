/**
 * Tests for PersonalPagesList component
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Note } from '@/types';

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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockUsePersonalPages = vi.fn((_ws: any) => ({
  data: [] as Note[],
  isLoading: false,
}));

vi.mock('@/features/notes/hooks/usePersonalPages', () => ({
  usePersonalPages: (workspaceId: string) => mockUsePersonalPages(workspaceId),
}));

// ---------------------------------------------------------------------------
// Component import (after mocks)
// ---------------------------------------------------------------------------

let PersonalPagesList: React.ComponentType<{
  workspaceId: string;
  workspaceSlug: string;
  currentNoteId?: string;
}>;

beforeEach(async () => {
  vi.clearAllMocks();
  mockUsePersonalPages.mockReturnValue({ data: [], isLoading: false });
  const mod = await import('../PersonalPagesList');
  PersonalPagesList = mod.PersonalPagesList;
});

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

const makeNote = (id: string, title: string): Note =>
  ({
    id,
    title,
    workspaceId: 'ws-1',
    projectId: undefined,
    parentId: undefined,
  }) as Note;

const defaultProps = {
  workspaceId: 'ws-1',
  workspaceSlug: 'workspace',
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PersonalPagesList', () => {
  it('Test 1: renders list of personal pages as links', () => {
    mockUsePersonalPages.mockReturnValue({
      data: [makeNote('n1', 'My First Page'), makeNote('n2', 'Journal')],
      isLoading: false,
    });
    render(<PersonalPagesList {...defaultProps} />);
    expect(screen.getByText('My First Page')).toBeInTheDocument();
    expect(screen.getByText('Journal')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /My First Page/i })).toHaveAttribute(
      'href',
      '/workspace/notes/n1'
    );
  });

  it('Test 2: shows "No personal pages" message when list is empty', () => {
    mockUsePersonalPages.mockReturnValue({ data: [], isLoading: false });
    render(<PersonalPagesList {...defaultProps} />);
    expect(screen.getByText(/no personal pages/i)).toBeInTheDocument();
  });

  it('Test 3: active page has highlighted styling', () => {
    mockUsePersonalPages.mockReturnValue({
      data: [makeNote('n1', 'Active Page')],
      isLoading: false,
    });
    render(<PersonalPagesList {...defaultProps} currentNoteId="n1" />);
    const link = screen.getByRole('link', { name: /Active Page/i });
    expect(link.className).toContain('bg-sidebar-accent');
  });
});
