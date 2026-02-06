/**
 * Component tests for SkillGenerationWizard.
 *
 * T023: Tests for 3-path skill generation wizard.
 * Source: FR-001, FR-002, FR-003, FR-004, US1, US2
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StoreContext, RootStore } from '@/stores/RootStore';
import { SkillGenerationWizard } from '../SkillGenerationWizard';
import { roleSkillsApi } from '@/services/api/role-skills';
import type { RoleTemplate } from '@/services/api/role-skills';

// Mock the role-skills API
vi.mock('@/services/api/role-skills', () => ({
  roleSkillsApi: {
    generateSkill: vi.fn(),
    createRoleSkill: vi.fn(),
    getTemplates: vi.fn(),
    getRoleSkills: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

const mockTemplate: RoleTemplate = {
  id: 'tmpl-1',
  roleType: 'developer',
  displayName: 'Developer',
  description: 'Code & architecture',
  icon: 'Code',
  sortOrder: 3,
  version: 1,
  defaultSkillContent: '# Developer\n\n## Focus Areas\n- Code quality\n- Architecture',
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const rootStore = new RootStore();
  // Pre-select developer role
  rootStore.roleSkill.toggleRole('developer');

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

describe('SkillGenerationWizard', () => {
  const defaultProps = {
    roleType: 'developer' as const,
    template: mockTemplate,
    workspaceId: 'ws-123',
    onBack: vi.fn(),
    onComplete: vi.fn(),
    currentIndex: 1,
    totalRoles: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('path selection', () => {
    it('should render three path options', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText(/Use Default Developer Skill/)).toBeInTheDocument();
      expect(screen.getByText('Describe Your Expertise')).toBeInTheDocument();
      expect(screen.getByText('Show Me Examples')).toBeInTheDocument();
    });

    it('should show "REC" badge on Describe Your Expertise option', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText('REC')).toBeInTheDocument();
    });

    it('should show header with role name', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText(/Skill Setup · Developer/)).toBeInTheDocument();
    });

    it('should show "(1 of 2)" when configuring multiple roles', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.toggleRole('tester');
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} currentIndex={1} totalRoles={2} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByText(/1 of 2/)).toBeInTheDocument();
    });
  });

  describe('use default path', () => {
    it('should show preview with default template content on Use Default click', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const useButton = screen.getByRole('radio', { name: /Use Default Developer Skill/ });
      await user.click(useButton);

      expect(screen.getByText('Your Skill')).toBeInTheDocument();
      expect(screen.getByText(/Focus Areas/)).toBeInTheDocument();
    });

    it('should show "Save & Activate" button in preview', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const useButton = screen.getByRole('radio', { name: /Use Default Developer Skill/ });
      await user.click(useButton);

      expect(screen.getByRole('button', { name: /Save & Activate/ })).toBeInTheDocument();
    });

    it('should call onComplete after saving default skill', async () => {
      const user = userEvent.setup();
      vi.mocked(roleSkillsApi.createRoleSkill).mockResolvedValue({
        id: 'skill-1',
        roleType: 'developer',
        roleName: 'Developer',
        skillContent: mockTemplate.defaultSkillContent,
        experienceDescription: null,
        isPrimary: true,
        templateVersion: 1,
        templateUpdateAvailable: false,
        wordCount: 10,
        createdAt: '2026-02-06T00:00:00Z',
        updatedAt: '2026-02-06T00:00:00Z',
      });

      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const useButton = screen.getByRole('radio', { name: /Use Default Developer Skill/ });
      await user.click(useButton);

      const saveButton = screen.getByRole('button', { name: /Save & Activate/ });
      await user.click(saveButton);

      await waitFor(() => {
        expect(defaultProps.onComplete).toHaveBeenCalledOnce();
      });
    });
  });

  describe('describe expertise path', () => {
    it('should show textarea when Describe Expertise is selected', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const describeButton = screen.getByRole('radio', { name: /Describe Your Expertise/ });
      await user.click(describeButton);

      expect(screen.getByRole('textbox', { name: /expertise/i })).toBeInTheDocument();
    });

    it('should disable Generate button when description is too short', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const describeButton = screen.getByRole('radio', { name: /Describe Your Expertise/ });
      await user.click(describeButton);

      const textarea = screen.getByRole('textbox', { name: /expertise/i });
      await user.type(textarea, 'short');

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      expect(genButton).toBeDisabled();
    });

    it('should enable Generate button when description meets minimum', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const describeButton = screen.getByRole('radio', { name: /Describe Your Expertise/ });
      await user.click(describeButton);

      const textarea = screen.getByRole('textbox', { name: /expertise/i });
      await user.type(textarea, 'I am a full-stack engineer with expertise in TypeScript');

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      expect(genButton).toBeEnabled();
    });

    it('should show generating state during AI generation', async () => {
      const user = userEvent.setup();
      vi.mocked(roleSkillsApi.generateSkill).mockReturnValue(new Promise(() => {}));

      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('describe');
      rootStore.roleSkill.setExperienceDescription(
        'I am a full-stack engineer with expertise in TypeScript'
      );
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      await user.click(genButton);

      const generatingTexts = await screen.findAllByText(/Generating your Developer skill/);
      expect(generatingTexts.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('should show preview after successful generation', async () => {
      const user = userEvent.setup();
      vi.mocked(roleSkillsApi.generateSkill).mockResolvedValue({
        skillContent: '# Senior Developer\n\n## Focus\n- TypeScript',
        suggestedRoleName: 'Senior TypeScript Developer',
        wordCount: 50,
        generationModel: 'claude-sonnet',
        generationTimeMs: 2500,
      });

      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('describe');
      rootStore.roleSkill.setExperienceDescription(
        'I am a full-stack engineer with expertise in TypeScript'
      );
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      await user.click(genButton);

      await waitFor(() => {
        expect(screen.getByText('Your Skill')).toBeInTheDocument();
      });
      expect(screen.getByText('Generated by AI')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Senior TypeScript Developer')).toBeInTheDocument();
    });

    it('should show error fallback when generation fails', async () => {
      const user = userEvent.setup();
      vi.mocked(roleSkillsApi.generateSkill).mockRejectedValue(new Error('API error'));

      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('describe');
      rootStore.roleSkill.setExperienceDescription(
        'I am a full-stack engineer with expertise in TypeScript'
      );
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      await user.click(genButton);

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
      expect(screen.getByText(/Skill generation unavailable/)).toBeInTheDocument();
    });
  });

  describe('preview actions', () => {
    it('should allow editing the role name', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      // Use default to get to preview quickly
      const useButton = screen.getByRole('radio', { name: /Use Default Developer Skill/ });
      await user.click(useButton);

      const nameInput = screen.getByLabelText(/Role name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'My Custom Dev Name');

      expect(nameInput).toHaveValue('My Custom Dev Name');
    });

    it('should show word count', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const useButton = screen.getByRole('radio', { name: /Use Default Developer Skill/ });
      await user.click(useButton);

      expect(screen.getByText(/\/ 2000 words/)).toBeInTheDocument();
    });
  });

  describe('examples view', () => {
    it('should render examples when Show Examples is clicked', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const examplesButton = screen.getByRole('radio', { name: /Show Me Examples/ });
      await user.click(examplesButton);

      expect(screen.getByText(/How a Developer Skill Changes AI Behavior/)).toBeInTheDocument();
      const withoutSkillTexts = screen.getAllByText(/Without skill/);
      expect(withoutSkillTexts.length).toBeGreaterThanOrEqual(1);
      const withSkillTexts = screen.getAllByText(/With Developer skill/);
      expect(withSkillTexts.length).toBeGreaterThanOrEqual(1);
    });

    it('should have "Back to Options" button in examples view', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const examplesButton = screen.getByRole('radio', { name: /Show Me Examples/ });
      await user.click(examplesButton);

      expect(screen.getByRole('button', { name: /Back to Options/i })).toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('should call onBack when Back button is clicked from path selection', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('path');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      await user.click(screen.getByLabelText('Back'));

      expect(defaultProps.onBack).toHaveBeenCalledOnce();
    });
  });
});
