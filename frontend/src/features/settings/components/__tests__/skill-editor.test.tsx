/**
 * Tests for SkillEditor component.
 *
 * T040: Skill editor rendering, word count, toolbar, save/cancel.
 * Source: FR-009, FR-010, US6
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SkillEditor } from '../skill-editor';

describe('SkillEditor', () => {
  const defaultProps = {
    initialContent: '# Developer\n\n## Focus Areas\n- Code quality\n- Architecture',
    onSave: vi.fn(),
    onCancel: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should render textarea with initial content', () => {
      render(<SkillEditor {...defaultProps} />);
      const textarea = screen.getByLabelText('Skill content editor');
      expect(textarea).toHaveValue(defaultProps.initialContent);
    });

    it('should render toolbar buttons', () => {
      render(<SkillEditor {...defaultProps} />);
      expect(screen.getByTitle('Bold')).toBeInTheDocument();
      expect(screen.getByTitle('Italic')).toBeInTheDocument();
      expect(screen.getByTitle('Heading 1')).toBeInTheDocument();
      expect(screen.getByTitle('Heading 2')).toBeInTheDocument();
      expect(screen.getByTitle('Heading 3')).toBeInTheDocument();
      expect(screen.getByTitle('Bullet List')).toBeInTheDocument();
      expect(screen.getByTitle('Code Block')).toBeInTheDocument();
    });

    it('should render Save and Cancel buttons', () => {
      render(<SkillEditor {...defaultProps} />);
      expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    });

    it('should show word count', () => {
      render(<SkillEditor {...defaultProps} />);
      expect(screen.getByText(/\/ 2000 words/)).toBeInTheDocument();
    });
  });

  describe('editing', () => {
    it('should update content when typing', async () => {
      const user = userEvent.setup();
      render(<SkillEditor {...defaultProps} />);

      const textarea = screen.getByLabelText('Skill content editor');
      await user.clear(textarea);
      await user.type(textarea, 'New content');

      expect(textarea).toHaveValue('New content');
    });

    it('should call onSave with content when Save is clicked', async () => {
      const user = userEvent.setup();
      render(<SkillEditor {...defaultProps} />);

      const saveButton = screen.getByRole('button', { name: 'Save' });
      await user.click(saveButton);

      expect(defaultProps.onSave).toHaveBeenCalledWith(defaultProps.initialContent);
    });

    it('should call onCancel when Cancel is clicked', async () => {
      const user = userEvent.setup();
      render(<SkillEditor {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      await user.click(cancelButton);

      expect(defaultProps.onCancel).toHaveBeenCalledOnce();
    });

    it('should call onCancel when Escape is pressed', async () => {
      const user = userEvent.setup();
      render(<SkillEditor {...defaultProps} />);

      const textarea = screen.getByLabelText('Skill content editor');
      await user.click(textarea);
      await user.keyboard('{Escape}');

      expect(defaultProps.onCancel).toHaveBeenCalledOnce();
    });
  });

  describe('validation', () => {
    it('should disable Save when content is empty', async () => {
      const user = userEvent.setup();
      render(<SkillEditor {...defaultProps} />);

      const textarea = screen.getByLabelText('Skill content editor');
      await user.clear(textarea);

      expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
    });

    it('should show saving state', () => {
      render(<SkillEditor {...defaultProps} isSaving />);
      expect(screen.getByRole('button', { name: 'Saving...' })).toBeDisabled();
    });
  });
});
