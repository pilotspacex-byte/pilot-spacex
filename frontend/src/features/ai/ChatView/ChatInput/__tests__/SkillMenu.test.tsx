/**
 * Unit tests for SkillMenu component.
 *
 * Tests dynamic skill rendering, fallback behavior,
 * and session skill presence.
 *
 * @module features/ai/ChatView/ChatInput/__tests__/SkillMenu.test
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import { SkillMenu } from '../SkillMenu';
import { SKILLS, SESSION_SKILLS, FALLBACK_SKILLS } from '../../constants';
import type { SkillDefinition } from '../../types';

// cmdk uses scrollIntoView which is not available in JSDOM
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

const noop = vi.fn();

function renderSkillMenu(props: { skills?: SkillDefinition[] } = {}) {
  return render(
    <SkillMenu open={true} onOpenChange={noop} onSelect={noop} skills={props.skills}>
      <button>trigger</button>
    </SkillMenu>
  );
}

describe('SkillMenu', () => {
  it('renders hardcoded SKILLS when no skills prop provided', () => {
    renderSkillMenu();

    // Should show all default skills (session + fallback)
    for (const skill of SKILLS) {
      expect(screen.getByText(`/${skill.name}`)).toBeInTheDocument();
    }
  });

  it('renders dynamic skills when skills prop is provided', () => {
    const dynamicSkills: SkillDefinition[] = [
      {
        name: 'custom-skill',
        description: 'A custom skill from API',
        category: 'notes',
        icon: 'FileText',
        examples: ['Do custom thing'],
      },
    ];

    renderSkillMenu({ skills: dynamicSkills });

    expect(screen.getByText('/custom-skill')).toBeInTheDocument();
    expect(screen.getByText('A custom skill from API')).toBeInTheDocument();
  });

  it('does not show hardcoded skills when dynamic skills provided', () => {
    const dynamicSkills: SkillDefinition[] = [
      {
        name: 'only-this',
        description: 'Only skill',
        category: 'notes',
        icon: 'FileText',
        examples: [],
      },
    ];

    renderSkillMenu({ skills: dynamicSkills });

    // Hardcoded-only skills like extract-issues should NOT appear
    expect(screen.queryByText('/extract-issues')).not.toBeInTheDocument();
    expect(screen.getByText('/only-this')).toBeInTheDocument();
  });

  it('session skills are present in combined SKILLS constant', () => {
    // SESSION_SKILLS should include resume and new
    const sessionNames = SESSION_SKILLS.map((s) => s.name);
    expect(sessionNames).toContain('resume');
    expect(sessionNames).toContain('new');
  });

  it('FALLBACK_SKILLS does not include session skills', () => {
    const fallbackNames = FALLBACK_SKILLS.map((s) => s.name);
    expect(fallbackNames).not.toContain('resume');
    expect(fallbackNames).not.toContain('new');
  });

  it('groups skills by category', () => {
    renderSkillMenu();

    // Should show category headings
    expect(screen.getByText('Session')).toBeInTheDocument();
    expect(screen.getByText('Issues')).toBeInTheDocument();
    expect(screen.getByText('Writing')).toBeInTheDocument();
  });

  it('shows description for each skill', () => {
    const skills: SkillDefinition[] = [
      {
        name: 'test-skill',
        description: 'Test description text',
        category: 'writing',
        icon: 'PenTool',
        examples: ['Example prompt'],
      },
    ];

    renderSkillMenu({ skills });

    expect(screen.getByText('Test description text')).toBeInTheDocument();
  });

  it('compact layout: skill name and description on single line', () => {
    const skills: SkillDefinition[] = [
      {
        name: 'compact-skill',
        description: 'Short desc',
        category: 'notes',
        icon: 'FileText',
        examples: ['Try this example'],
      },
    ];

    renderSkillMenu({ skills });

    // Name and description rendered, examples omitted in compact layout
    expect(screen.getByText('/compact-skill')).toBeInTheDocument();
    expect(screen.getByText('Short desc')).toBeInTheDocument();
    expect(screen.queryByText(/Try this example/)).not.toBeInTheDocument();
  });
});
