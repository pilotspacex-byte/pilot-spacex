/**
 * TDD red-phase tests for MermaidPreview component.
 *
 * MermaidPreview renders mermaid diagram syntax as interactive SVG.
 * Expected component path: ../MermaidPreview.tsx
 *
 * Spec refs: FR-001 (render diagrams), FR-002 (10 diagram types),
 * FR-005 (inline error display), FR-006 (last valid SVG cache),
 * FR-052 (theme sync)
 *
 * These tests define the expected API and behavior. The component
 * does not exist yet — all tests are expected to fail (red phase).
 *
 * @module pm-blocks/__tests__/MermaidPreview.test
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';

// Mock mermaid to avoid JSDOM rendering issues
vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(async (_id: string, definition: string) => {
      if (definition.includes('INVALID_SYNTAX')) {
        throw new Error('Parse error on line 1');
      }
      return { svg: `<svg data-testid="mermaid-svg">${definition}</svg>` };
    }),
  },
}));

// This import will fail until the component is created
import { MermaidPreview } from '../MermaidPreview';

describe('MermaidPreview', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  // ── FR-001: Render diagrams as SVG ──────────────────────────────────
  describe('FR-001: diagram rendering', () => {
    it('renders valid mermaid syntax as SVG', async () => {
      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-svg-container')).toBeInTheDocument();
      });
    });

    it('renders empty state when code is empty', () => {
      render(<MermaidPreview code="" />);
      expect(screen.queryByTestId('mermaid-svg-container')).not.toBeInTheDocument();
    });

    it('debounces rendering by 300ms', async () => {
      const { default: mermaid } = await import('mermaid');
      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      // Should not render immediately
      expect(mermaid.render).not.toHaveBeenCalled();

      // Advance past debounce
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      expect(mermaid.render).toHaveBeenCalledTimes(1);
    });
  });

  // ── FR-002: 10 diagram types ────────────────────────────────────────
  describe('FR-002: diagram type support', () => {
    const diagramTypes = [
      { type: 'flowchart', code: 'flowchart TD\n  A --> B' },
      { type: 'sequence', code: 'sequenceDiagram\n  A->>B: Hello' },
      { type: 'gantt', code: 'gantt\n  title Timeline\n  task1 :a, 2024-01-01, 1w' },
      { type: 'classDiagram', code: 'classDiagram\n  class Foo {\n    +bar()\n  }' },
      { type: 'erDiagram', code: 'erDiagram\n  A ||--o{ B : has' },
      { type: 'stateDiagram', code: 'stateDiagram-v2\n  [*] --> Active' },
      { type: 'C4Context', code: 'C4Context\n  Person(user, "User")' },
      { type: 'pie', code: 'pie\n  "A": 60\n  "B": 40' },
      { type: 'mindmap', code: 'mindmap\n  root\n    A\n    B' },
      { type: 'gitGraph', code: 'gitGraph\n  commit\n  branch feature' },
    ];

    it.each(diagramTypes)('renders $type diagram', async ({ code }) => {
      render(<MermaidPreview code={code} />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-svg-container')).toBeInTheDocument();
      });
    });
  });

  // ── FR-005: Inline error display ────────────────────────────────────
  describe('FR-005: error handling', () => {
    it('displays inline error message for invalid syntax', async () => {
      render(<MermaidPreview code="INVALID_SYNTAX" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-error')).toBeInTheDocument();
        expect(screen.getByText(/parse error/i)).toBeInTheDocument();
      });
    });

    it('does not show toast notifications for errors', async () => {
      render(<MermaidPreview code="INVALID_SYNTAX" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      // Error should be inline, not a toast
      await waitFor(() => {
        expect(screen.getByTestId('mermaid-error')).toBeInTheDocument();
      });
    });
  });

  // ── FR-006: Last valid SVG cache ────────────────────────────────────
  describe('FR-006: last valid SVG preservation', () => {
    it('preserves last valid SVG when syntax error is introduced', async () => {
      const { rerender } = render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      // Wait for initial valid render
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-svg-container')).toBeInTheDocument();
      });

      // Introduce syntax error
      rerender(<MermaidPreview code="INVALID_SYNTAX" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      // Last valid SVG should still be visible alongside the error
      await waitFor(() => {
        expect(screen.getByTestId('mermaid-svg-container')).toBeInTheDocument();
        expect(screen.getByTestId('mermaid-error')).toBeInTheDocument();
      });
    });
  });

  // ── FR-052: Theme sync ──────────────────────────────────────────────
  describe('FR-052: theme synchronization', () => {
    it('accepts a theme prop', async () => {
      render(<MermaidPreview code="flowchart TD\n  A --> B" theme="dark" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-svg-container')).toBeInTheDocument();
      });
    });

    it('re-renders when theme changes', async () => {
      const { default: mermaid } = await import('mermaid');
      const { rerender } = render(<MermaidPreview code="flowchart TD\n  A --> B" theme="light" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      const callCount = (mermaid.render as ReturnType<typeof vi.fn>).mock.calls.length;

      rerender(<MermaidPreview code="flowchart TD\n  A --> B" theme="dark" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(mermaid.render).toHaveBeenCalledTimes(callCount + 1);
      });
    });
  });

  // ── Security: XSS prevention (C-1) ─────────────────────────────────
  describe('Security: XSS prevention (C-1)', () => {
    it('preserves foreignObject but strips script inside it', async () => {
      const { default: mermaid } = await import('mermaid');
      vi.mocked(mermaid.render).mockResolvedValueOnce({
        svg: '<svg><foreignObject><script>alert("xss")</script><div>safe</div></foreignObject><rect/></svg>',
        diagramType: 'flowchart',
      });

      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        const container = screen.getByTestId('mermaid-svg-container');
        // foreignObject is allowed (mermaid v11+ uses it for text rendering)
        expect(container.innerHTML).toContain('foreignObject');
        // But script tags inside it must be stripped
        expect(container.innerHTML).not.toContain('script');
        expect(container.innerHTML).not.toContain('alert');
      });
    });

    it('strips script tags from SVG output', async () => {
      const { default: mermaid } = await import('mermaid');
      vi.mocked(mermaid.render).mockResolvedValueOnce({
        svg: '<svg><script>alert("xss")</script><rect/></svg>',
        diagramType: 'flowchart',
      });

      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        const container = screen.getByTestId('mermaid-svg-container');
        expect(container.innerHTML).not.toContain('script');
      });
    });

    it('strips iframe tags from SVG output', async () => {
      const { default: mermaid } = await import('mermaid');
      vi.mocked(mermaid.render).mockResolvedValueOnce({
        svg: '<svg><iframe src="https://evil.com"></iframe><rect/></svg>',
        diagramType: 'flowchart',
      });

      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        const container = screen.getByTestId('mermaid-svg-container');
        expect(container.innerHTML).not.toContain('iframe');
      });
    });

    it('strips object and embed tags from SVG output', async () => {
      const { default: mermaid } = await import('mermaid');
      vi.mocked(mermaid.render).mockResolvedValueOnce({
        svg: '<svg><object data="x"></object><embed src="y"/><rect/></svg>',
        diagramType: 'flowchart',
      });

      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        const container = screen.getByTestId('mermaid-svg-container');
        expect(container.innerHTML).not.toContain('object');
        expect(container.innerHTML).not.toContain('embed');
      });
    });

    it('preserves valid SVG elements after sanitization', async () => {
      const { default: mermaid } = await import('mermaid');
      vi.mocked(mermaid.render).mockResolvedValueOnce({
        svg: '<svg><rect width="100" height="50"/><text>Safe content</text></svg>',
        diagramType: 'flowchart',
      });

      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        const container = screen.getByTestId('mermaid-svg-container');
        expect(container.innerHTML).toContain('rect');
        expect(container.innerHTML).toContain('Safe content');
      });
    });

    it('strips on* event handlers from SVG attributes', async () => {
      const { default: mermaid } = await import('mermaid');
      vi.mocked(mermaid.render).mockResolvedValueOnce({
        svg: '<svg><rect onclick="alert(1)" width="100"/></svg>',
        diagramType: 'flowchart',
      });

      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        const container = screen.getByTestId('mermaid-svg-container');
        expect(container.innerHTML).not.toContain('onclick');
      });
    });
  });
});
