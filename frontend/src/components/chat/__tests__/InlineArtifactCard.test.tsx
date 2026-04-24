/**
 * InlineArtifactCard — Phase 87 Plan 04 (CHAT-04) variant rendering tests.
 *
 * Verifies:
 *   - 3 variants (full / group / compact) render correct chrome
 *   - Click handlers route through useArtifactPeekState().openPeek
 *   - Group expander cap (5 visible) + singular/plural copy
 *   - Compact pill carries Lucide icon + envelope title
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { InlineArtifactRef } from '../InlineArtifactCard';

// ---- Mocks ----------------------------------------------------------------

const openPeekMock = vi.fn();

vi.mock('@/hooks/use-artifact-peek-state', () => ({
  useArtifactPeekState: () => ({
    openPeek: openPeekMock,
    closePeek: vi.fn(),
    openFocus: vi.fn(),
    closeFocus: vi.fn(),
    escalate: vi.fn(),
    demote: vi.fn(),
    setView: vi.fn(),
    peekId: null,
    peekType: null,
    focusId: null,
    focusType: null,
    view: 'split' as const,
    isPeekOpen: false,
    isFocusOpen: false,
  }),
}));

vi.mock('@/components/artifacts/ArtifactCard', () => ({
  ArtifactCard: vi.fn(
    ({
      id,
      type,
      density,
      title,
    }: {
      id: string;
      type: string;
      density: string;
      title?: string;
    }) => (
      <div
        data-mock-artifact-card=""
        data-id={id}
        data-type={type}
        data-density={density}
      >
        {title ?? ''}
      </div>
    ),
  ),
}));

import { InlineArtifactCard } from '../InlineArtifactCard';

beforeEach(() => {
  openPeekMock.mockReset();
});

// ---- Tests ----------------------------------------------------------------

describe('InlineArtifactCard — variant resolution + chrome', () => {
  it('Test 1: NOTE w/o variant → renders Full and delegates to ArtifactCard preview', () => {
    const ref: InlineArtifactRef = {
      id: 'n1',
      type: 'NOTE',
      title: 'Some Note',
      updatedAt: '2026-04-24',
    };
    const { container } = render(<InlineArtifactCard artifact={ref} />);
    const wrap = container.querySelector('[data-inline-card="full"]');
    expect(wrap).not.toBeNull();
    const mock = container.querySelector('[data-mock-artifact-card]');
    expect(mock).not.toBeNull();
    expect(mock?.getAttribute('data-density')).toBe('preview');
    expect(mock?.getAttribute('data-id')).toBe('n1');
    expect(mock?.getAttribute('data-type')).toBe('NOTE');
  });

  it('Test 2: ISSUE w/ group → renders Group with header + count', () => {
    const ref: InlineArtifactRef = {
      id: 'g1',
      type: 'ISSUE',
      group: {
        label: 'Tasks',
        rows: [
          {
            id: 't1',
            type: 'ISSUE',
            title: 'Build slash menu',
            state: 'In Progress',
            stateColor: '#3b82f6',
            updatedAt: '2h',
          },
        ],
      },
    };
    const { container } = render(<InlineArtifactCard artifact={ref} />);
    expect(container.querySelector('[data-inline-card="group"]')).not.toBeNull();
    expect(screen.getByText('Tasks')).toBeTruthy();
    expect(screen.getByText('1')).toBeTruthy(); // count
  });

  it('Test 3: 7 rows → 5 visible + "Show 2 more"; click expands', () => {
    const rows = Array.from({ length: 7 }, (_, i) => ({
      id: `t${i}`,
      type: 'ISSUE' as const,
      title: `Task ${i}`,
      updatedAt: '1h',
    }));
    const ref: InlineArtifactRef = {
      id: 'g1',
      type: 'ISSUE',
      group: { label: 'Tasks', rows },
    };
    const { container } = render(<InlineArtifactCard artifact={ref} />);
    expect(container.querySelectorAll('[data-inline-group-row]').length).toBe(5);
    const moreBtn = screen.getByText('Show 2 more');
    fireEvent.click(moreBtn);
    expect(container.querySelectorAll('[data-inline-group-row]').length).toBe(7);
  });

  it('Test 4: 1 row → no Show-more button', () => {
    const ref: InlineArtifactRef = {
      id: 'g1',
      type: 'ISSUE',
      group: {
        label: 'Tasks',
        rows: [{ id: 't0', type: 'ISSUE', title: 'Only', updatedAt: '1h' }],
      },
    };
    render(<InlineArtifactCard artifact={ref} />);
    expect(screen.queryByText(/Show .* more/)).toBeNull();
  });

  it('Test 5: 6 rows → "Show 1 more" (singular)', () => {
    const rows = Array.from({ length: 6 }, (_, i) => ({
      id: `t${i}`,
      type: 'ISSUE' as const,
      title: `Task ${i}`,
      updatedAt: '1h',
    }));
    const ref: InlineArtifactRef = {
      id: 'g1',
      type: 'ISSUE',
      group: { label: 'Tasks', rows },
    };
    render(<InlineArtifactCard artifact={ref} />);
    expect(screen.getByText('Show 1 more')).toBeTruthy();
  });

  it('Test 6: click on group row → openPeek(rowId, rowType)', () => {
    const ref: InlineArtifactRef = {
      id: 'g1',
      type: 'ISSUE',
      group: {
        label: 'Tasks',
        rows: [{ id: 'row-x', type: 'ISSUE', title: 'X', updatedAt: '1h' }],
      },
    };
    const { container } = render(<InlineArtifactCard artifact={ref} />);
    const row = container.querySelector('[data-inline-group-row]') as HTMLElement;
    fireEvent.click(row);
    expect(openPeekMock).toHaveBeenCalledWith('row-x', 'ISSUE');
  });

  it('Test 7: variant=compact → data-compact-pill, click → openPeek', () => {
    const ref: InlineArtifactRef = {
      id: 'p1',
      type: 'MD',
      variant: 'compact',
      title: 'design.md',
    };
    const { container } = render(<InlineArtifactCard artifact={ref} />);
    expect(container.querySelector('[data-inline-card="compact"]')).not.toBeNull();
    const pill = container.querySelector('[data-compact-pill]') as HTMLElement;
    expect(pill).not.toBeNull();
    fireEvent.click(pill);
    expect(openPeekMock).toHaveBeenCalledWith('p1', 'MD');
  });

  it('Test 8: NOTE Full → header click opens peek; chevron click does NOT', () => {
    const ref: InlineArtifactRef = {
      id: 'n1',
      type: 'NOTE',
      variant: 'full',
      title: 'Note 1',
      updatedAt: '2026-04-24',
    };
    const { container } = render(<InlineArtifactCard artifact={ref} />);
    const header = container.querySelector('[data-full-header-target]') as HTMLElement;
    fireEvent.click(header);
    expect(openPeekMock).toHaveBeenCalledWith('n1', 'NOTE');
    openPeekMock.mockReset();
    const chevron = container.querySelector(
      'button[aria-label="Expand body"]',
    ) as HTMLElement;
    fireEvent.click(chevron);
    expect(openPeekMock).not.toHaveBeenCalled();
  });

  it('Test 9: compact pill title uses CSS truncate (not JS slice)', () => {
    const longTitle = 'x'.repeat(50);
    const ref: InlineArtifactRef = {
      id: 'p1',
      type: 'MD',
      variant: 'compact',
      title: longTitle,
    };
    const { container } = render(<InlineArtifactCard artifact={ref} />);
    const titleEl = container.querySelector('[data-compact-pill] .truncate');
    expect(titleEl).not.toBeNull();
    expect(titleEl?.textContent).toBe(longTitle); // not sliced
  });

  it('Test 10: empty group → "No items" placeholder', () => {
    const ref: InlineArtifactRef = {
      id: 'g1',
      type: 'ISSUE',
      group: { label: 'Tasks', rows: [] },
    };
    render(<InlineArtifactCard artifact={ref} />);
    expect(screen.getByText('No items')).toBeTruthy();
  });

  it('Test 11: INLINE_TYPE_ICON map present and renders an SVG for each tier-1 type', () => {
    for (const type of ['NOTE', 'ISSUE', 'SPEC', 'DECISION'] as const) {
      const { container } = render(
        <InlineArtifactCard
          artifact={{ id: `${type}-1`, type, variant: 'compact', title: 't' }}
        />,
      );
      const pill = container.querySelector('[data-compact-pill]');
      expect(pill?.querySelector('svg')).not.toBeNull();
    }
  });

  it('Test 12: compact renders envelope-supplied title verbatim', () => {
    const ref: InlineArtifactRef = {
      id: 'p1',
      type: 'MD',
      variant: 'compact',
      title: 'design.md',
    };
    render(<InlineArtifactCard artifact={ref} />);
    expect(screen.getByText('design.md')).toBeTruthy();
  });
});
