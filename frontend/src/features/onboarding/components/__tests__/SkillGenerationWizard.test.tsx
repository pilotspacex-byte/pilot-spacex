/**
 * Component tests for SkillGenerationWizard.
 *
 * Tests for the single-form skill generation wizard with two-panel layout.
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

  describe('form view', () => {
    it('should render the form with textarea and examples panel', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText('Generate Your AI Skill')).toBeInTheDocument();
      expect(screen.getByText('Describe Your Expertise')).toBeInTheDocument();
      expect(screen.getByText(/How a Developer Skill Changes AI Behavior/)).toBeInTheDocument();
    });

    it('should pre-fill textarea with role sample description', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const textarea = screen.getByRole('textbox', { name: /expertise/i }) as HTMLTextAreaElement;
      expect(textarea.value).toContain('full-stack TypeScript developer');
    });

    it('should show header with role name', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText(/Skill Setup · Developer/)).toBeInTheDocument();
    });

    it('should show "(1 of 2)" when configuring multiple roles', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.toggleRole('tester');
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} currentIndex={1} totalRoles={2} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByText(/1 of 2/)).toBeInTheDocument();
    });

    it('should show "Use Default Template" link when template exists', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText('Use Default Template')).toBeInTheDocument();
    });

    it('should show before/after examples in right panel', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const withoutSkillTexts = screen.getAllByText(/Without skill/);
      expect(withoutSkillTexts.length).toBeGreaterThanOrEqual(1);
      const withSkillTexts = screen.getAllByText(/With Developer skill/);
      expect(withSkillTexts.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('use default template', () => {
    it('should show preview with default template content on Use Default click', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      await user.click(screen.getByText('Use Default Template'));

      expect(screen.getByText('Your Skill')).toBeInTheDocument();
      expect(screen.getByText(/Focus Areas/)).toBeInTheDocument();
    });

    it('should show "Save & Activate" button in preview', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      await user.click(screen.getByText('Use Default Template'));

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
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      await user.click(screen.getByText('Use Default Template'));

      const saveButton = screen.getByRole('button', { name: /Save & Activate/ });
      await user.click(saveButton);

      await waitFor(() => {
        expect(defaultProps.onComplete).toHaveBeenCalledOnce();
      });
    });
  });

  describe('generate skill', () => {
    it('should disable Generate button when description is too short', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      rootStore.roleSkill.setExperienceDescription('');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const textarea = screen.getByRole('textbox', { name: /expertise/i });
      await user.clear(textarea);
      await user.type(textarea, 'short');

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      expect(genButton).toBeDisabled();
    });

    it('should enable Generate button when description meets minimum', () => {
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      // Pre-fill from role sample (auto via useEffect)
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      expect(genButton).toBeEnabled();
    });

    it('should show generating state during AI generation', async () => {
      const user = userEvent.setup();
      vi.mocked(roleSkillsApi.generateSkill).mockReturnValue(new Promise(() => {}));

      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
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
      rootStore.roleSkill.setGenerationStep('form');
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
      rootStore.roleSkill.setGenerationStep('form');
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
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      // Use default to get to preview
      await user.click(screen.getByText('Use Default Template'));

      const nameInput = screen.getByLabelText(/Role name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'My Custom Dev Name');

      expect(nameInput).toHaveValue('My Custom Dev Name');
    });

    it('should show word count', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      await user.click(screen.getByText('Use Default Template'));

      expect(screen.getByText(/\/ 2000 words/)).toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('should call onBack when Back button is clicked from form', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      await user.click(screen.getByLabelText('Back'));

      expect(defaultProps.onBack).toHaveBeenCalledOnce();
    });

    it('should go back to form when Back is clicked from preview', async () => {
      const user = userEvent.setup();
      const { Wrapper, rootStore } = createWrapper();
      rootStore.roleSkill.setGenerationStep('form');
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      // Navigate to preview
      await user.click(screen.getByText('Use Default Template'));
      expect(screen.getByText('Your Skill')).toBeInTheDocument();

      // Go back
      await user.click(screen.getByLabelText('Back'));

      expect(screen.getByText('Generate Your AI Skill')).toBeInTheDocument();
    });
  });
});
