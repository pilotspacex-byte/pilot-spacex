import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Workspace } from '@/types';

// Mock MobX observer as passthrough
vi.mock('mobx-react-lite', () => ({
  observer: (component: React.FC) => component,
}));

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock workspace-nav utilities
const mockGetLastWorkspacePath = vi.fn();
vi.mock('@/lib/workspace-nav', () => ({
  getLastWorkspacePath: (slug: string) => mockGetLastWorkspacePath(slug),
}));

// Workspace list fixture
const wsA: Workspace = {
  id: 'ws-a',
  name: 'Workspace Alpha',
  slug: 'ws-alpha',
  memberCount: 3,
  memberIds: [],
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
  ownerId: 'user-1',
};

const wsB: Workspace = {
  id: 'ws-b',
  name: 'Workspace Beta',
  slug: 'ws-beta',
  memberCount: 1,
  memberIds: [],
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
  ownerId: 'user-1',
};

// Mock workspace store
const mockFetchWorkspaces = vi.fn();
const mockWorkspaceStore = {
  workspaceList: [wsA, wsB],
  currentWorkspace: wsA,
  selectWorkspace: vi.fn(),
  fetchWorkspaces: mockFetchWorkspaces,
};

vi.mock('@/stores', () => ({
  useWorkspaceStore: () => mockWorkspaceStore,
}));

// Mock workspace-selector (addRecentWorkspace)
vi.mock('@/components/workspace-selector', () => ({
  addRecentWorkspace: vi.fn(),
}));

// Minimal UI component stubs
vi.mock('@/components/ui/popover', () => ({
  Popover: ({
    children,
    open,
    onOpenChange,
  }: {
    children: React.ReactNode;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
  }) => (
    <div data-open={open} data-testid="popover-root" onClick={() => onOpenChange?.(!open)}>
      {children}
    </div>
  ),
  PopoverTrigger: ({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) =>
    asChild ? <>{children}</> : <div>{children}</div>,
  PopoverContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="popover-content">{children}</div>
  ),
}));

vi.mock('@/components/ui/separator', () => ({
  Separator: () => <hr />,
}));

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) =>
    asChild ? <>{children}</> : <div>{children}</div>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => (
    <button onClick={onClick}>{children}</button>
  ),
}));

vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogDescription: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('@/components/ui/input', () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}));

vi.mock('@/components/ui/label', () => ({
  Label: ({ children }: { children: React.ReactNode }) => <label>{children}</label>,
}));

vi.mock('@/services/api/workspaces', () => ({
  workspacesApi: { get: vi.fn(), create: vi.fn() },
}));

vi.mock('@/services/api/client', () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

// Import AFTER all mocks are in place
import { WorkspaceSwitcher } from '../layout/workspace-switcher';

describe('WorkspaceSwitcher', () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockGetLastWorkspacePath.mockClear();
    mockWorkspaceStore.selectWorkspace.mockClear();
    mockFetchWorkspaces.mockClear();
  });

  it('renders member count for each workspace', () => {
    render(<WorkspaceSwitcher currentSlug="ws-alpha" />);

    // Member counts rendered correctly (plural vs singular)
    expect(screen.getByText('3 members')).toBeInTheDocument();
    expect(screen.getByText('1 member')).toBeInTheDocument();

    // Workspace Beta (only appears in list, not in trigger) should be visible
    expect(screen.getByText('Workspace Beta')).toBeInTheDocument();
  });

  it('navigates to lastPath when switching workspace with saved path', () => {
    mockGetLastWorkspacePath.mockReturnValue('/ws-beta/issues');

    render(<WorkspaceSwitcher currentSlug="ws-alpha" />);

    // Click workspace Beta
    const wsBetaButton = screen.getByRole('button', { name: /Workspace Beta/i });
    fireEvent.click(wsBetaButton);

    expect(mockGetLastWorkspacePath).toHaveBeenCalledWith('ws-beta');
    expect(mockPush).toHaveBeenCalledWith('/ws-beta/issues');
  });

  it('navigates to workspace root when no last path saved', () => {
    mockGetLastWorkspacePath.mockReturnValue(null);

    render(<WorkspaceSwitcher currentSlug="ws-alpha" />);

    // Click workspace Beta
    const wsBetaButton = screen.getByRole('button', { name: /Workspace Beta/i });
    fireEvent.click(wsBetaButton);

    expect(mockGetLastWorkspacePath).toHaveBeenCalledWith('ws-beta');
    expect(mockPush).toHaveBeenCalledWith('/ws-beta');
  });

  it('fetches workspaces when popover opens', () => {
    render(<WorkspaceSwitcher currentSlug="ws-alpha" />);

    // fetchWorkspaces should NOT be called on initial render (popover is closed)
    expect(mockFetchWorkspaces).not.toHaveBeenCalled();

    // Click the trigger button to open the popover
    const triggerButton = screen.getByRole('button', { name: /Switch workspace/i });
    act(() => {
      fireEvent.click(triggerButton);
    });

    expect(mockFetchWorkspaces).toHaveBeenCalledTimes(1);
  });

  it('does not fetch workspaces when popover is closed', () => {
    render(<WorkspaceSwitcher currentSlug="ws-alpha" />);
    expect(mockFetchWorkspaces).not.toHaveBeenCalled();
  });
});
