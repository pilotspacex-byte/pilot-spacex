/**
 * Unit tests for GutterTOC and getMagnetOffset.
 *
 * @module components/editor/gutter/__tests__/GutterTOC.test
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { GutterTOC, getMagnetOffset } from '../GutterTOC';

// Mock motion/react to avoid framer-motion complexity in tests
vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
      <div data-testid="motion-div" {...filterDomProps(props)}>
        {children}
      </div>
    ),
    span: (props: Record<string, unknown>) => (
      <span data-testid="motion-span" {...filterDomProps(props)} />
    ),
  },
  useReducedMotion: () => false,
}));

/** Filter out non-DOM props to avoid React warnings */
function filterDomProps(props: Record<string, unknown>) {
  const filtered: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(props)) {
    if (!['animate', 'initial', 'exit', 'transition', 'whileHover'].includes(key)) {
      filtered[key] = value;
    }
  }
  return filtered;
}

// Mock extractHeadings from AutoTOC
vi.mock('../../AutoTOC', () => ({
  extractHeadings: vi.fn(() => [
    { id: 'heading-1', level: 1, text: 'Introduction', position: 0 },
    { id: 'heading-2', level: 2, text: 'Getting Started', position: 100 },
    { id: 'heading-3', level: 3, text: 'Prerequisites', position: 200 },
  ]),
}));

function createMockEditor() {
  const listeners = new Map<string, Set<() => void>>();

  const mockDom = {
    querySelector: vi.fn((selector: string) => {
      const id = selector.match(/data-block-id="(.+?)"/)?.[1];
      if (!id) return null;
      return {
        offsetTop: id === 'heading-1' ? 50 : id === 'heading-2' ? 200 : 350,
        getAttribute: (attr: string) => (attr === 'data-block-id' ? id : null),
        scrollIntoView: vi.fn(),
      } as unknown as HTMLElement;
    }),
  };

  return {
    view: { dom: mockDom },
    state: { doc: { descendants: vi.fn() } },
    commands: {
      focus: vi.fn(),
      setTextSelection: vi.fn(),
    },
    on: vi.fn((event: string, cb: () => void) => {
      if (!listeners.has(event)) listeners.set(event, new Set());
      listeners.get(event)!.add(cb);
    }),
    off: vi.fn((event: string, cb: () => void) => {
      listeners.get(event)?.delete(cb);
    }),
    isDestroyed: false,
  };
}

describe('getMagnetOffset', () => {
  it('returns 0 for the active dot itself', () => {
    expect(getMagnetOffset(2, 2)).toBe(0);
  });

  it('returns 4px pull for adjacent dot above active', () => {
    // dot 1 is above active dot 2 — pulled down (+4)
    expect(getMagnetOffset(1, 2)).toBe(4);
  });

  it('returns -4px pull for adjacent dot below active', () => {
    // dot 3 is below active dot 2 — pulled up (-4)
    expect(getMagnetOffset(3, 2)).toBe(-4);
  });

  it('returns 2px for dot 2 positions away above', () => {
    expect(getMagnetOffset(0, 2)).toBe(2);
  });

  it('returns -2px for dot 2 positions away below', () => {
    expect(getMagnetOffset(4, 2)).toBe(-2);
  });

  it('returns 1px for dot 3 positions away above', () => {
    expect(getMagnetOffset(0, 3)).toBe(1);
  });

  it('returns 0 for dots more than 3 away', () => {
    expect(getMagnetOffset(0, 5)).toBe(0);
    expect(getMagnetOffset(10, 2)).toBe(0);
  });

  it('returns 0 when activeIndex is -1 (no active heading)', () => {
    expect(getMagnetOffset(0, -1)).toBe(0);
    expect(getMagnetOffset(1, -1)).toBe(0);
  });
});

describe('GutterTOC', () => {
  let mockEditor: ReturnType<typeof createMockEditor>;
  // scrollRef removed from GutterTOC props (N-11)
  let observerCallback: IntersectionObserverCallback;
  let observedElements: Element[];

  beforeEach(() => {
    mockEditor = createMockEditor();
    // scrollRef removed from GutterTOC props (N-11)
    observedElements = [];

    // Mock IntersectionObserver
    vi.stubGlobal(
      'IntersectionObserver',
      vi.fn((callback: IntersectionObserverCallback) => {
        observerCallback = callback;
        return {
          observe: vi.fn((el: Element) => observedElements.push(el)),
          unobserve: vi.fn(),
          disconnect: vi.fn(),
        };
      })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders a nav element with TOC aria-label', () => {
    render(<GutterTOC editor={mockEditor as unknown as import('@tiptap/react').Editor} />);
    const nav = screen.getByRole('navigation', { name: 'Table of contents' });
    expect(nav).toBeInTheDocument();
  });

  it('renders one button per heading with correct aria-labels', () => {
    render(<GutterTOC editor={mockEditor as unknown as import('@tiptap/react').Editor} />);

    expect(screen.getByRole('button', { name: 'Jump to: Introduction' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Jump to: Getting Started' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Jump to: Prerequisites' })).toBeInTheDocument();
  });

  it('renders nav element when headings exist', () => {
    const { container } = render(
      <GutterTOC editor={mockEditor as unknown as import('@tiptap/react').Editor} />
    );
    expect(container.querySelector('nav')).toBeInTheDocument();
  });

  it('shows hover label on mouse enter', async () => {
    render(<GutterTOC editor={mockEditor as unknown as import('@tiptap/react').Editor} />);

    const btn = screen.getByRole('button', { name: 'Jump to: Introduction' });
    fireEvent.mouseEnter(btn);

    expect(screen.getByText('Introduction')).toBeInTheDocument();
  });

  it('hides hover label on mouse leave', () => {
    render(<GutterTOC editor={mockEditor as unknown as import('@tiptap/react').Editor} />);

    const btn = screen.getByRole('button', { name: 'Jump to: Introduction' });
    fireEvent.mouseEnter(btn);
    expect(screen.getByText('Introduction')).toBeInTheDocument();

    fireEvent.mouseLeave(btn);
    // Label text only appears in the hover tooltip, not in the button
    // After leave, the tooltip is removed
    const tooltips = screen.queryAllByText('Introduction');
    // 0 tooltips visible after leave (the button only has aria-label, not text)
    expect(tooltips.length).toBe(0);
  });

  it('calls editor focus and setTextSelection on click', () => {
    render(<GutterTOC editor={mockEditor as unknown as import('@tiptap/react').Editor} />);

    const btn = screen.getByRole('button', { name: 'Jump to: Getting Started' });
    fireEvent.click(btn);

    expect(mockEditor.commands.focus).toHaveBeenCalled();
    expect(mockEditor.commands.setTextSelection).toHaveBeenCalledWith(100);
  });

  it('sets aria-current on the active heading dot', () => {
    render(<GutterTOC editor={mockEditor as unknown as import('@tiptap/react').Editor} />);

    // Simulate IntersectionObserver firing for heading-2
    act(() => {
      if (observerCallback) {
        observerCallback(
          [
            {
              isIntersecting: true,
              target: { getAttribute: () => 'heading-2' } as unknown as Element,
            } as unknown as IntersectionObserverEntry,
          ],
          {} as IntersectionObserver
        );
      }
    });

    const activeBtn = screen.getByRole('button', { name: 'Jump to: Getting Started' });
    expect(activeBtn).toHaveAttribute('aria-current', 'true');

    const inactiveBtn = screen.getByRole('button', { name: 'Jump to: Introduction' });
    expect(inactiveBtn).not.toHaveAttribute('aria-current');
  });

  it('shows hover label on focus for keyboard accessibility', () => {
    render(<GutterTOC editor={mockEditor as unknown as import('@tiptap/react').Editor} />);

    const btn = screen.getByRole('button', { name: 'Jump to: Prerequisites' });
    fireEvent.focus(btn);

    expect(screen.getByText('Prerequisites')).toBeInTheDocument();
  });

  it('registers and unregisters editor update listener', () => {
    const { unmount } = render(
      <GutterTOC editor={mockEditor as unknown as import('@tiptap/react').Editor} />
    );

    expect(mockEditor.on).toHaveBeenCalledWith('update', expect.any(Function));

    unmount();

    expect(mockEditor.off).toHaveBeenCalledWith('update', expect.any(Function));
  });
});
