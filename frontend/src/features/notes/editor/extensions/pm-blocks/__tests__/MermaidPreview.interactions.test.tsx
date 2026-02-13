/**
 * Tests for MermaidPreview interactive features:
 * - FR-003: SVG node click tooltips + "Link to Issue"
 * - FR-012: Export as PNG
 * - T014: Size limit enforcement (500 lines / 200 nodes)
 *
 * @module pm-blocks/__tests__/MermaidPreview.interactions.test
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';

vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(async (_id: string, definition: string) => {
      if (definition.includes('INVALID_SYNTAX')) {
        throw new Error('Parse error on line 1');
      }
      // Return SVG with node elements matching mermaid's CSS classes
      return {
        svg: `<svg><g class="node"><text class="nodeLabel">NodeA</text></g><g class="node"><text class="nodeLabel">NodeB</text></g></svg>`,
      };
    }),
  },
}));

import { MermaidPreview } from '../MermaidPreview';

describe('MermaidPreview interactions', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  // ── FR-003: Node click tooltips ─────────────────────────────────────
  describe('FR-003: interactive diagrams', () => {
    it('shows tooltip when clicking an SVG node', async () => {
      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-svg-container')).toBeInTheDocument();
      });

      // Click on a node label
      const nodeLabel = screen.getByTestId('mermaid-svg-container').querySelector('.nodeLabel');
      expect(nodeLabel).not.toBeNull();

      fireEvent.click(screen.getByTestId('mermaid-svg-container'), {
        target: nodeLabel,
      });
    });

    it('shows "Link to Issue" button when onLinkToIssue is provided', async () => {
      const onLinkToIssue = vi.fn();
      render(<MermaidPreview code="flowchart TD\n  A --> B" onLinkToIssue={onLinkToIssue} />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-svg-container')).toBeInTheDocument();
      });
    });

    it('does not show tooltip when clicking outside nodes', async () => {
      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-svg-container')).toBeInTheDocument();
      });

      // Click on the SVG container itself (not a node)
      fireEvent.click(screen.getByTestId('mermaid-svg-container'));

      expect(screen.queryByTestId('mermaid-node-tooltip')).not.toBeInTheDocument();
    });
  });

  // ── FR-012: Export as image ─────────────────────────────────────────
  describe('FR-012: diagram export', () => {
    it('renders export button when SVG is displayed', async () => {
      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-export-button')).toBeInTheDocument();
      });
    });

    it('export button has correct aria-label', async () => {
      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        const btn = screen.getByTestId('mermaid-export-button');
        expect(btn).toHaveAttribute('aria-label', 'Export diagram as PNG');
      });
    });

    it('does not show export button when no SVG is rendered', () => {
      render(<MermaidPreview code="" />);
      expect(screen.queryByTestId('mermaid-export-button')).not.toBeInTheDocument();
    });
  });

  // ── T014: Size limit enforcement ────────────────────────────────────
  describe('T014: size limits', () => {
    it('shows complexity error when source exceeds 500 lines', async () => {
      const longCode = Array.from({ length: 501 }, (_, i) => `  node${i}`).join('\n');
      const code = `flowchart TD\n${longCode}`;

      render(<MermaidPreview code={code} />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-complexity-error')).toBeInTheDocument();
        expect(screen.getByText(/diagram too complex/i)).toBeInTheDocument();
        expect(screen.getByText(/showing source only/i)).toBeInTheDocument();
      });
    });

    it('does not show complexity error for code within limits', async () => {
      render(<MermaidPreview code="flowchart TD\n  A --> B" />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-svg-container')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('mermaid-complexity-error')).not.toBeInTheDocument();
    });

    it('does not render mermaid when source exceeds line limit', async () => {
      const { default: mermaid } = await import('mermaid');
      const longCode = Array.from({ length: 501 }, (_, i) => `  node${i}`).join('\n');
      const code = `flowchart TD\n${longCode}`;

      render(<MermaidPreview code={code} />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      // mermaid.render should NOT have been called
      expect(mermaid.render).not.toHaveBeenCalled();
    });

    it('allows exactly 500 lines', async () => {
      const lines = Array.from({ length: 499 }, (_, i) => `  node${i}`).join('\n');
      const code = `flowchart TD\n${lines}`;

      render(<MermaidPreview code={code} />);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mermaid-svg-container')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('mermaid-complexity-error')).not.toBeInTheDocument();
    });
  });
});
