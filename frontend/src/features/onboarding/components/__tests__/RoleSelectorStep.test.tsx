/**
 * Component tests for RoleSelectorStep.
 *
 * Migrated from RoleSkillStore to props-based state management.
 * Source: FR-001, FR-002, FR-018, US1
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RoleSelectorStep } from '../RoleSelectorStep';
import type { SkillTemplate } from '@/services/api/skill-templates';
import type { SDLCRoleType } from '../../constants/skill-wizard-constants';

const mockTemplates: SkillTemplate[] = [
  {
    id: '1',
    workspace_id: 'ws-1',
    name: 'Business Analyst',
    description: 'Requirements & analysis',
    skill_content: '# Business Analyst',
    icon: 'FileSearch',
    sort_order: 1,
    source: 'built_in',
    role_type: 'business_analyst',
    is_active: true,
    created_by: null,
    created_at: '2026-02-06T00:00:00Z',
    updated_at: '2026-02-06T00:00:00Z',
  },
  {
    id: '2',
    workspace_id: 'ws-1',
    name: 'Developer',
    description: 'Code & architecture',
    skill_content: '# Developer',
    icon: 'Code',
    sort_order: 3,
    source: 'built_in',
    role_type: 'developer',
    is_active: true,
    created_by: null,
    created_at: '2026-02-06T00:00:00Z',
    updated_at: '2026-02-06T00:00:00Z',
  },
  {
    id: '3',
    workspace_id: 'ws-1',
    name: 'Tester',
    description: 'Quality & test plans',
    skill_content: '# Tester',
    icon: 'TestTube',
    sort_order: 4,
    source: 'built_in',
    role_type: 'tester',
    is_active: true,
    created_by: null,
    created_at: '2026-02-06T00:00:00Z',
    updated_at: '2026-02-06T00:00:00Z',
  },
];

describe('RoleSelectorStep', () => {
  let selectedRoles: SDLCRoleType[];
  let onToggleRole: ReturnType<typeof vi.fn>;

  const defaultProps = {
    onContinue: vi.fn(),
    onSkip: vi.fn(),
    onBack: vi.fn(),
    onCustomRole: vi.fn(),
    templates: mockTemplates,
    isLoadingTemplates: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    selectedRoles = [];
    onToggleRole = vi.fn((roleType: SDLCRoleType) => {
      const idx = selectedRoles.indexOf(roleType);
      if (idx >= 0) {
        selectedRoles = selectedRoles.filter(r => r !== roleType);
      } else {
        selectedRoles = [...selectedRoles, roleType];
      }
    });
  });

  describe('rendering', () => {
    it('should render the title and description', () => {
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={selectedRoles}
          onToggleRole={onToggleRole}
        />
      );

      expect(screen.getByText('Set Up Your Skill')).toBeInTheDocument();
    });

    it('should render role cards from templates', () => {
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={selectedRoles}
          onToggleRole={onToggleRole}
        />
      );

      expect(screen.getByText('Business Analyst')).toBeInTheDocument();
      expect(screen.getByText('Developer')).toBeInTheDocument();
      expect(screen.getByText('Tester')).toBeInTheDocument();
    });

    it('should render the Custom Skill card', () => {
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={selectedRoles}
          onToggleRole={onToggleRole}
        />
      );

      expect(screen.getByText('Custom Skill')).toBeInTheDocument();
    });

    it('should show loading state while templates are loading', () => {
      render(
        <RoleSelectorStep
          {...defaultProps}
          isLoadingTemplates={true}
          selectedRoles={selectedRoles}
          onToggleRole={onToggleRole}
        />
      );

      expect(screen.getByText('Loading skills...')).toBeInTheDocument();
    });
  });

  describe('selection behavior', () => {
    it('should call onToggleRole when a role card is clicked', async () => {
      const user = userEvent.setup();
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={selectedRoles}
          onToggleRole={onToggleRole}
        />
      );

      const devCard = screen.getByTestId('role-card-developer');
      await user.click(devCard);

      expect(onToggleRole).toHaveBeenCalledWith('developer');
    });

    it('should call onCustomRole when Custom Skill card is clicked', async () => {
      const user = userEvent.setup();
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={selectedRoles}
          onToggleRole={onToggleRole}
        />
      );

      const customCard = screen.getByTestId('role-card-custom');
      await user.click(customCard);

      expect(defaultProps.onCustomRole).toHaveBeenCalledOnce();
    });
  });

  describe('continue button', () => {
    it('should be disabled when no roles selected', () => {
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={[]}
          onToggleRole={onToggleRole}
        />
      );

      const button = screen.getByRole('button', { name: /Continue/i });
      expect(button).toBeDisabled();
    });

    it('should be enabled when at least one role is selected', () => {
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={['developer']}
          onToggleRole={onToggleRole}
        />
      );

      const button = screen.getByRole('button', { name: /Continue/i });
      expect(button).toBeEnabled();
    });

    it('should call onContinue when clicked', async () => {
      const user = userEvent.setup();
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={['developer']}
          onToggleRole={onToggleRole}
        />
      );

      const button = screen.getByRole('button', { name: /Continue/i });
      await user.click(button);

      expect(defaultProps.onContinue).toHaveBeenCalledOnce();
    });

    it('should show count when multiple roles selected', () => {
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={['developer', 'tester']}
          onToggleRole={onToggleRole}
        />
      );

      expect(screen.getByRole('button', { name: /Set Up 2 Skills/i })).toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('should call onBack when Back button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={selectedRoles}
          onToggleRole={onToggleRole}
        />
      );

      await user.click(screen.getByText('Back'));

      expect(defaultProps.onBack).toHaveBeenCalledOnce();
    });

    it('should call onSkip when Skip button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <RoleSelectorStep
          {...defaultProps}
          selectedRoles={selectedRoles}
          onToggleRole={onToggleRole}
        />
      );

      await user.click(screen.getByText('Skip'));

      expect(defaultProps.onSkip).toHaveBeenCalledOnce();
    });
  });

  describe('existing skills', () => {
    it('should show "Already set up" for roles with existing skills', () => {
      render(
        <RoleSelectorStep
          {...defaultProps}
          existingSkillRoleTypes={['developer']}
          selectedRoles={selectedRoles}
          onToggleRole={onToggleRole}
        />
      );

      expect(screen.getByText('Already set up')).toBeInTheDocument();
    });
  });
});
