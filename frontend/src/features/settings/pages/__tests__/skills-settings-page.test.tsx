/**
 * Tests for SkillsSettingsPage (Phase 20 restructured).
 *
 * Covers: My Skills section, Template Catalog, admin actions.
 * Source: P20-09, P20-10
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import * as React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/',
}));

const mockWorkspaceStore = {
  currentUserRole: 'member' as string | null,
  isAdmin: false,
  getWorkspaceBySlug: vi.fn().mockReturnValue({
    id: 'ws-123',
    slug: 'test-workspace',
  }),
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: mockWorkspaceStore,
    roleSkillStore: {
      editingSkillId: null,
      setEditingSkillId: vi.fn(),
      clearEditingSkillId: vi.fn(),
    },
  }),
}));

vi.mock('@/stores/RootStore', () => ({
  useRoleSkillStore: () => ({
    editingSkillId: null,
    setEditingSkillId: vi.fn(),
    clearEditingSkillId: vi.fn(),
  }),
}));

// Mock user-skills hooks
const mockUserSkills = vi.fn();
const mockUpdateUserSkill = vi.fn();
const mockDeleteUserSkill = vi.fn();

vi.mock('@/services/api/user-skills', () => ({
  useUserSkills: (...args: unknown[]) => mockUserSkills(...args),
  useCreateUserSkill: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateUserSkill: () => ({ mutate: mockUpdateUserSkill, isPending: false }),
  useDeleteUserSkill: () => ({ mutate: mockDeleteUserSkill, isPending: false }),
}));

// Mock skill-templates hooks
vi.mock('@/services/api/skill-templates', () => ({
  useSkillTemplates: () => ({ data: [], isLoading: false, isError: false, error: null }),
  useCreateSkillTemplate: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateSkillTemplate: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteSkillTemplate: () => ({ mutate: vi.fn(), isPending: false }),
}));

// Mock workspace-role-skills (legacy, may still be imported transitively)
vi.mock('@/services/api/workspace-role-skills', () => ({
  useWorkspaceRoleSkills: () => ({ data: { skills: [] } }),
  useActivateWorkspaceSkill: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteWorkspaceSkill: () => ({ mutate: vi.fn(), isPending: false }),
  useGenerateWorkspaceSkill: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

// Mock onboarding hooks (for SkillGeneratorModal)
vi.mock('@/features/onboarding/hooks', () => ({
  useRoleSkills: () => ({ data: [], isLoading: false, isError: false, error: null }),
  useRoleTemplates: () => ({ data: [] }),
  useUpdateRoleSkill: () => ({ mutate: vi.fn(), isPending: false }),
  useRegenerateSkill: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteRoleSkill: () => ({ mutate: vi.fn() }),
  useCreateRoleSkill: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
  useGenerateSkill: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

vi.mock('@/services/api', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(), patch: vi.fn() },
}));

vi.mock('@/components/role-skill/role-icons', () => ({
  getRoleIcon: () => {
    return function MockIcon(props: Record<string, unknown>) {
      return React.createElement('span', { 'data-testid': 'role-icon', ...props });
    };
  },
}));

// Mock ChatView (lazy-loaded in skills page)
vi.mock('@/features/ai/ChatView/ChatView', () => ({
  ChatView: function MockChatView() {
    return React.createElement('div', { 'data-testid': 'chat-view' }, 'Mock ChatView');
  },
}));

// Mock AI store
vi.mock('@/stores/ai/AIStore', () => ({
  getAIStore: () => ({
    pilotSpace: {
      workspaceId: null,
      setWorkspaceId: vi.fn(),
    },
    approval: {},
  }),
}));

// Mock useMediaQuery — default to desktop (not small screen)
vi.mock('@/hooks/useMediaQuery', () => ({
  useMediaQuery: () => false,
}));

// Mock ResizablePanel components
vi.mock('@/components/ui/resizable', () => ({
  ResizablePanelGroup: ({ children, ...props }: { children: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'resizable-panel-group', ...props }, children),
  ResizablePanel: ({ children, ...props }: { children: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'resizable-panel', ...props }, children),
  ResizableHandle: () => React.createElement('div', { 'data-testid': 'resizable-handle' }),
}));

// Mock CollapsedChatStrip
vi.mock('@/components/editor/CollapsedChatStrip', () => ({
  CollapsedChatStrip: ({ onClick }: { onClick: () => void }) =>
    React.createElement('button', { 'data-testid': 'collapsed-chat-strip', onClick }, 'PilotSpace Agent'),
}));

// Mock motion
vi.mock('motion/react', () => ({
  motion: {
    aside: ({ children, ...props }: { children: React.ReactNode }) =>
      React.createElement('aside', props, children),
  },
}));

import { SkillsSettingsPage } from '../skills-settings-page';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

function renderPage() {
  return render(React.createElement(SkillsSettingsPage), { wrapper: createWrapper() });
}

const mockUserSkillsList = [
  {
    id: 'us-1',
    user_id: 'u-1',
    workspace_id: 'ws-123',
    template_id: 'tpl-1',
    skill_content: 'You are an expert developer.',
    experience_description: '10 years React',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    template_name: 'Senior Developer',
  },
  {
    id: 'us-2',
    user_id: 'u-1',
    workspace_id: 'ws-123',
    template_id: null,
    skill_content: 'Custom skill content here.',
    experience_description: null,
    is_active: false,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    template_name: null,
  },
];

describe('SkillsSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWorkspaceStore.currentUserRole = 'member';
    mockWorkspaceStore.isAdmin = false;
    mockWorkspaceStore.getWorkspaceBySlug.mockReturnValue({
      id: 'ws-123',
      slug: 'test-workspace',
    });
  });

  describe('loading state', () => {
    it('should show loading skeleton when loading', () => {
      mockUserSkills.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      });

      const { container } = renderPage();
      expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('should show error alert when loading fails', () => {
      mockUserSkills.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error('Network error'),
      });

      renderPage();
      expect(screen.getByText(/Failed to load skills.*Network error/)).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty message when no user skills', () => {
      mockUserSkills.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      expect(screen.getByText('Personalize your AI co-pilot')).toBeInTheDocument();
    });
  });

  describe('skills list', () => {
    it('should render user skills with My Skills section', () => {
      mockUserSkills.mockReturnValue({
        data: mockUserSkillsList,
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      expect(screen.getByText('My Skills')).toBeInTheDocument();
      expect(screen.getByText('Senior Developer')).toBeInTheDocument();
      expect(screen.getByText('Custom Skill')).toBeInTheDocument();
    });

    it('should render Add Skill button', () => {
      mockUserSkills.mockReturnValue({
        data: mockUserSkillsList,
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      expect(screen.getByRole('button', { name: /Add Skill/ })).toBeEnabled();
    });

    it('should show Skill Templates section heading', () => {
      mockUserSkills.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      expect(screen.getByText('Skill Templates')).toBeInTheDocument();
    });
  });

  describe('guest view', () => {
    it('should show guest message for guest users', () => {
      mockWorkspaceStore.currentUserRole = 'guest';
      mockUserSkills.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      expect(screen.getByText(/Member or higher access/)).toBeInTheDocument();
    });
  });

  describe('admin features', () => {
    it('should show Create Template button for admins', () => {
      mockWorkspaceStore.currentUserRole = 'admin';
      mockWorkspaceStore.isAdmin = true;
      mockUserSkills.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      expect(screen.getByRole('button', { name: /Create Template/ })).toBeInTheDocument();
    });

    it('should NOT show Create Template button for members', () => {
      mockUserSkills.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      expect(screen.queryByRole('button', { name: /Create Template/ })).not.toBeInTheDocument();
    });
  });

  describe('Create Skill button', () => {
    it('should render "Create Skill" button on skills tab', () => {
      mockUserSkills.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      expect(screen.getByRole('button', { name: /Create Skill/ })).toBeInTheDocument();
    });

    it('should open ChatView panel when Create Skill is clicked', async () => {
      const user = userEvent.setup();
      mockUserSkills.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      // Initially shows collapsed chat strip (desktop, chat closed)
      expect(screen.getByTestId('collapsed-chat-strip')).toBeInTheDocument();

      const createSkillBtn = screen.getByRole('button', { name: /Create Skill/ });
      await user.click(createSkillBtn);

      // After clicking, ChatView should be rendered (lazy loaded via Suspense)
      const chatView = await screen.findByTestId('chat-view');
      expect(chatView).toBeInTheDocument();
    });
  });

  describe('ChatView layout', () => {
    it('should show collapsed chat strip on desktop when chat is closed', () => {
      mockUserSkills.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      expect(screen.getByTestId('collapsed-chat-strip')).toBeInTheDocument();
    });
  });

  describe('skill deletion', () => {
    it('should show delete confirmation on Delete click', async () => {
      const user = userEvent.setup();
      mockUserSkills.mockReturnValue({
        data: mockUserSkillsList,
        isLoading: false,
        isError: false,
        error: null,
      });

      renderPage();
      const deleteButtons = screen.getAllByLabelText('Delete skill');
      await user.click(deleteButtons[0]!);

      expect(screen.getByText(/Remove Senior Developer Skill\?/)).toBeInTheDocument();
    });
  });
});
