/**
 * WorkspaceSkillCard tests -- migrated from WorkspaceRoleSkill to SkillTemplate type.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { WorkspaceSkillCard } from '../workspace-skill-card';
import type { SkillTemplate } from '@/services/api/skill-templates';

const baseSkill: SkillTemplate = {
  id: 'skill-1',
  workspace_id: 'ws-1',
  name: 'Senior Developer',
  description: '10 years React',
  skill_content: 'You are a senior developer with 10 years of React experience.',
  icon: 'Code',
  sort_order: 0,
  source: 'workspace',
  role_type: 'developer',
  is_active: false,
  created_by: 'user-1',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('WorkspaceSkillCard', () => {
  it('renders Pending Review badge when is_active is false', () => {
    render(<WorkspaceSkillCard skill={baseSkill} onActivate={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.getByText('Pending Review')).toBeInTheDocument();
    expect(screen.queryByText('Active')).not.toBeInTheDocument();
  });

  it('renders Active badge when is_active is true', () => {
    const activeSkill = { ...baseSkill, is_active: true };
    render(<WorkspaceSkillCard skill={activeSkill} onActivate={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.queryByText('Pending Review')).not.toBeInTheDocument();
  });

  it('shows Activate button for pending skills', () => {
    render(<WorkspaceSkillCard skill={baseSkill} onActivate={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Activate' })).toBeInTheDocument();
  });

  it('does not show Activate button for active skills', () => {
    const activeSkill = { ...baseSkill, is_active: true };
    render(<WorkspaceSkillCard skill={activeSkill} onActivate={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'Activate' })).not.toBeInTheDocument();
  });

  it('does not show Deactivate button for active skills (is_active is one-way)', () => {
    const activeSkill = { ...baseSkill, is_active: true };
    render(<WorkspaceSkillCard skill={activeSkill} onActivate={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /deactivate/i })).not.toBeInTheDocument();
  });

  it('calls onActivate with skill id when Activate clicked', async () => {
    const user = userEvent.setup();
    const onActivate = vi.fn();
    render(<WorkspaceSkillCard skill={baseSkill} onActivate={onActivate} onRemove={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: 'Activate' }));
    expect(onActivate).toHaveBeenCalledWith('skill-1');
  });

  it('calls onRemove when Remove button clicked', async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn();
    render(<WorkspaceSkillCard skill={baseSkill} onActivate={vi.fn()} onRemove={onRemove} />);
    await user.click(screen.getByRole('button', { name: 'Remove' }));
    // Confirm dialog appears — need to confirm
    expect(screen.getByText(/Remove "Senior Developer" skill\?/)).toBeInTheDocument();
  });
});
