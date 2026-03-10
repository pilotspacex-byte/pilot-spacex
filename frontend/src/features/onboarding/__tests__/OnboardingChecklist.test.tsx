/**
 * Integration tests for OnboardingChecklist.
 *
 * ONBD-03: Inline ApiKeySetupStep expansion for ai_providers step.
 * ONBD-04: Success toast on role skill save (via useCreateRoleSkill).
 * ONBD-05: Settings links per step.
 * Source: FR-001, FR-002, FR-003, FR-013, US1
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { toast } from 'sonner';

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

vi.mock('@/services/api/onboarding', () => ({
  onboardingApi: {
    getOnboardingState: vi.fn(),
    validateProviderKey: vi.fn(),
    dismissOnboarding: vi.fn(),
    updateOnboardingStep: vi.fn(),
    createGuidedNote: vi.fn(),
  },
}));

vi.mock('@/services/api/role-skills', () => ({
  roleSkillsApi: {
    getTemplates: vi.fn(),
    getRoleSkills: vi.fn(),
    createRoleSkill: vi.fn(),
  },
}));

// Shared mutable mock state for OnboardingStore
const mockOnboardingStore = {
  isModalOpen: true,
  activeStep: null as string | null,
  showingCelebration: false,
  closeModal: vi.fn(),
  setActiveStep: vi.fn(),
  setInviteDialogFromOnboarding: vi.fn(),
  triggerCelebration: vi.fn(),
  hydrate: vi.fn(),
};

const mockRoleSkillStore = {
  selectedRoles: [] as string[],
  clearSelectedRoles: vi.fn(),
  setGenerationStep: vi.fn(),
  toggleRole: vi.fn(),
  setExperienceDescription: vi.fn(),
  customRoleDescription: '',
};

vi.mock('@/stores/RootStore', () => ({
  useOnboardingStore: () => mockOnboardingStore,
  useRoleSkillStore: () => mockRoleSkillStore,
  StoreContext: React.createContext(null),
  RootStore: class {},
}));

// ── Imports (after mocks) ────────────────────────────────────────────────────

import { OnboardingChecklist } from '../components/OnboardingChecklist';
import * as useOnboardingStateModule from '../hooks/useOnboardingState';
import * as useRoleSkillActionsModule from '../hooks/useRoleSkillActions';
import { roleSkillsApi } from '@/services/api/role-skills';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const allIncompleteState = {
  workspaceId: 'ws-uuid-123',
  steps: {
    ai_providers: false,
    invite_members: false,
    role_setup: false,
    first_note: false,
  },
  completionPercentage: 0,
  dismissedAt: null,
  completedAt: null,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

const defaultProps = {
  workspaceId: 'ws-uuid-123',
  workspaceSlug: 'my-workspace',
};

function mockOnboardingData(state = allIncompleteState) {
  vi.spyOn(useOnboardingStateModule, 'useOnboardingState').mockReturnValue({
    data: state,
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof useOnboardingStateModule.useOnboardingState>);
  vi.spyOn(useRoleSkillActionsModule, 'useRoleTemplates').mockReturnValue({
    data: [],
  } as unknown as ReturnType<typeof useRoleSkillActionsModule.useRoleTemplates>);
  vi.spyOn(useRoleSkillActionsModule, 'useRoleSkills').mockReturnValue({
    data: [],
  } as unknown as ReturnType<typeof useRoleSkillActionsModule.useRoleSkills>);
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('OnboardingChecklist — ONBD-03: inline ApiKeySetupStep', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockOnboardingStore.activeStep = null;
    mockOnboardingStore.isModalOpen = true;
    mockOnboardingStore.showingCelebration = false;
  });

  it('shows ApiKeySetupStep inline when ai_providers step is active', () => {
    mockOnboardingData();
    mockOnboardingStore.activeStep = 'ai_providers';

    const wrapper = createWrapper();
    render(<OnboardingChecklist {...defaultProps} />, { wrapper });

    expect(screen.getByText('Anthropic API Key')).toBeInTheDocument();
    expect(screen.getByText('sk-ant-')).toBeInTheDocument();
  });

  it('does NOT show ApiKeySetupStep when ai_providers step is not active', () => {
    mockOnboardingData();
    mockOnboardingStore.activeStep = null;

    const wrapper = createWrapper();
    render(<OnboardingChecklist {...defaultProps} />, { wrapper });

    expect(screen.queryByText('Anthropic API Key')).not.toBeInTheDocument();
  });

  it('does NOT show ApiKeySetupStep when ai_providers step is already complete', () => {
    mockOnboardingData({
      ...allIncompleteState,
      steps: { ...allIncompleteState.steps, ai_providers: true },
      completionPercentage: 25,
    });
    mockOnboardingStore.activeStep = 'ai_providers';

    const wrapper = createWrapper();
    render(<OnboardingChecklist {...defaultProps} />, { wrapper });

    expect(screen.queryByText('Anthropic API Key')).not.toBeInTheDocument();
  });
});

describe('OnboardingChecklist — ONBD-05: settings links', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockOnboardingStore.activeStep = null;
    mockOnboardingStore.isModalOpen = true;
    mockOnboardingStore.showingCelebration = false;
  });

  it('renders Go to settings links for ai_providers, invite_members, role_setup (not first_note)', () => {
    mockOnboardingData();

    const wrapper = createWrapper();
    render(<OnboardingChecklist {...defaultProps} />, { wrapper });

    const settingsLinks = screen.getAllByRole('link', { name: /go to settings/i });
    expect(settingsLinks).toHaveLength(3);

    const hrefs = settingsLinks.map((l) => l.getAttribute('href'));
    expect(hrefs).toContain('/my-workspace/settings/ai-providers');
    expect(hrefs).toContain('/my-workspace/settings/members');
    expect(hrefs).toContain('/my-workspace/settings/skills');
    // first_note must NOT have a settings link
    expect(hrefs).not.toContain(expect.stringContaining('first_note'));
  });

  it('does NOT render Go to settings link for completed steps', () => {
    mockOnboardingData({
      ...allIncompleteState,
      steps: {
        ai_providers: true, // completed — no link
        invite_members: false,
        role_setup: false,
        first_note: false,
      },
      completionPercentage: 25,
    });

    const wrapper = createWrapper();
    render(<OnboardingChecklist {...defaultProps} />, { wrapper });

    // Only 2 links: invite_members + role_setup
    const settingsLinks = screen.getAllByRole('link', { name: /go to settings/i });
    expect(settingsLinks).toHaveLength(2);

    const hrefs = settingsLinks.map((l) => l.getAttribute('href'));
    expect(hrefs).not.toContain('/my-workspace/settings/ai-providers');
  });
});

describe('useCreateRoleSkill — ONBD-04: success toast', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fires toast.success("Skill saved and active") on mutation success', async () => {
    const mockSkill = {
      id: 'skill-1',
      roleType: 'developer' as const,
      roleName: 'Developer',
      skillContent: '# Developer',
      experienceDescription: null,
      isPrimary: true,
      templateVersion: 1,
      templateUpdateAvailable: false,
      wordCount: 5,
      createdAt: '2026-01-01T00:00:00Z',
      updatedAt: '2026-01-01T00:00:00Z',
    };

    vi.mocked(roleSkillsApi.createRoleSkill).mockResolvedValue(mockSkill);
    vi.mocked(roleSkillsApi.getRoleSkills).mockResolvedValue({ skills: [] });

    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useRoleSkillActionsModule.useCreateRoleSkill({ workspaceId: 'ws-uuid-123' }),
      { wrapper }
    );

    result.current.mutate({
      roleType: 'developer',
      roleName: 'Developer',
      skillContent: '# Developer',
      isPrimary: true,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith('Skill saved and active');
  });

  it('does NOT fire toast.success when mutation fails', async () => {
    vi.mocked(roleSkillsApi.createRoleSkill).mockRejectedValue(new Error('Server error'));

    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useRoleSkillActionsModule.useCreateRoleSkill({ workspaceId: 'ws-uuid-123' }),
      { wrapper }
    );

    result.current.mutate({
      roleType: 'developer',
      roleName: 'Developer',
      skillContent: '# Developer',
      isPrimary: true,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(toast.success).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith('Failed to save role skill', expect.any(Object));
  });
});
