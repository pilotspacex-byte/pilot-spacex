import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { OnThisPageTOC } from '../OnThisPageTOC';
import type { HeadingItem } from '../AutoTOC';
import type { Editor } from '@tiptap/react';

// Mock IntersectionObserver (already in vitest.setup.tsx, but ensure it's available)
const mockObserve = vi.fn();
const mockDisconnect = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: mockObserve,
    disconnect: mockDisconnect,
    unobserve: vi.fn(),
  }));
});

function createMockEditor(): Editor {
  return {
    commands: {
      setTextSelection: vi.fn(),
    },
    view: {
      dom: {
        querySelector: vi.fn(() => ({
          scrollIntoView: vi.fn(),
          getAttribute: vi.fn(() => 'block-1'),
        })),
      },
    },
  } as unknown as Editor;
}

const sampleHeadings: HeadingItem[] = [
  { id: 'h1-intro', level: 1, text: 'Introduction', position: 0 },
  { id: 'h2-overview', level: 2, text: 'Overview', position: 50 },
  { id: 'h2-details', level: 2, text: 'Details', position: 120 },
  { id: 'h1-conclusion', level: 1, text: 'Conclusion', position: 200 },
];

describe('OnThisPageTOC', () => {
  it('should render heading list with "On this page" label', () => {
    const editor = createMockEditor();
    render(<OnThisPageTOC editor={editor} headings={sampleHeadings} />);

    expect(screen.getByText('On this page')).toBeInTheDocument();
    expect(screen.getByText('Introduction')).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Details')).toBeInTheDocument();
    expect(screen.getByText('Conclusion')).toBeInTheDocument();
  });

  it('should return null when fewer than 2 headings', () => {
    const editor = createMockEditor();
    const { container } = render(<OnThisPageTOC editor={editor} headings={[sampleHeadings[0]!]} />);

    expect(container.innerHTML).toBe('');
  });

  it('should return null when editor is null', () => {
    const { container } = render(<OnThisPageTOC editor={null} headings={sampleHeadings} />);

    expect(container.innerHTML).toBe('');
  });

  it('should render nav with correct aria-label', () => {
    const editor = createMockEditor();
    render(<OnThisPageTOC editor={editor} headings={sampleHeadings} />);

    expect(screen.getByRole('navigation', { name: 'On this page' })).toBeInTheDocument();
  });

  it('should apply indentation classes based on heading level', () => {
    const editor = createMockEditor();
    const { container } = render(<OnThisPageTOC editor={editor} headings={sampleHeadings} />);

    const buttons = container.querySelectorAll('button');
    // H1 headings should have pl-3
    expect(buttons[0]).toHaveClass('pl-3');
    // H2 headings should have pl-5
    expect(buttons[1]).toHaveClass('pl-5');
    expect(buttons[2]).toHaveClass('pl-5');
    // H1 again
    expect(buttons[3]).toHaveClass('pl-3');
  });

  it('should call scrollIntoView when heading is clicked', () => {
    const editor = createMockEditor();
    render(<OnThisPageTOC editor={editor} headings={sampleHeadings} />);

    fireEvent.click(screen.getByText('Overview'));

    expect(editor.commands.setTextSelection).toHaveBeenCalledWith(50);
    expect(editor.view.dom.querySelector).toHaveBeenCalledWith('[data-block-id="h2-overview"]');
  });

  it('should set up IntersectionObserver for heading tracking', () => {
    const editor = createMockEditor();
    render(<OnThisPageTOC editor={editor} headings={sampleHeadings} />);

    expect(IntersectionObserver).toHaveBeenCalled();
    // Observer should observe each heading element (querySelector called per heading)
    expect(mockObserve).toHaveBeenCalled();
  });

  it('should apply custom className', () => {
    const editor = createMockEditor();
    render(<OnThisPageTOC editor={editor} headings={sampleHeadings} className="custom-class" />);

    expect(screen.getByRole('navigation')).toHaveClass('custom-class');
  });
});
