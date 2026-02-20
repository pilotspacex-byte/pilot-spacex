/**
 * Unit tests for EditorGutter container component.
 *
 * @module components/editor/gutter/__tests__/EditorGutter.test
 */
import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { EditorGutter } from '../EditorGutter';

// Mock child components to isolate container tests
vi.mock('../GutterTOC', () => ({
  GutterTOC: () => <div data-testid="gutter-toc" />,
}));

vi.mock('../GutterIssueIndicators', () => ({
  GutterIssueIndicators: () => <div data-testid="gutter-issues" />,
}));

// Mock motion/react
vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
      <div {...props}>{children}</div>
    ),
  },
  useReducedMotion: () => false,
}));

function createMockEditor() {
  return {
    view: { dom: { querySelector: vi.fn() } },
    state: { doc: { descendants: vi.fn() } },
    commands: { focus: vi.fn(), setTextSelection: vi.fn() },
    on: vi.fn(),
    off: vi.fn(),
    isDestroyed: false,
  };
}

describe('EditorGutter', () => {
  it('renders the gutter container with correct width', () => {
    const mockEditor = createMockEditor();

    const { container } = render(
      <EditorGutter
        editor={mockEditor as unknown as import('@tiptap/react').Editor}
        linkedIssues={[]}
      />
    );

    const gutter = container.firstElementChild;
    expect(gutter).toBeInTheDocument();
    expect(gutter?.className).toContain('w-14');
    expect(gutter?.className).toContain('absolute');
  });

  it('renders GutterTOC child component', () => {
    const mockEditor = createMockEditor();

    const { getByTestId } = render(
      <EditorGutter
        editor={mockEditor as unknown as import('@tiptap/react').Editor}
        linkedIssues={[]}
      />
    );

    expect(getByTestId('gutter-toc')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const mockEditor = createMockEditor();

    const { container } = render(
      <EditorGutter
        editor={mockEditor as unknown as import('@tiptap/react').Editor}
        linkedIssues={[]}
        className="hidden lg:flex"
      />
    );

    const gutter = container.firstElementChild;
    expect(gutter?.className).toContain('hidden');
    expect(gutter?.className).toContain('lg:flex');
  });

  it('has two track columns (TOC + issue indicators)', () => {
    const mockEditor = createMockEditor();

    const { getByTestId } = render(
      <EditorGutter
        editor={mockEditor as unknown as import('@tiptap/react').Editor}
        linkedIssues={[]}
      />
    );

    expect(getByTestId('gutter-toc')).toBeInTheDocument();
    expect(getByTestId('gutter-issues')).toBeInTheDocument();
  });
});
