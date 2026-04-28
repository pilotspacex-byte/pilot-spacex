/**
 * Phase 87.1 Plan 04 — ArtifactRendererSwitch dispatch for MD and HTML.
 *
 * Verifies:
 *  - type='MD' with content → renders MarkdownRenderer with content prop
 *  - type='HTML' with content → renders HtmlRenderer with content + filename
 *  - type='HTML' iframe sandbox attribute equals empty string (no allow-scripts)
 *  - placeholder branch: no content → still falls through to UnsupportedState
 *    (we keep the old behavior when the hook hasn't fetched content yet).
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const queryState: {
  data: unknown;
  isLoading: boolean;
  error: Error | null;
} = { data: null, isLoading: false, error: null };

vi.mock('@/hooks/use-artifact-query', () => ({
  useArtifactQuery: () => ({
    data: queryState.data,
    isLoading: queryState.isLoading,
    error: queryState.error,
    refetch: vi.fn(),
  }),
}));

// Mock the renderer modules with deterministic stubs that expose props
// via test ids — avoids dynamic-resolution timing complexity.
vi.mock('@/features/artifacts/components/renderers/MarkdownRenderer', () => ({
  MarkdownRenderer: ({ content }: { content: string }) => (
    <div data-testid="md-renderer">{content}</div>
  ),
}));
vi.mock('@/features/artifacts/components/renderers/HtmlRenderer', () => ({
  HtmlRenderer: ({ content, filename }: { content: string; filename: string }) => (
    <div data-testid="html-renderer" data-filename={filename}>
      {content}
    </div>
  ),
}));

// next/dynamic returns a synchronous proxy that reads the *mocked* module
// at first render. We use React.lazy-style suspense fallback semantics by
// rendering null until the loader resolves. In practice with mocked modules
// the promise is already settled by the time React renders, so we read it
// in a `useEffect` and trigger one re-render.
type AnyProps = Record<string, unknown>;
vi.mock('next/dynamic', () => ({
  default: (loader: () => Promise<unknown>) => {
    function DynamicProxy(props: AnyProps) {
      const [Resolved, setResolved] = React.useState<React.ComponentType<AnyProps> | null>(
        null,
      );
      React.useEffect(() => {
        let cancelled = false;
        void loader().then((resolved) => {
          if (cancelled) return;
          let candidate: unknown = resolved;
          if (typeof resolved === 'object' && resolved !== null) {
            const m = resolved as Record<string, unknown>;
            candidate =
              m.MarkdownRenderer ??
              m.HtmlRenderer ??
              m.NoteReadOnly ??
              m.IssueReadOnly ??
              m.default ??
              resolved;
          }
          setResolved(() => candidate as React.ComponentType<AnyProps>);
        });
        return () => {
          cancelled = true;
        };
      }, []);
      const ResolvedComp = Resolved as React.ComponentType<AnyProps> | null;
      return ResolvedComp ? React.createElement(ResolvedComp, props) : null;
    }
    return DynamicProxy;
  },
}));

import * as React from 'react';
import { ArtifactRendererSwitch } from '../ArtifactRendererSwitch';

describe('ArtifactRendererSwitch — MD/HTML dispatch (Phase 87.1 Plan 04)', () => {
  it('renders MarkdownRenderer when type=MD and content is present', async () => {
    queryState.isLoading = false;
    queryState.error = null;
    queryState.data = {
      type: 'MD',
      id: 'md-1',
      content: '# hello world\n\nbody',
      title: 'hello.md',
    };
    render(<ArtifactRendererSwitch type="MD" id="md-1" />);
    // The artifact-renderer wrapper appears immediately
    expect(screen.getByTestId('artifact-renderer')).toBeInTheDocument();
    // MarkdownRenderer (mocked) renders the content prop
    await waitFor(
      () => {
        const md = screen.getByTestId('md-renderer');
        expect(md.textContent).toContain('hello world');
      },
      { timeout: 2000 },
    );
  });

  it('renders HtmlRenderer when type=HTML and content is present', async () => {
    queryState.isLoading = false;
    queryState.error = null;
    queryState.data = {
      type: 'HTML',
      id: 'h-1',
      content: '<p>x</p>',
      title: 'page.html',
    };
    render(<ArtifactRendererSwitch type="HTML" id="h-1" />);
    expect(screen.getByTestId('artifact-renderer')).toBeInTheDocument();
    await waitFor(
      () => {
        const html = screen.getByTestId('html-renderer');
        expect(html.textContent).toContain('<p>x</p>');
        expect(html.getAttribute('data-filename')).toBe('page.html');
      },
      { timeout: 2000 },
    );
  });

  it('shows EmptyState when MD data has no content (mid-fetch)', () => {
    queryState.isLoading = false;
    queryState.error = null;
    // No content key — preview not yet fetched.
    queryState.data = { type: 'MD', id: 'md-2' };
    render(<ArtifactRendererSwitch type="MD" id="md-2" />);
    expect(screen.getByText(/no preview available/i)).toBeInTheDocument();
  });
});

// Sandbox-invariant test moved to a sibling file (HtmlRenderer.sandbox.test.tsx)
// because that test must mount the REAL HtmlRenderer and the module-level
// vi.mock above replaces it with a stub for this file's scope.
