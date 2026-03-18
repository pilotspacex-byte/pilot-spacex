/**
 * Tests for SkillAddModal component.
 *
 * Dual-mode Add Skill modal with Manual + AI Generate tabs.
 * Covers: manual save, AI flow, tab switching, validation, template pre-seed.
 */

import * as React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SkillAddModal } from '../skill-add-modal';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockCreateUserSkill = {
  mutateAsync: vi.fn().mockResolvedValue({ id: 'new-skill-id' }),
  isPending: false,
};

const mockGenerateSkill = {
  mutateAsync: vi.fn().mockResolvedValue({
    skillContent: '# Generated Skill\n\nContent here',
    suggestedRoleName: 'AI Generated Name',
    wordCount: 5,
  }),
  isPending: false,
};

const mockCreateRoleSkill = {
  mutateAsync: vi.fn().mockResolvedValue({}),
  isPending: false,
};

const mockGenerateWorkspaceSkill = {
  mutateAsync: vi.fn().mockResolvedValue({
    skill_content: '# Workspace Skill',
    role_name: 'Workspace Role',
  }),
  isPending: false,
};

vi.mock('@/services/api/user-skills', () => ({
  useCreateUserSkill: () => mockCreateUserSkill,
}));

vi.mock('@/features/onboarding/hooks', () => ({
  useGenerateSkill: () => mockGenerateSkill,
  useCreateRoleSkill: () => mockCreateRoleSkill,
}));

vi.mock('@/services/api/workspace-role-skills', () => ({
  useGenerateWorkspaceSkill: () => mockGenerateWorkspaceSkill,
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-ws' }),
  useRouter: () => ({ push: vi.fn() }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderModal(props: Partial<React.ComponentProps<typeof SkillAddModal>> = {}) {
  const queryClient = createQueryClient();
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    workspaceId: 'ws-123',
    workspaceSlug: 'test-ws',
    ...props,
  };

  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <SkillAddModal {...defaultProps} />
      </QueryClientProvider>
    ),
    props: defaultProps,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SkillAddModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('1. Manual tab renders', () => {
    it('should render name input, description input, content textarea, save button, and inline tip', () => {
      renderModal();

      // Manual tab should be default
      expect(screen.getByText('Manual')).toBeInTheDocument();
      expect(screen.getByText('AI Generate')).toBeInTheDocument();

      // Fields
      expect(screen.getByPlaceholderText('e.g. Senior Backend Developer')).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText('Brief description of what this skill covers')
      ).toBeInTheDocument();

      // Save button
      expect(screen.getByRole('button', { name: /save skill/i })).toBeInTheDocument();

      // Inline tip
      expect(screen.getByText(/include your role, tech stack/i)).toBeInTheDocument();
    });
  });

  describe('2. Manual save', () => {
    it('should call createUserSkill.mutateAsync with correct payload on save', async () => {
      const user = userEvent.setup();
      renderModal();

      // Fill name
      const nameInput = screen.getByPlaceholderText('e.g. Senior Backend Developer');
      await user.type(nameInput, 'My Custom Skill');

      // Fill content
      const textarea = screen.getByLabelText('Skill content editor');
      await user.type(textarea, 'Some skill content here');

      // Fill description (optional)
      const descInput = screen.getByPlaceholderText('Brief description of what this skill covers');
      await user.type(descInput, 'A brief description');

      // Click save
      const saveBtn = screen.getByRole('button', { name: /save skill/i });
      await user.click(saveBtn);

      expect(mockCreateUserSkill.mutateAsync).toHaveBeenCalledWith({
        skill_name: 'My Custom Skill',
        skill_content: 'Some skill content here',
        experience_description: 'A brief description',
      });
    });
  });

  describe('3. Manual validation', () => {
    it('should disable Save Skill button when name is empty', () => {
      renderModal();

      const saveBtn = screen.getByRole('button', { name: /save skill/i });
      expect(saveBtn).toBeDisabled();
    });

    it('should disable Save Skill button when content is empty', async () => {
      const user = userEvent.setup();
      renderModal();

      // Fill name but not content
      const nameInput = screen.getByPlaceholderText('e.g. Senior Backend Developer');
      await user.type(nameInput, 'Some Skill');

      const saveBtn = screen.getByRole('button', { name: /save skill/i });
      expect(saveBtn).toBeDisabled();
    });

    it('should show inline error on blur when name is empty', async () => {
      const user = userEvent.setup();
      renderModal();

      const nameInput = screen.getByPlaceholderText('e.g. Senior Backend Developer');
      await user.click(nameInput);
      await user.tab(); // blur

      expect(screen.getByText('Skill name is required')).toBeInTheDocument();
    });
  });

  describe('4. AI tab renders', () => {
    it('should render description textarea and generate button in AI tab', async () => {
      const user = userEvent.setup();
      renderModal();

      // Switch to AI tab
      const aiTab = screen.getByRole('tab', { name: /ai generate/i });
      await user.click(aiTab);

      // Description textarea
      expect(screen.getByLabelText('Experience Description')).toBeInTheDocument();

      // Generate button
      expect(screen.getByRole('button', { name: /generate/i })).toBeInTheDocument();
    });
  });

  describe('5. Tab switching preserves state', () => {
    it('should preserve manual tab state when switching to AI and back', async () => {
      const user = userEvent.setup();
      renderModal();

      // Fill manual fields
      const nameInput = screen.getByPlaceholderText('e.g. Senior Backend Developer');
      await user.type(nameInput, 'Preserved Name');

      const textarea = screen.getByLabelText('Skill content editor');
      await user.type(textarea, 'Preserved content');

      // Switch to AI tab
      const aiTab = screen.getByRole('tab', { name: /ai generate/i });
      await user.click(aiTab);

      // Switch back to Manual tab
      const manualTab = screen.getByRole('tab', { name: /manual/i });
      await user.click(manualTab);

      // Verify state preserved
      expect(screen.getByPlaceholderText('e.g. Senior Backend Developer')).toHaveValue(
        'Preserved Name'
      );
      expect(screen.getByLabelText('Skill content editor')).toHaveValue('Preserved content');
    });
  });

  describe('6. Template pre-seed', () => {
    it('should open AI tab with description pre-filled when template is provided', () => {
      renderModal({
        template: {
          id: 'tmpl-1',
          name: 'Backend Dev',
          description: 'Python backend developer with FastAPI experience',
          skill_content: '# Backend Dev Content',
        },
      });

      // AI Generate tab should be active
      const aiTab = screen.getByRole('tab', { name: /ai generate/i });
      expect(aiTab).toHaveAttribute('data-state', 'active');

      // Description should be pre-filled
      const desc = screen.getByLabelText('Experience Description');
      expect(desc).toHaveValue('Python backend developer with FastAPI experience');
    });
  });

  describe('7. AI generation flow', () => {
    it('should transition from form to generating to preview on successful generation', async () => {
      // Use a deferred promise so we can observe the generating state
      let resolveGenerate!: (value: unknown) => void;
      mockGenerateSkill.mutateAsync.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveGenerate = resolve;
          })
      );

      const user = userEvent.setup();
      renderModal({ defaultTab: 'ai-generate' });

      // Fill description with enough chars
      const desc = screen.getByLabelText('Experience Description');
      await user.type(desc, 'Senior Python developer with 8 years of experience in FastAPI');

      // Click generate
      const generateBtn = screen.getByRole('button', { name: /generate/i });
      await user.click(generateBtn);

      // Should show generating state (bouncing dots / progress)
      expect(screen.getByText('Generating your skill...')).toBeInTheDocument();

      // Resolve the deferred promise to transition to preview
      await React.act(async () => {
        resolveGenerate({
          skillContent: '# Generated Skill\n\nContent here',
          suggestedRoleName: 'AI Generated Name',
          wordCount: 5,
        });
      });

      // Wait for preview step
      await waitFor(() => {
        expect(screen.getByText(/skill preview/i)).toBeInTheDocument();
      });
    });
  });

  describe('8. Tab disabled during generation', () => {
    it('should disable Manual tab trigger when AI step is generating', async () => {
      // Make generation hang
      mockGenerateSkill.mutateAsync.mockImplementation(
        () => new Promise(() => {}) // never resolves
      );

      const user = userEvent.setup();
      renderModal({ defaultTab: 'ai-generate' });

      // Fill description
      const desc = screen.getByLabelText('Experience Description');
      await user.type(desc, 'Senior Python developer with 8 years of experience in FastAPI');

      // Click generate
      const generateBtn = screen.getByRole('button', { name: /generate/i });
      await user.click(generateBtn);

      // Manual tab should be disabled
      const manualTab = screen.getByRole('tab', { name: /manual/i });
      expect(manualTab).toBeDisabled();
    });
  });

  describe('9. Modal close resets state', () => {
    it('should call onOpenChange(false) and reset fields after reopen', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      const { rerender } = renderModal({ onOpenChange });

      // Fill manual name
      const nameInput = screen.getByPlaceholderText('e.g. Senior Backend Developer');
      await user.type(nameInput, 'Will be cleared');

      // Click cancel to close
      const cancelBtn = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelBtn);

      expect(onOpenChange).toHaveBeenCalledWith(false);

      // Simulate close + reopen after reset timeout
      const queryClient = createQueryClient();
      await vi.waitFor(() => {
        rerender(
          <QueryClientProvider client={queryClient}>
            <SkillAddModal
              open={false}
              onOpenChange={onOpenChange}
              workspaceId="ws-123"
              workspaceSlug="test-ws"
            />
          </QueryClientProvider>
        );
      });

      // Wait for reset timeout (200ms)
      await new Promise((r) => setTimeout(r, 250));

      rerender(
        <QueryClientProvider client={queryClient}>
          <SkillAddModal
            open={true}
            onOpenChange={onOpenChange}
            workspaceId="ws-123"
            workspaceSlug="test-ws"
          />
        </QueryClientProvider>
      );

      // Name should be cleared after reopen
      const reopenedInput = screen.getByPlaceholderText('e.g. Senior Backend Developer');
      expect(reopenedInput).toHaveValue('');
    });
  });

  describe('10. Keyboard navigation', () => {
    it('should close modal on Escape', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();
      renderModal({ onOpenChange });

      await user.keyboard('{Escape}');

      expect(onOpenChange).toHaveBeenCalled();
    });
  });
});
