/**
 * Unit tests for SkillCreatorCard component.
 * Phase 64-03
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SkillCreatorCard } from '../SkillCreatorCard';

// Mock CodeMirror 6 packages — editor is not renderable in jsdom
vi.mock('@codemirror/view', () => ({
  EditorView: Object.assign(
    vi.fn().mockImplementation(() => ({
      destroy: vi.fn(),
      state: { doc: { toString: () => '' } },
    })),
    {
      updateListener: { of: vi.fn(() => []) },
      theme: vi.fn(() => []),
    }
  ),
  keymap: { of: vi.fn(() => []) },
}));

vi.mock('@codemirror/state', () => ({
  EditorState: {
    create: vi.fn(() => ({})),
  },
}));

vi.mock('@codemirror/lang-markdown', () => ({
  markdown: vi.fn(() => []),
}));

vi.mock('codemirror', () => ({
  basicSetup: [],
}));

vi.mock('@codemirror/basic-setup', () => ({
  basicSetup: [],
}));

const defaultProps = {
  skillName: 'test-skill',
  frontmatter: { description: 'A test skill description' },
  content: '## Instructions\nDo something useful.',
  isUpdate: false,
};

describe('SkillCreatorCard', () => {
  let onSave: ReturnType<typeof vi.fn>;
  let onTest: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onSave = vi.fn();
    onTest = vi.fn();
  });

  it('renders skill name from props', () => {
    render(<SkillCreatorCard {...defaultProps} onSave={onSave} onTest={onTest} />);
    expect(screen.getByText('test-skill')).toBeInTheDocument();
  });

  it('renders description from frontmatter', () => {
    render(<SkillCreatorCard {...defaultProps} onSave={onSave} onTest={onTest} />);
    expect(screen.getByText('A test skill description')).toBeInTheDocument();
  });

  it('shows content in read-only mode by default', () => {
    render(<SkillCreatorCard {...defaultProps} onSave={onSave} onTest={onTest} />);
    // Content is shown in a <pre> element; check for partial text
    expect(screen.getByText(/Do something useful/)).toBeInTheDocument();
    expect(screen.queryByTestId('codemirror-editor')).not.toBeInTheDocument();
  });

  it('shows "Updated" badge when isUpdate=true', () => {
    render(<SkillCreatorCard {...defaultProps} isUpdate={true} onSave={onSave} onTest={onTest} />);
    expect(screen.getByText('Updated')).toBeInTheDocument();
  });

  it('shows "New" badge when isUpdate=false', () => {
    render(<SkillCreatorCard {...defaultProps} isUpdate={false} onSave={onSave} onTest={onTest} />);
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('clicking Edit button opens modal with CodeMirror editor', async () => {
    const user = userEvent.setup();
    render(<SkillCreatorCard {...defaultProps} onSave={onSave} onTest={onTest} />);
    const editButton = screen.getByRole('button', { name: /edit/i });
    await user.click(editButton);
    // Modal opens with the skill name in the dialog title
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByTestId('codemirror-editor')).toBeInTheDocument();
  });

  it('calls onTest with current content when Test button clicked', async () => {
    const user = userEvent.setup();
    render(<SkillCreatorCard {...defaultProps} onSave={onSave} onTest={onTest} />);
    await user.click(screen.getByRole('button', { name: /test/i }));
    expect(onTest).toHaveBeenCalledWith(defaultProps.content);
  });

  it('calls onSave with current content when Save button clicked', async () => {
    const user = userEvent.setup();
    render(<SkillCreatorCard {...defaultProps} onSave={onSave} onTest={onTest} />);
    await user.click(screen.getByRole('button', { name: /save/i }));
    expect(onSave).toHaveBeenCalledWith(defaultProps.content);
  });
});
