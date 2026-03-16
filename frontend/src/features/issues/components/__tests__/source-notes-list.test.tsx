/**
 * SourceNotesList component tests (T026).
 *
 * Verifies empty state, note titles, link type badges,
 * navigation URLs, and multiple note rendering.
 */

import { render, screen, within } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SourceNotesList } from '../source-notes-list';
import type { NoteIssueLink } from '@/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function createNoteLink(overrides?: Partial<NoteIssueLink>): NoteIssueLink {
  return {
    id: 'nl-1',
    noteId: 'note-1',
    issueId: 'issue-1',
    linkType: 'extracted',
    noteTitle: 'Meeting Notes',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SourceNotesList', () => {
  it('renders empty state when no links', () => {
    render(<SourceNotesList links={[]} workspaceSlug="my-team" />);
    expect(screen.getByText('No linked notes')).toBeInTheDocument();
  });

  it('shows note titles', () => {
    const links = [
      createNoteLink({ id: 'nl-1', noteTitle: 'Sprint Planning Notes' }),
      createNoteLink({ id: 'nl-2', noteTitle: 'Design Review' }),
    ];

    render(<SourceNotesList links={links} workspaceSlug="my-team" />);

    expect(screen.getByText('Sprint Planning Notes')).toBeInTheDocument();
    expect(screen.getByText('Design Review')).toBeInTheDocument();
  });

  it('shows extracted link type badge with amber color', () => {
    render(
      <SourceNotesList
        links={[createNoteLink({ linkType: 'extracted' })]}
        workspaceSlug="my-team"
      />
    );

    const badge = screen.getByText('Extracted');
    expect(badge.className).toContain('bg-amber-100');
    expect(badge.className).toContain('text-amber-700');
  });

  it('shows related link type badge with slate color', () => {
    render(
      <SourceNotesList links={[createNoteLink({ linkType: 'related' })]} workspaceSlug="my-team" />
    );

    const badge = screen.getByText('Related');
    expect(badge.className).toContain('bg-slate-100');
    expect(badge.className).toContain('text-slate-700');
  });

  it('shows referenced link type badge with sky color', () => {
    render(
      <SourceNotesList
        links={[createNoteLink({ linkType: 'referenced' })]}
        workspaceSlug="my-team"
      />
    );

    const badge = screen.getByText('Referenced');
    expect(badge.className).toContain('bg-sky-100');
    expect(badge.className).toContain('text-sky-700');
  });

  it('navigates to correct note URL', () => {
    render(
      <SourceNotesList links={[createNoteLink({ noteId: 'note-42' })]} workspaceSlug="my-team" />
    );

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/my-team/notes/note-42');
  });

  it('multiple notes render correctly', () => {
    const links = [
      createNoteLink({ id: 'nl-1', noteId: 'n1', noteTitle: 'Note A', linkType: 'extracted' }),
      createNoteLink({ id: 'nl-2', noteId: 'n2', noteTitle: 'Note B', linkType: 'related' }),
      createNoteLink({ id: 'nl-3', noteId: 'n3', noteTitle: 'Note C', linkType: 'referenced' }),
    ];

    render(<SourceNotesList links={links} workspaceSlug="ws" />);

    const list = screen.getByRole('list', { name: 'Linked notes' });
    const items = within(list).getAllByRole('listitem');
    expect(items).toHaveLength(3);

    const allLinks = screen.getAllByRole('link');
    expect(allLinks[0]).toHaveAttribute('href', '/ws/notes/n1');
    expect(allLinks[1]).toHaveAttribute('href', '/ws/notes/n2');
    expect(allLinks[2]).toHaveAttribute('href', '/ws/notes/n3');
  });

  // -------------------------------------------------------------------------
  // Navigation (T042)
  // -------------------------------------------------------------------------

  describe('Navigation (T042)', () => {
    it('note links navigate to /{workspaceSlug}/notes/{noteId} path', () => {
      render(
        <SourceNotesList
          links={[createNoteLink({ noteId: 'note-abc' })]}
          workspaceSlug="acme-team"
        />
      );

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', '/acme-team/notes/note-abc');
    });

    it('extracted link type badge renders with amber styling classes', () => {
      render(
        <SourceNotesList links={[createNoteLink({ linkType: 'extracted' })]} workspaceSlug="ws" />
      );

      const badge = screen.getByText('Extracted');
      expect(badge.className).toContain('bg-amber-100');
      expect(badge.className).toContain('text-amber-700');
    });

    it('inline link type badge renders with purple styling classes', () => {
      render(
        <SourceNotesList links={[createNoteLink({ linkType: 'inline' })]} workspaceSlug="ws" />
      );

      const badge = screen.getByText('Inline');
      expect(badge.className).toContain('bg-purple-100');
      expect(badge.className).toContain('text-purple-700');
    });

    it('referenced link type badge renders with sky styling classes', () => {
      render(
        <SourceNotesList links={[createNoteLink({ linkType: 'referenced' })]} workspaceSlug="ws" />
      );

      const badge = screen.getByText('Referenced');
      expect(badge.className).toContain('bg-sky-100');
      expect(badge.className).toContain('text-sky-700');
    });

    it('links render as <a> tags via Next.js Link component', () => {
      render(<SourceNotesList links={[createNoteLink({ noteId: 'note-x' })]} workspaceSlug="ws" />);

      const link = screen.getByRole('link');
      expect(link.tagName).toBe('A');
    });

    it('multiple notes all have correct navigation URLs', () => {
      const links = [
        createNoteLink({ id: 'nl-1', noteId: 'n-alpha', noteTitle: 'Alpha' }),
        createNoteLink({ id: 'nl-2', noteId: 'n-beta', noteTitle: 'Beta' }),
        createNoteLink({ id: 'nl-3', noteId: 'n-gamma', noteTitle: 'Gamma' }),
      ];

      render(<SourceNotesList links={links} workspaceSlug="dev-team" />);

      const allLinks = screen.getAllByRole('link');
      expect(allLinks).toHaveLength(3);
      expect(allLinks[0]).toHaveAttribute('href', '/dev-team/notes/n-alpha');
      expect(allLinks[1]).toHaveAttribute('href', '/dev-team/notes/n-beta');
      expect(allLinks[2]).toHaveAttribute('href', '/dev-team/notes/n-gamma');
    });
  });
});
