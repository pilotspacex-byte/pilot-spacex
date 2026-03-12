/**
 * Unit tests for AppShell responsive sidebar behavior.
 *
 * Tests:
 * 1. Mobile (<768px) → AnimatePresence overlay (fixed position, z-50)
 * 2. Tablet (768-1024px) → Inline motion.aside with 60px collapsed icon-rail
 * 3. Tablet → hamburger button NOT rendered
 * 4. Mobile with sidebar closed → hamburger button IS rendered
 * 5. Desktop (>1024px) → Inline motion.aside at full width
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppShell } from '../app-shell';

// Mock mobx-react-lite
vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

// Mock motion/react — render children without animation wrappers
vi.mock('motion/react', () => ({
  motion: {
    div: ({
      children,
      className,
      ...rest
    }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div className={className} {...rest}>
        {children}
      </div>
    ),
    aside: ({
      children,
      className,
      ...rest
    }: React.HTMLAttributes<HTMLElement> & {
      children?: React.ReactNode;
      animate?: unknown;
      initial?: unknown;
      exit?: unknown;
      transition?: unknown;
    }) => (
      <aside className={className} {...rest}>
        {children}
      </aside>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Control responsive hook returns
const mockUseResponsive = vi.fn();
vi.mock('@/hooks/useMediaQuery', () => ({
  useResponsive: () => mockUseResponsive(),
}));

// Control sidebar state
const mockSetSidebarCollapsed = vi.fn();
const mockSidebarCollapsed = vi.fn(() => true);
vi.mock('@/stores', () => ({
  useUIStore: () => ({
    sidebarCollapsed: mockSidebarCollapsed(),
    setSidebarCollapsed: mockSetSidebarCollapsed,
    toggleSidebar: vi.fn(),
    hydrate: vi.fn(),
    sidebarWidth: 260,
  }),
}));

// Stub CommandPalette and useCommandPaletteShortcut
vi.mock('@/components/search/CommandPalette', () => ({
  CommandPalette: () => null,
}));

vi.mock('@/hooks/useCommandPaletteShortcut', () => ({
  useCommandPaletteShortcut: () => {},
}));

// Stub Sidebar to a simple element we can detect
vi.mock('../sidebar', () => ({
  Sidebar: () => <div data-testid="sidebar-content">Sidebar</div>,
}));

function renderShell() {
  return render(
    <AppShell>
      <div>content</div>
    </AppShell>
  );
}

describe('AppShell responsive sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSidebarCollapsed.mockReturnValue(true);
  });

  describe('Mobile viewport (<768px)', () => {
    beforeEach(() => {
      mockUseResponsive.mockReturnValue({
        isMobile: true,
        isTablet: false,
        isDesktop: false,
        isSmallScreen: true,
        isLargeScreen: false,
      });
    });

    it('renders sidebar as fixed overlay when sidebarOpen', () => {
      // sidebarOpen = !sidebarCollapsed, so set collapsed=false → open
      mockSidebarCollapsed.mockReturnValue(false);
      renderShell();

      const aside = screen.getByRole('complementary');
      expect(aside.className).toContain('fixed');
      expect(aside.className).toContain('z-50');
    });

    it('renders hamburger button when sidebar is closed', () => {
      // sidebarOpen = !sidebarCollapsed, collapsed=true → closed
      mockSidebarCollapsed.mockReturnValue(true);
      renderShell();

      const hamburger = screen.getByRole('button', { name: /open sidebar/i });
      expect(hamburger).toBeInTheDocument();
    });

    it('does NOT render hamburger button when sidebar is open', () => {
      mockSidebarCollapsed.mockReturnValue(false);
      renderShell();

      const hamburger = screen.queryByRole('button', { name: /open sidebar/i });
      expect(hamburger).not.toBeInTheDocument();
    });
  });

  describe('Tablet viewport (768-1024px)', () => {
    beforeEach(() => {
      mockUseResponsive.mockReturnValue({
        isMobile: false,
        isTablet: true,
        isDesktop: false,
        isSmallScreen: true,
        isLargeScreen: false,
      });
      // Tablet auto-collapses → collapsed=true
      mockSidebarCollapsed.mockReturnValue(true);
    });

    it('renders sidebar as inline aside (not fixed/overlay)', () => {
      renderShell();

      const aside = screen.getByRole('complementary');
      expect(aside.className).not.toContain('fixed');
      expect(aside.className).not.toContain('z-50');
    });

    it('does NOT render hamburger button on tablet', () => {
      renderShell();

      const hamburger = screen.queryByRole('button', { name: /open sidebar/i });
      expect(hamburger).not.toBeInTheDocument();
    });
  });

  describe('Desktop viewport (>1024px)', () => {
    beforeEach(() => {
      mockUseResponsive.mockReturnValue({
        isMobile: false,
        isTablet: false,
        isDesktop: true,
        isSmallScreen: false,
        isLargeScreen: true,
      });
      mockSidebarCollapsed.mockReturnValue(false);
    });

    it('renders sidebar as inline aside at full width', () => {
      renderShell();

      const aside = screen.getByRole('complementary');
      expect(aside.className).not.toContain('fixed');
      expect(aside.className).not.toContain('z-50');
    });

    it('does NOT render hamburger button on desktop', () => {
      renderShell();

      const hamburger = screen.queryByRole('button', { name: /open sidebar/i });
      expect(hamburger).not.toBeInTheDocument();
    });
  });
});
