/**
 * Tests for SkillsSettingsPage.
 *
 * T040: Skills settings page rendering, CRUD operations, states.
 * Source: FR-009, FR-010, FR-015, FR-018, US6
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/',
}));

const mockRoleSkillStore = {
  editingSkillId: null as string | null,
  selectedRoles: [] as string[],
  isGenerating: false,
  customRoleDescription: '',
  setEditingSkillId: vi.fn(),
  clearEditingSkillId: vi.fn(),
  setGenerationStep: vi.fn(),
  clearSelectedRoles: vi.fn(),
  toggleRole: vi.fn(),
  setExperienceDescription: vi.fn(),
};

const mockWorkspaceStore = {
  currentUserRole: 'member' as string | null,
  getWorkspaceBySlug: vi.fn().mockReturnValue({
    id: 'ws-123',
    slug: 'test-workspace',
  }),
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: mockWorkspaceStore,
    roleSkillStore: mockRoleSkillStore,
  }),
}));

vi.mock('@/stores/RootStore', () => ({
  useRoleSkillStore: () => mockRoleSkillStore,
}));

const mockUseRoleSkills = vi.fn();
const mockUseRoleTemplates = vi.fn();
const mockUpdateMutate = vi.fn();
const mockDeleteMutate = vi.fn();
const mockCreateMutate = vi.fn();
const mockRegenerateMutateAsync = vi.fn();

vi.mock('@/features/onboarding/hooks', () => ({
  useRoleSkills: (...args: unknown[]) => mockUseRoleSkills(...args),
  useRoleTemplates: () => mockUseRoleTemplates(),
  useUpdateRoleSkill: () => ({ mutate: mockUpdateMutate, isPending: false }),
  useRegenerateSkill: () => ({ mutateAsync: mockRegenerateMutateAsync, isPending: false }),
  useDeleteRoleSkill: () => ({ mutate: mockDeleteMutate }),
  useCreateRoleSkill: () => ({ mutate: mockCreateMutate }),
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
      return <span data-testid="role-icon" {...props} />;
    };
  },
}));

import { SkillsSettingsPage } from '../skills-settings-page';

const mockSkills = [
  {
    id: 'skill-1',
    roleType: 'developer' as const,
    roleName: 'Developer',
    skillContent: '# Developer\n\n## Focus Areas\n- Code quality',
    experienceDescription: 'Full-stack TypeScript dev',
    isPrimary: true,
    templateVersion: 1,
    templateUpdateAvailable: false,
    wordCount: 10,
    createdAt: '2026-02-06T00:00:00Z',
    updatedAt: '2026-02-06T00:00:00Z',
  },
  {
    id: 'skill-2',
    roleType: 'tester' as const,
    roleName: 'Tester',
    skillContent: '# Tester\n\n## Focus Areas\n- Test coverage',
    experienceDescription: null,
    isPrimary: false,
    templateVersion: 1,
    templateUpdateAvailable: false,
    wordCount: 8,
    createdAt: '2026-02-06T01:00:00Z',
    updatedAt: '2026-02-06T01:00:00Z',
  },
];

const mockTemplates = [
  {
    id: 'tmpl-1',
    roleType: 'developer' as const,
    displayName: 'Developer',
    description: 'Code & architecture',
    icon: 'Code',
    sortOrder: 3,
    version: 1,
    defaultSkillContent: '# Developer Default',
  },
];

describe('SkillsSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRoleSkillStore.editingSkillId = null;
    mockWorkspaceStore.currentUserRole = 'member';
    mockWorkspaceStore.getWorkspaceBySlug.mockReturnValue({
      id: 'ws-123',
      slug: 'test-workspace',
    });
    mockUseRoleTemplates.mockReturnValue({ data: mockTemplates });
  });

  describe('loading state', () => {
    it('should show loading skeleton when loading', () => {
      mockUseRoleSkills.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      });

      const { container } = render(<SkillsSettingsPage />);
      expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('should show error alert when loading fails', () => {
      mockUseRoleSkills.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error('Network error'),
      });

      render(<SkillsSettingsPage />);
      expect(screen.getByText(/Failed to load skills.*Network error/)).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty state when no skills configured', () => {
      mockUseRoleSkills.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<SkillsSettingsPage />);
      expect(screen.getByText('No roles configured')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Set Up Your Role/ })).toBeInTheDocument();
    });
  });

  describe('skills list', () => {
    it('should render skills with header and actions', () => {
      mockUseRoleSkills.mockReturnValue({
        data: mockSkills,
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<SkillsSettingsPage />);
      expect(screen.getByText('AI Skills')).toBeInTheDocument();
      expect(screen.getByText('Developer')).toBeInTheDocument();
      expect(screen.getByText('Tester')).toBeInTheDocument();
      expect(screen.getByText('PRIMARY')).toBeInTheDocument();
    });

    it('should show slots remaining', () => {
      mockUseRoleSkills.mockReturnValue({
        data: mockSkills,
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<SkillsSettingsPage />);
      expect(screen.getByText('1 slot left')).toBeInTheDocument();
    });

    it('should render Add Role button', () => {
      mockUseRoleSkills.mockReturnValue({
        data: mockSkills,
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<SkillsSettingsPage />);
      expect(screen.getByRole('button', { name: /Add Role/ })).toBeEnabled();
    });

    it('should show primary skill first', () => {
      mockUseRoleSkills.mockReturnValue({
        data: [mockSkills[1]!, mockSkills[0]!],
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<SkillsSettingsPage />);
      const articles = screen.getAllByRole('article');
      expect(articles[0]).toHaveAttribute('aria-label', 'Developer role skill');
    });
  });

  describe('max roles', () => {
    it('should show warning and disable Add when 3 roles configured', () => {
      const threeSkills = [
        ...mockSkills,
        {
          ...mockSkills[0]!,
          id: 'skill-3',
          roleType: 'architect' as const,
          roleName: 'Architect',
          isPrimary: false,
        },
      ];

      mockUseRoleSkills.mockReturnValue({
        data: threeSkills,
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<SkillsSettingsPage />);
      expect(screen.getByText(/Maximum 3 roles per workspace reached/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Add Role/ })).toBeDisabled();
    });
  });

  describe('guest view', () => {
    it('should show guest message for guest users', () => {
      mockWorkspaceStore.currentUserRole = 'guest';
      mockUseRoleSkills.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<SkillsSettingsPage />);
      expect(screen.getByText(/Member or higher access/)).toBeInTheDocument();
    });
  });

  describe('skill actions', () => {
    it('should open remove confirmation dialog on Remove click', async () => {
      const user = userEvent.setup();
      mockUseRoleSkills.mockReturnValue({
        data: mockSkills,
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<SkillsSettingsPage />);
      const removeButtons = screen.getAllByRole('button', { name: /Remove/ });
      await user.click(removeButtons[0]!);

      expect(screen.getByText(/Remove Developer Role\?/)).toBeInTheDocument();
      expect(screen.getByText(/permanently deleted/)).toBeInTheDocument();
    });

    it('should call deleteSkill when remove is confirmed', async () => {
      const user = userEvent.setup();
      mockUseRoleSkills.mockReturnValue({
        data: mockSkills,
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<SkillsSettingsPage />);
      const removeButtons = screen.getAllByRole('button', { name: /Remove/ });
      await user.click(removeButtons[0]!);

      const confirmButton = screen.getByRole('button', { name: /Remove Role/ });
      await user.click(confirmButton);

      expect(mockDeleteMutate).toHaveBeenCalledWith('skill-1', expect.any(Object));
    });

    it('should open reset confirmation dialog on Reset click', async () => {
      const user = userEvent.setup();
      mockUseRoleSkills.mockReturnValue({
        data: mockSkills,
        isLoading: false,
        isError: false,
        error: null,
      });

      render(<SkillsSettingsPage />);
      const resetButtons = screen.getAllByRole('button', { name: /Reset/ });
      await user.click(resetButtons[0]!);

      expect(screen.getByText(/Reset to Default Template\?/)).toBeInTheDocument();
    });
  });
});
