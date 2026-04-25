/**
 * Smoke test for IssueToolbar.
 *
 * Asserts NAV-04 sweep (Plan 90-05): the inline "Search issues..."
 * input has been removed; Command Palette v3 (Tasks scope) subsumes
 * product search. View switcher (Board/List/Table/Priority), Density
 * dropdown, FilterBar, and Create button remain.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('@/stores/RootStore', () => ({
  useIssueViewStore: () => ({
    cardDensity: 'comfortable',
    setCardDensity: vi.fn(),
    setEffectiveViewMode: vi.fn(),
    getEffectiveViewMode: () => 'board',
  }),
}));

vi.mock('../FilterBar', () => ({
  FilterBar: () => <div data-testid="filter-bar" />,
}));

import { IssueToolbar } from '../IssueToolbar';

describe('IssueToolbar - NAV-04 sweep', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render a page-level search input', () => {
    render(<IssueToolbar />);
    expect(screen.queryByPlaceholderText(/search/i)).toBeNull();
  });

  it('still renders view switcher and FilterBar', () => {
    render(<IssueToolbar />);
    expect(screen.getByLabelText(/Switch to Board view/i)).toBeInTheDocument();
    expect(screen.getByTestId('filter-bar')).toBeInTheDocument();
  });
});
