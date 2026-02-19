/**
 * Tests for SidebarPanel, SidebarPanelHeader, SidebarPanelContent, useSidebarPanel.
 *
 * Coverage target: >80%
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import { SidebarPanel } from './SidebarPanel';
import { SidebarPanelHeader } from './SidebarPanelHeader';
import { SidebarPanelContent } from './SidebarPanelContent';
import { useSidebarPanel, SIDEBAR_DEFAULTS } from './useSidebarPanel';
import type { SidebarTab } from './SidebarPanelHeader';

// motion/react animations are mocked to resolve immediately in tests
vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
      <div {...props}>{children}</div>
    ),
    aside: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
      <aside {...props}>{children}</aside>
    ),
  },
  AnimatePresence: ({ children }: React.PropsWithChildren) => <>{children}</>,
}));

vi.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
    <div data-testid="scroll-area" {...props}>
      {children}
    </div>
  ),
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    onClick,
    ...props
  }: React.PropsWithChildren<Record<string, unknown> & { onClick?: () => void }>) => (
    <button onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));

// -------------------------------------------------------------------------
// useSidebarPanel
// -------------------------------------------------------------------------
describe('useSidebarPanel', () => {
  it('starts closed with no active panel', () => {
    const { result } = renderHook(() => useSidebarPanel());
    expect(result.current.isOpen).toBe(false);
    expect(result.current.activePanel).toBeNull();
  });

  it('opens with a panel id', () => {
    const { result } = renderHook(() => useSidebarPanel());
    act(() => result.current.openSidebar('versions'));
    expect(result.current.isOpen).toBe(true);
    expect(result.current.activePanel).toBe('versions');
  });

  it('closes the panel', () => {
    const { result } = renderHook(() => useSidebarPanel());
    act(() => result.current.openSidebar('versions'));
    act(() => result.current.closeSidebar());
    expect(result.current.isOpen).toBe(false);
    expect(result.current.activePanel).toBeNull();
  });

  it('defaults width to DEFAULT_WIDTH', () => {
    const { result } = renderHook(() => useSidebarPanel());
    expect(result.current.width).toBe(SIDEBAR_DEFAULTS.DEFAULT_WIDTH);
  });

  it('clamps width to MIN_WIDTH', () => {
    const { result } = renderHook(() => useSidebarPanel());
    act(() => result.current.setWidth(10));
    expect(result.current.width).toBe(SIDEBAR_DEFAULTS.MIN_WIDTH);
  });

  it('clamps width to MAX_WIDTH', () => {
    const { result } = renderHook(() => useSidebarPanel());
    act(() => result.current.setWidth(9999));
    expect(result.current.width).toBe(SIDEBAR_DEFAULTS.MAX_WIDTH);
  });

  it('sets width within bounds', () => {
    const { result } = renderHook(() => useSidebarPanel());
    act(() => result.current.setWidth(360));
    expect(result.current.width).toBe(360);
  });

  it('closes on Escape key when open', () => {
    const { result } = renderHook(() => useSidebarPanel());
    act(() => result.current.openSidebar('versions'));

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });

    expect(result.current.isOpen).toBe(false);
  });

  it('does not close on non-Escape keys', () => {
    const { result } = renderHook(() => useSidebarPanel());
    act(() => result.current.openSidebar('versions'));

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    });

    expect(result.current.isOpen).toBe(true);
  });

  it('does not attach Escape listener when closed', () => {
    const { result } = renderHook(() => useSidebarPanel());
    // stays closed
    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });
    expect(result.current.isOpen).toBe(false);
  });
});

// -------------------------------------------------------------------------
// SidebarPanelHeader
// -------------------------------------------------------------------------
const MOCK_TABS: SidebarTab[] = [
  { id: 'versions', label: 'Versions' },
  { id: 'presence', label: 'Presence' },
];

describe('SidebarPanelHeader', () => {
  const defaultProps = {
    title: 'Test Panel',
    activePanel: 'versions' as const,
    onTabChange: vi.fn(),
    onClose: vi.fn(),
  };

  beforeEach(() => vi.clearAllMocks());

  it('renders the title', () => {
    render(<SidebarPanelHeader {...defaultProps} />);
    expect(screen.getByText('Test Panel')).toBeInTheDocument();
  });

  it('renders a close button', () => {
    render(<SidebarPanelHeader {...defaultProps} />);
    expect(screen.getByTestId('sidebar-close-button')).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    render(<SidebarPanelHeader {...defaultProps} />);
    fireEvent.click(screen.getByTestId('sidebar-close-button'));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('renders tabs when provided', () => {
    render(<SidebarPanelHeader {...defaultProps} tabs={MOCK_TABS} />);
    expect(screen.getByTestId('sidebar-tab-versions')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar-tab-presence')).toBeInTheDocument();
  });

  it('marks active tab with aria-selected=true', () => {
    render(<SidebarPanelHeader {...defaultProps} tabs={MOCK_TABS} />);
    const activeTab = screen.getByTestId('sidebar-tab-versions');
    expect(activeTab).toHaveAttribute('aria-selected', 'true');
  });

  it('marks inactive tabs with aria-selected=false', () => {
    render(<SidebarPanelHeader {...defaultProps} tabs={MOCK_TABS} />);
    const inactiveTab = screen.getByTestId('sidebar-tab-presence');
    expect(inactiveTab).toHaveAttribute('aria-selected', 'false');
  });

  it('calls onTabChange when a tab is clicked', () => {
    render(<SidebarPanelHeader {...defaultProps} tabs={MOCK_TABS} />);
    fireEvent.click(screen.getByTestId('sidebar-tab-presence'));
    expect(defaultProps.onTabChange).toHaveBeenCalledWith('presence');
  });

  it('renders no tabs section when tabs not provided', () => {
    render(<SidebarPanelHeader {...defaultProps} />);
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
  });

  it('renders empty tabs when empty array provided', () => {
    render(<SidebarPanelHeader {...defaultProps} tabs={[]} />);
    expect(screen.queryByRole('tab')).not.toBeInTheDocument();
  });
});

// -------------------------------------------------------------------------
// SidebarPanelContent
// -------------------------------------------------------------------------
describe('SidebarPanelContent', () => {
  it('renders children', () => {
    render(
      <SidebarPanelContent activePanel="versions">
        <div data-testid="inner-content">Hello</div>
      </SidebarPanelContent>
    );
    expect(screen.getByTestId('inner-content')).toBeInTheDocument();
  });

  it('sets aria role=tabpanel', () => {
    render(
      <SidebarPanelContent activePanel="versions">
        <div />
      </SidebarPanelContent>
    );
    expect(screen.getByRole('tabpanel')).toBeInTheDocument();
  });

  it('sets aria-labelledby matching tab id', () => {
    render(
      <SidebarPanelContent activePanel="versions">
        <div />
      </SidebarPanelContent>
    );
    const panel = screen.getByRole('tabpanel');
    expect(panel).toHaveAttribute('aria-labelledby', 'sidebar-tab-versions');
  });

  it('sets panel id matching activePanel', () => {
    render(
      <SidebarPanelContent activePanel="presence">
        <div />
      </SidebarPanelContent>
    );
    const panel = screen.getByRole('tabpanel');
    expect(panel).toHaveAttribute('id', 'sidebar-panel-content-presence');
  });
});

// -------------------------------------------------------------------------
// SidebarPanel (integration)
// -------------------------------------------------------------------------
describe('SidebarPanel', () => {
  const defaultProps = {
    isOpen: true,
    activePanel: 'versions' as const,
    title: 'Note Panel',
    width: 320,
    onTabChange: vi.fn(),
    onClose: vi.fn(),
  };

  beforeEach(() => vi.clearAllMocks());

  it('renders the panel when isOpen=true', () => {
    render(
      <SidebarPanel {...defaultProps}>
        <div>content</div>
      </SidebarPanel>
    );
    expect(screen.getByTestId('sidebar-panel')).toBeInTheDocument();
  });

  it('does not render when isOpen=false', () => {
    render(
      <SidebarPanel {...defaultProps} isOpen={false}>
        <div>content</div>
      </SidebarPanel>
    );
    expect(screen.queryByTestId('sidebar-panel')).not.toBeInTheDocument();
  });

  it('renders children content', () => {
    render(
      <SidebarPanel {...defaultProps}>
        <div data-testid="child-content">child</div>
      </SidebarPanel>
    );
    expect(screen.getByTestId('child-content')).toBeInTheDocument();
  });

  it('has role=complementary on the panel aside', () => {
    render(
      <SidebarPanel {...defaultProps}>
        <div />
      </SidebarPanel>
    );
    const panel = screen.getByTestId('sidebar-panel');
    expect(panel).toHaveAttribute('role', 'complementary');
  });

  it('has aria-label on the panel', () => {
    render(
      <SidebarPanel {...defaultProps}>
        <div />
      </SidebarPanel>
    );
    const panel = screen.getByTestId('sidebar-panel');
    expect(panel).toHaveAttribute('aria-label', 'Note Panel panel');
  });

  it('calls onClose when Escape key is pressed within panel', () => {
    render(
      <SidebarPanel {...defaultProps}>
        <div />
      </SidebarPanel>
    );
    const panel = screen.getByTestId('sidebar-panel');
    fireEvent.keyDown(panel, { key: 'Escape' });
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('shows mobile backdrop when open', () => {
    render(
      <SidebarPanel {...defaultProps}>
        <div />
      </SidebarPanel>
    );
    expect(screen.getByTestId('sidebar-backdrop')).toBeInTheDocument();
  });

  it('closes when backdrop is clicked', () => {
    render(
      <SidebarPanel {...defaultProps}>
        <div />
      </SidebarPanel>
    );
    fireEvent.click(screen.getByTestId('sidebar-backdrop'));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('renders drag handle when open', () => {
    render(
      <SidebarPanel {...defaultProps}>
        <div />
      </SidebarPanel>
    );
    expect(screen.getByTestId('sidebar-drag-handle')).toBeInTheDocument();
  });

  it('renders tabs when provided', () => {
    render(
      <SidebarPanel {...defaultProps} tabs={MOCK_TABS}>
        <div />
      </SidebarPanel>
    );
    expect(screen.getByTestId('sidebar-tab-versions')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar-tab-presence')).toBeInTheDocument();
  });

  it('calls onTabChange when a tab is clicked', () => {
    render(
      <SidebarPanel {...defaultProps} tabs={MOCK_TABS}>
        <div />
      </SidebarPanel>
    );
    fireEvent.click(screen.getByTestId('sidebar-tab-presence'));
    expect(defaultProps.onTabChange).toHaveBeenCalledWith('presence');
  });

  it('uses default title Panel when not provided', () => {
    const { title: _t, ...withoutTitle } = defaultProps;
    render(
      <SidebarPanel {...withoutTitle}>
        <div />
      </SidebarPanel>
    );
    expect(screen.getByText('Panel')).toBeInTheDocument();
  });
});
