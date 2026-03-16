/**
 * Unit tests for NotePreviewCard component.
 *
 * Tests:
 * - Renders note title text
 * - Has role="button" and tabIndex=0 for keyboard accessibility
 * - Navigates to note on click via router.push
 * - Navigates to note on Enter keydown
 * - Shows linkType badge with first char uppercase + rest lowercase
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

const mockPush = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('lucide-react', () => ({
  FileText: () => <span data-testid="icon-file-text" />,
}));

vi.mock('@/lib/utils', () => ({
  cn: (...classes: (string | undefined | false)[]) => classes.filter(Boolean).join(' '),
}));

import { NotePreviewCard } from '../note-preview-card';

const BASE_PROPS = {
  noteId: 'note-abc',
  noteTitle: 'My test note',
  linkType: 'extracted' as const,
  workspaceSlug: 'my-workspace',
};

describe('NotePreviewCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the noteTitle text', () => {
    render(<NotePreviewCard {...BASE_PROPS} />);
    expect(screen.getByText('My test note')).toBeInTheDocument();
  });

  it('has role="button" and tabIndex=0', () => {
    render(<NotePreviewCard {...BASE_PROPS} />);
    const card = screen.getByRole('button');
    expect(card).toBeInTheDocument();
    expect(card).toHaveAttribute('tabindex', '0');
  });

  it('calls router.push with correct path on click', () => {
    render(<NotePreviewCard {...BASE_PROPS} />);
    fireEvent.click(screen.getByRole('button'));
    expect(mockPush).toHaveBeenCalledOnce();
    expect(mockPush).toHaveBeenCalledWith('/my-workspace/notes/note-abc');
  });

  it('calls router.push on Enter keydown', () => {
    render(<NotePreviewCard {...BASE_PROPS} />);
    fireEvent.keyDown(screen.getByRole('button'), { key: 'Enter' });
    expect(mockPush).toHaveBeenCalledOnce();
    expect(mockPush).toHaveBeenCalledWith('/my-workspace/notes/note-abc');
  });

  it('calls router.push on Space keydown', () => {
    render(<NotePreviewCard {...BASE_PROPS} />);
    fireEvent.keyDown(screen.getByRole('button'), { key: ' ' });
    expect(mockPush).toHaveBeenCalledOnce();
    expect(mockPush).toHaveBeenCalledWith('/my-workspace/notes/note-abc');
  });

  it('does not call router.push on other keydown (e.g. Tab)', () => {
    render(<NotePreviewCard {...BASE_PROPS} />);
    fireEvent.keyDown(screen.getByRole('button'), { key: 'Tab' });
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('shows badge text "Extracted" for linkType extracted', () => {
    render(<NotePreviewCard {...BASE_PROPS} linkType="extracted" />);
    expect(screen.getByText('Extracted')).toBeInTheDocument();
  });

  it('shows badge text "Related" for linkType related', () => {
    render(<NotePreviewCard {...BASE_PROPS} linkType="related" />);
    expect(screen.getByText('Related')).toBeInTheDocument();
  });

  it('shows badge text "Referenced" for linkType referenced', () => {
    render(<NotePreviewCard {...BASE_PROPS} linkType="referenced" />);
    expect(screen.getByText('Referenced')).toBeInTheDocument();
  });

  it('shows badge text "Inline" for linkType inline', () => {
    render(<NotePreviewCard {...BASE_PROPS} linkType="inline" />);
    expect(screen.getByText('Inline')).toBeInTheDocument();
  });

  it('uses workspaceSlug and noteId in the pushed path', () => {
    render(
      <NotePreviewCard
        noteId="note-xyz"
        noteTitle="Another note"
        linkType="related"
        workspaceSlug="other-slug"
      />
    );
    fireEvent.click(screen.getByRole('button'));
    expect(mockPush).toHaveBeenCalledWith('/other-slug/notes/note-xyz');
  });
});
