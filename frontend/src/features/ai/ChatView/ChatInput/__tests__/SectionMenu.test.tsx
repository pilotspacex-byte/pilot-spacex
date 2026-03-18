import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SectionMenu } from '../SectionMenu';
import type { HeadingItem } from '@/components/editor/AutoTOC';

// cmdk calls scrollIntoView which jsdom doesn't implement
Element.prototype.scrollIntoView = vi.fn();

// Mock Radix popover to always render content in tests
vi.mock('@/components/ui/popover', () => ({
  Popover: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    open ? <div>{children}</div> : null,
  PopoverTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  PopoverContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

const sampleHeadings: HeadingItem[] = [
  { id: 'h1-intro', level: 1, text: 'Introduction', position: 0 },
  { id: 'h2-prereqs', level: 2, text: 'Prerequisites', position: 50 },
  { id: 'h1-main', level: 1, text: 'Main Content', position: 100 },
  { id: 'h3-detail', level: 3, text: 'Details', position: 150 },
];

describe('SectionMenu', () => {
  const mockOnSelect = vi.fn();
  const mockOnOpenChange = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  function renderMenu(open = true, headings = sampleHeadings) {
    return render(
      <SectionMenu
        open={open}
        onOpenChange={mockOnOpenChange}
        onSelect={mockOnSelect}
        onCancel={mockOnCancel}
        headings={headings}
      >
        <button type="button">Trigger</button>
      </SectionMenu>
    );
  }

  it('should render headings when open', () => {
    renderMenu(true);

    expect(screen.getByText('Introduction')).toBeInTheDocument();
    expect(screen.getByText('Prerequisites')).toBeInTheDocument();
    expect(screen.getByText('Main Content')).toBeInTheDocument();
    expect(screen.getByText('Details')).toBeInTheDocument();
  });

  it('should not render content when closed', () => {
    renderMenu(false);

    expect(screen.queryByText('Introduction')).not.toBeInTheDocument();
  });

  it('should show search input with placeholder', () => {
    renderMenu(true);

    expect(screen.getByPlaceholderText('Search sections...')).toBeInTheDocument();
  });

  it('should show "Note Sections" group heading', () => {
    renderMenu(true);

    expect(screen.getByText('Note Sections')).toBeInTheDocument();
  });

  it('should show empty state when no headings', () => {
    renderMenu(true, []);

    expect(
      screen.getByText('No headings in this note. Add headings to create sections.')
    ).toBeInTheDocument();
  });

  it('should call onSelect with heading when item is clicked', async () => {
    const user = userEvent.setup();
    renderMenu(true);

    await user.click(screen.getByText('Prerequisites'));

    expect(mockOnSelect).toHaveBeenCalledWith(sampleHeadings[1]);
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('should call onSelect with heading when item selected via keyboard', async () => {
    const user = userEvent.setup();
    renderMenu(true);

    // Focus the search input and navigate with arrow keys + Enter
    const searchInput = screen.getByPlaceholderText('Search sections...');
    await user.click(searchInput);
    // cmdk auto-highlights first item; 2 ArrowDowns reach "Main Content" (3rd item)
    await user.keyboard('{ArrowDown}{ArrowDown}{Enter}');

    expect(mockOnSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'h1-main', text: 'Main Content' })
    );
  });
});
