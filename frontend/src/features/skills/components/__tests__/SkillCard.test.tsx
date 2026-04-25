/**
 * SkillCard tests — Phase 91 Plan 03 Task 2.
 *
 * Validates that SkillCard renders the expected anatomy via Phase 85
 * <ArtifactCard type="SKILL" density="full"> and that footer/empty/onClick
 * branches behave per UI-SPEC §Surface 1.
 *
 * Time-sensitive assertions use vi.useFakeTimers + vi.setSystemTime to make
 * formatDistanceToNow output deterministic across runs (advisor flag #3).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Skill } from '@/types/skill';
import { SkillCard } from '../SkillCard';

const NOW = new Date('2026-04-25T12:00:00Z');

function buildSkill(overrides: Partial<Skill> = {}): Skill {
  return {
    name: 'AI Context',
    slug: 'ai-context',
    description: 'Generate AI context for a chat session.',
    category: 'AI',
    icon: 'Sparkles',
    examples: [],
    feature_module: ['chat'],
    reference_files: ['architecture.md', 'examples.md', 'usage.md'],
    updated_at: new Date(NOW.getTime() - 2 * 86400 * 1000).toISOString(),
    ...overrides,
  };
}

describe('SkillCard (Phase 91)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders skill name as the card title', () => {
    render(<SkillCard skill={buildSkill()} />);
    expect(screen.getByText('AI Context')).toBeInTheDocument();
  });

  it('renders the SKILL type badge', () => {
    render(<SkillCard skill={buildSkill()} />);
    expect(screen.getByText('SKILL')).toBeInTheDocument();
  });

  it('renders refs count + relative time in the footer', () => {
    render(<SkillCard skill={buildSkill()} />);
    const footer = screen.getByTestId('skill-card-footer');
    expect(footer).toHaveTextContent(/3 refs/);
    expect(footer).toHaveTextContent(/2 days ago/i);
  });

  it('singularizes "1 ref" vs "0 refs" / "3 refs"', () => {
    const { rerender } = render(
      <SkillCard skill={buildSkill({ reference_files: ['only.md'] })} />,
    );
    expect(screen.getByText(/1 ref$/)).toBeInTheDocument();

    rerender(<SkillCard skill={buildSkill({ reference_files: [] })} />);
    expect(screen.getByText(/0 refs/)).toBeInTheDocument();
  });

  it('renders the feature_module chip when present', () => {
    render(<SkillCard skill={buildSkill({ feature_module: ['issues'] })} />);
    expect(screen.getByText('issues')).toBeInTheDocument();
  });

  it('does not render any feature chip when feature_module is null', () => {
    render(<SkillCard skill={buildSkill({ feature_module: null })} />);
    // The chip element holds the feature_module text; absence implies no chip.
    // The skill description still renders, so we assert via test-id absence.
    expect(screen.queryByTestId('skill-card-feature-chip')).toBeNull();
  });

  it('does not render description when description is empty', () => {
    render(<SkillCard skill={buildSkill({ description: '' })} />);
    expect(screen.queryByTestId('skill-card-description')).toBeNull();
  });

  it('renders description when non-empty', () => {
    render(<SkillCard skill={buildSkill({ description: 'Helpful prose.' })} />);
    expect(screen.getByText('Helpful prose.')).toBeInTheDocument();
  });

  it('falls back to em-dash when updated_at is null', () => {
    render(<SkillCard skill={buildSkill({ updated_at: null })} />);
    expect(screen.getByText(/—/)).toBeInTheDocument();
  });

  it('calls onClick when the card is clicked', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const onClick = vi.fn();
    render(<SkillCard skill={buildSkill()} onClick={onClick} />);
    await user.click(screen.getByRole('article'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
