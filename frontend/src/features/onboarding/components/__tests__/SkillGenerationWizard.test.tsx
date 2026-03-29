/**
 * Component tests for SkillGenerationWizard.
 *
 * Migrated from RoleSkillStore/roleSkillsApi to local state/skill-templates API.
 * Source: FR-001, FR-002, FR-003, FR-004, US1, US2
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SkillGenerationWizard } from '../SkillGenerationWizard';
import { skillTemplatesApi } from '@/services/api/skill-templates';
import type { SkillTemplate } from '@/services/api/skill-templates';

// Mock the skill-templates API
vi.mock('@/services/api/skill-templates', () => ({
  skillTemplatesApi: {
    getTemplates: vi.fn(),
    createTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
  },
  useSkillTemplates: vi.fn(() => ({ data: [], isLoading: false })),
  useCreateSkillTemplate: vi.fn(),
  useUpdateSkillTemplate: vi.fn(),
  useDeleteSkillTemplate: vi.fn(),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

const mockTemplate: SkillTemplate = {
  id: 'tmpl-1',
  workspace_id: 'ws-1',
  name: 'Developer',
  description: 'Code & architecture',
  skill_content: '# Developer\n\n## Focus Areas\n- Code quality\n- Architecture',
  icon: 'Code',
  sort_order: 3,
  source: 'built_in',
  role_type: 'developer',
  is_active: true,
  created_by: null,
  created_at: '2026-02-06T00:00:00Z',
  updated_at: '2026-02-06T00:00:00Z',
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return {
    Wrapper({ children }: { children: React.ReactNode }) {
      return React.createElement(
        QueryClientProvider,
        { client: queryClient },
        children
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
      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText('Generate Your AI Skill')).toBeInTheDocument();
      expect(screen.getByText('Describe Your Expertise')).toBeInTheDocument();
      expect(screen.getByText(/How a Developer Skill Changes AI Behavior/)).toBeInTheDocument();
    });

    it('should pre-fill textarea with role sample description', () => {
      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const textarea = screen.getByRole('textbox', { name: /expertise/i }) as HTMLTextAreaElement;
      expect(textarea.value).toContain('full-stack TypeScript developer');
    });

    it('should show header with role name', () => {
      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText(/Skill Setup · Developer/)).toBeInTheDocument();
    });

    it('should show "(1 of 2)" when configuring multiple roles', () => {
      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} currentIndex={1} totalRoles={2} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByText(/1 of 2/)).toBeInTheDocument();
    });

    it('should show "Use Default Template" link when template exists', () => {
      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText('Use Default Template')).toBeInTheDocument();
    });
  });

  describe('use default template', () => {
    it('should show preview with default template content on Use Default click', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      await user.click(screen.getByText('Use Default Template'));

      expect(screen.getByText('Your Skill')).toBeInTheDocument();
      expect(screen.getByText(/Focus Areas/)).toBeInTheDocument();
    });

    it('should show "Save & Activate" button in preview', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      await user.click(screen.getByText('Use Default Template'));

      expect(screen.getByRole('button', { name: /Save & Activate/ })).toBeInTheDocument();
    });

    it('should call onComplete after saving default skill', async () => {
      const user = userEvent.setup();
      vi.mocked(skillTemplatesApi.createTemplate).mockResolvedValue(mockTemplate);

      const { Wrapper } = createWrapper();
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
      const { Wrapper } = createWrapper();
      // Use a role type that has no sample description
      render(<SkillGenerationWizard {...defaultProps} roleType="custom" template={undefined} />, { wrapper: Wrapper });

      const textarea = screen.getByRole('textbox', { name: /expertise/i });
      await user.type(textarea, 'short');

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      expect(genButton).toBeDisabled();
    });

    it('should enable Generate button when description meets minimum', () => {
      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      expect(genButton).toBeEnabled();
    });

    it('should show generating state during AI generation', async () => {
      const user = userEvent.setup();
      vi.mocked(skillTemplatesApi.createTemplate).mockReturnValue(new Promise(() => {}));

      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      await user.click(genButton);

      const generatingTexts = await screen.findAllByText(/Generating your Developer skill/);
      expect(generatingTexts.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('should show preview after successful generation', async () => {
      const user = userEvent.setup();
      vi.mocked(skillTemplatesApi.createTemplate).mockResolvedValue({
        ...mockTemplate,
        name: 'Senior TypeScript Developer',
        skill_content: '# Senior Developer\n\n## Focus\n- TypeScript',
      });

      const { Wrapper } = createWrapper();
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
      vi.mocked(skillTemplatesApi.createTemplate).mockRejectedValue(new Error('API error'));

      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      const genButton = screen.getByRole('button', { name: /Generate Skill/i });
      await user.click(genButton);

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
      expect(screen.getByText(/Skill generation unavailable/)).toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('should call onBack when Back button is clicked from form', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
      render(<SkillGenerationWizard {...defaultProps} />, { wrapper: Wrapper });

      await user.click(screen.getByLabelText('Back'));

      expect(defaultProps.onBack).toHaveBeenCalledOnce();
    });

    it('should go back to form when Back is clicked from preview', async () => {
      const user = userEvent.setup();
      const { Wrapper } = createWrapper();
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
