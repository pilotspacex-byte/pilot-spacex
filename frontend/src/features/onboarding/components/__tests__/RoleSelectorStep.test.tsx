/**
 * Component tests for RoleSelectorStep.
 *
 * T023: Tests for role selection grid rendering, interaction, and accessibility.
 * Source: FR-001, FR-002, FR-018, US1
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StoreContext, RootStore } from '@/stores/RootStore';
import { RoleSelectorStep } from '../RoleSelectorStep';
import { roleSkillsApi } from '@/services/api/role-skills';

// Mock the role-skills API
vi.mock('@/services/api/role-skills', () => ({
  roleSkillsApi: {
    getTemplates: vi.fn(),
  },
}));

const mockTemplates = [
  {
    id: '1',
    roleType: 'business_analyst' as const,
    displayName: 'Business Analyst',
    description: 'Requirements & analysis',
    icon: 'FileSearch',
    sortOrder: 1,
    version: 1,
    defaultSkillContent: '# Business Analyst',
  },
  {
    id: '2',
    roleType: 'developer' as const,
    displayName: 'Developer',
    description: 'Code & architecture',
    icon: 'Code',
    sortOrder: 3,
    version: 1,
    defaultSkillContent: '# Developer',
  },
  {
    id: '3',
    roleType: 'tester' as const,
    displayName: 'Tester',
    description: 'Quality & test plans',
    icon: 'TestTube',
    sortOrder: 4,
    version: 1,
    defaultSkillContent: '# Tester',
  },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const rootStore = new RootStore();

  return {
    rootStore,
    Wrapper({ children }: { children: React.ReactNode }) {
      return React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(StoreContext.Provider, { value: rootStore }, children)
      );
    },
  };
}

describe('RoleSelectorStep', () => {
  const defaultProps = {
    onContinue: vi.fn(),
    onSkip: vi.fn(),
    onBack: vi.fn(),
    onCustomRole: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(roleSkillsApi.getTemplates).mockResolvedValue({
      templates: mockTemplates,
    });
  });

  describe('rendering', () => {
    it('should render the title and description', async () => {
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      expect(await screen.findByText('Set Up Your Role')).toBeInTheDocument();
      expect(
        screen.getByText(/Select your SDLC role to personalize your AI assistant/)
      ).toBeInTheDocument();
    });

    it('should render role cards from templates', async () => {
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      expect(await screen.findByText('Business Analyst')).toBeInTheDocument();
      expect(screen.getByText('Developer')).toBeInTheDocument();
      expect(screen.getByText('Tester')).toBeInTheDocument();
    });

    it('should render the Custom Role card', async () => {
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      expect(await screen.findByText('Custom Role')).toBeInTheDocument();
    });

    it('should show loading state while templates are fetching', () => {
      vi.mocked(roleSkillsApi.getTemplates).mockReturnValue(new Promise(() => {}));
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText('Loading roles...')).toBeInTheDocument();
    });
  });

  describe('selection behavior', () => {
    it('should toggle role selection on click', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      const devCard = await screen.findByTestId('role-card-developer');
      await user.click(devCard);

      expect(rootStore.roleSkill.selectedRoles).toContain('developer');
    });

    it('should deselect on second click', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      const devCard = await screen.findByTestId('role-card-developer');
      await user.click(devCard);
      await user.click(devCard);

      expect(rootStore.roleSkill.selectedRoles).not.toContain('developer');
    });

    it('should show selection summary bar when roles are selected', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      const devCard = await screen.findByTestId('role-card-developer');
      await user.click(devCard);

      expect(screen.getByText(/developer \(primary\)/i)).toBeInTheDocument();
    });

    it('should call onCustomRole when Custom Role card is clicked', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      const customCard = await screen.findByTestId('role-card-custom');
      await user.click(customCard);

      expect(defaultProps.onCustomRole).toHaveBeenCalledOnce();
    });
  });

  describe('continue button', () => {
    it('should be disabled when no roles selected', async () => {
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      const button = await screen.findByRole('button', { name: /Continue/i });
      expect(button).toBeDisabled();
    });

    it('should be enabled when at least one role is selected', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      const devCard = await screen.findByTestId('role-card-developer');
      await user.click(devCard);

      const button = screen.getByRole('button', { name: /Continue/i });
      expect(button).toBeEnabled();
    });

    it('should call onContinue when clicked', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      const devCard = await screen.findByTestId('role-card-developer');
      await user.click(devCard);

      const button = screen.getByRole('button', { name: /Continue/i });
      await user.click(button);

      expect(defaultProps.onContinue).toHaveBeenCalledOnce();
    });

    it('should show count when multiple roles selected', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      const devCard = await screen.findByTestId('role-card-developer');
      const testerCard = screen.getByTestId('role-card-tester');
      await user.click(devCard);
      await user.click(testerCard);

      expect(screen.getByRole('button', { name: /Set Up 2 Skills/i })).toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('should call onBack when Back button is clicked', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      await screen.findByText('Back');
      await user.click(screen.getByText('Back'));

      expect(defaultProps.onBack).toHaveBeenCalledOnce();
    });

    it('should call onSkip when Skip button is clicked', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      await screen.findByText('Skip');
      await user.click(screen.getByText('Skip'));

      expect(defaultProps.onSkip).toHaveBeenCalledOnce();
    });
  });

  describe('accessibility', () => {
    it('should have role="group" on the grid container', async () => {
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      await screen.findByRole('group', { name: 'Select your SDLC roles' });
    });

    it('should have live region for selection count', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} />, { wrapper: Wrapper });

      const devCard = await screen.findByTestId('role-card-developer');
      await user.click(devCard);

      const liveRegion = screen.getByRole('status');
      expect(liveRegion).toHaveTextContent(/1 of 3 roles selected/);
    });
  });

  describe('existing skills', () => {
    it('should show "Already set up" for roles with existing skills', async () => {
      const { Wrapper } = createWrapper();
      render(
        <RoleSelectorStep {...defaultProps} existingSkillRoleTypes={['developer']} />,
        { wrapper: Wrapper }
      );

      await screen.findByText('Developer');
      expect(screen.getByText('Already set up')).toBeInTheDocument();
    });

    it('should not toggle selection for existing skill roles', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      render(
        <RoleSelectorStep {...defaultProps} existingSkillRoleTypes={['developer']} />,
        { wrapper: Wrapper }
      );

      const devCard = await screen.findByTestId('role-card-developer');
      await user.click(devCard);

      expect(rootStore.roleSkill.selectedRoles).not.toContain('developer');
    });

    it('should still allow selecting non-existing roles', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      render(
        <RoleSelectorStep {...defaultProps} existingSkillRoleTypes={['developer']} />,
        { wrapper: Wrapper }
      );

      const testerCard = await screen.findByTestId('role-card-tester');
      await user.click(testerCard);

      expect(rootStore.roleSkill.selectedRoles).toContain('tester');
    });
  });

  describe('badges', () => {
    it('should show "Your default" badge on default role card', async () => {
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} defaultRole="developer" />, { wrapper: Wrapper });

      await screen.findByText('Developer');
      expect(screen.getByText('Your default')).toBeInTheDocument();
    });

    it('should show "Suggested by owner" badge on suggested role card', async () => {
      const { Wrapper } = createWrapper();
      render(<RoleSelectorStep {...defaultProps} suggestedRole="tester" />, { wrapper: Wrapper });

      await screen.findByText('Tester');
      expect(screen.getByText('Suggested by owner')).toBeInTheDocument();
    });
  });
});
