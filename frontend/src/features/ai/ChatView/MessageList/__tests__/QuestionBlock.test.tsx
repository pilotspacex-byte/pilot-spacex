/**
 * Unit tests for QuestionBlock component — Rendering & Navigation.
 *
 * Tests single/multi-select rendering, submit button state, "Other" text input,
 * step navigation, and non-stepping mode.
 *
 * Feature 014: Approval & User Input UX (T06)
 *
 * See also: QuestionBlock.behavior.test.tsx (resolved state, keyboard, ARIA, callbacks)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuestionBlock } from '../QuestionBlock';
import type { AgentQuestion } from '@/stores/ai/types/events';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeSingleSelectQuestion(overrides?: Partial<AgentQuestion>): AgentQuestion {
  return {
    question: 'What priority should this issue have?',
    options: [
      { label: 'High', description: 'Blocks release' },
      { label: 'Medium' },
      { label: 'Low', description: 'Nice to have' },
    ],
    multiSelect: false,
    ...overrides,
  };
}

function makeMultiSelectQuestion(overrides?: Partial<AgentQuestion>): AgentQuestion {
  return {
    question: 'Which labels apply?',
    options: [
      { label: 'Bug' },
      { label: 'Feature' },
      { label: 'Documentation' },
      { label: 'Other' },
    ],
    multiSelect: true,
    ...overrides,
  };
}

/** Create N distinct questions for step-navigation tests. */
function makeQuestionSet(count: number): AgentQuestion[] {
  const templates = [
    makeSingleSelectQuestion({ question: 'Question 1: Priority?' }),
    makeMultiSelectQuestion({ question: 'Question 2: Labels?' }),
    makeSingleSelectQuestion({
      question: 'Question 3: Assignee?',
      options: [{ label: 'Alice' }, { label: 'Bob' }, { label: 'Other' }],
    }),
    makeSingleSelectQuestion({
      question: 'Question 4: Sprint?',
      options: [{ label: 'Sprint 1' }, { label: 'Sprint 2' }],
    }),
  ];
  return templates.slice(0, count);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('QuestionBlock', () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // -----------------------------------------------------------------------
  // 1. Single-select (radio) rendering
  // -----------------------------------------------------------------------

  describe('single-select question', () => {
    it('renders question text and radio options', () => {
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.getByText('What priority should this issue have?')).toBeInTheDocument();
      expect(screen.getByRole('radiogroup')).toBeInTheDocument();

      const radios = screen.getAllByRole('radio');
      expect(radios).toHaveLength(3);
      expect(radios[0]).toHaveAttribute('aria-checked', 'false');
    });

    it('renders option descriptions when provided', () => {
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.getByText('Blocks release')).toBeInTheDocument();
      expect(screen.getByText('Nice to have')).toBeInTheDocument();
    });

    it('selects one option at a time (radio behavior)', async () => {
      const user = userEvent.setup();
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const radios = screen.getAllByRole('radio');

      await user.click(radios[0]!);
      expect(radios[0]!).toHaveAttribute('aria-checked', 'true');
      expect(radios[1]!).toHaveAttribute('aria-checked', 'false');

      await user.click(radios[1]!);
      expect(radios[0]!).toHaveAttribute('aria-checked', 'false');
      expect(radios[1]!).toHaveAttribute('aria-checked', 'true');
    });
  });

  // -----------------------------------------------------------------------
  // 2. Multi-select (checkbox) rendering
  // -----------------------------------------------------------------------

  describe('multi-select question', () => {
    it('renders checkboxes with role="group"', () => {
      const question = makeMultiSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.getByRole('group')).toBeInTheDocument();
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes).toHaveLength(4);
    });

    it('allows multiple selections', async () => {
      const user = userEvent.setup();
      const question = makeMultiSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');

      await user.click(checkboxes[0]!);
      await user.click(checkboxes[2]!);

      expect(checkboxes[0]!).toHaveAttribute('aria-checked', 'true');
      expect(checkboxes[1]!).toHaveAttribute('aria-checked', 'false');
      expect(checkboxes[2]!).toHaveAttribute('aria-checked', 'true');
    });

    it('toggles a checkbox off when clicked again', async () => {
      const user = userEvent.setup();
      const question = makeMultiSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');

      await user.click(checkboxes[0]!);
      expect(checkboxes[0]!).toHaveAttribute('aria-checked', 'true');

      await user.click(checkboxes[0]!);
      expect(checkboxes[0]!).toHaveAttribute('aria-checked', 'false');
    });
  });

  // -----------------------------------------------------------------------
  // 3. Submit button disabled until selection
  // -----------------------------------------------------------------------

  describe('submit button state', () => {
    it('is disabled when no option is selected', () => {
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const submitButton = screen.getByRole('button', { name: /submit/i });
      expect(submitButton).toBeDisabled();
    });

    it('becomes enabled after selecting an option', async () => {
      const user = userEvent.setup();
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const radios = screen.getAllByRole('radio');
      await user.click(radios[1]!);

      const submitButton = screen.getByRole('button', { name: /submit/i });
      expect(submitButton).toBeEnabled();
    });

    it('does not call onSubmit when clicked while disabled', async () => {
      const user = userEvent.setup();
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  // -----------------------------------------------------------------------
  // 4. "Other" option with text input
  // -----------------------------------------------------------------------

  describe('"Other" option behavior', () => {
    it('shows text input when "Other" is selected', async () => {
      const user = userEvent.setup();
      const question = makeMultiSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      // "Other" is the last option
      await user.click(checkboxes[3]!);

      const otherInput = screen.getByLabelText('Custom answer text');
      expect(otherInput).toBeInTheDocument();
      expect(otherInput).toHaveAttribute('maxLength', '200');
    });

    it('hides text input when "Other" is deselected', async () => {
      const user = userEvent.setup();
      const question = makeMultiSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[3]!);
      expect(screen.getByLabelText('Custom answer text')).toBeInTheDocument();

      await user.click(checkboxes[3]!);
      expect(screen.queryByLabelText('Custom answer text')).not.toBeInTheDocument();
    });

    it('requires non-empty text for "Other" before submit is enabled', async () => {
      const user = userEvent.setup();
      const question = makeSingleSelectQuestion({
        options: [{ label: 'Option A' }, { label: 'Other' }],
      });
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const radios = screen.getAllByRole('radio');
      // Select "Other" (last option)
      await user.click(radios[1]!);

      const submitButton = screen.getByRole('button', { name: /submit/i });
      // Submit should be disabled: "Other" selected but no text
      expect(submitButton).toBeDisabled();

      const otherInput = screen.getByLabelText('Custom answer text');
      await user.type(otherInput, 'My custom answer');

      expect(submitButton).toBeEnabled();
    });

    it('enforces 200-character max length on "Other" input', async () => {
      const user = userEvent.setup();
      const question = makeSingleSelectQuestion({
        options: [{ label: 'A' }, { label: 'Other' }],
      });
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const radios = screen.getAllByRole('radio');
      await user.click(radios[1]!);

      const otherInput = screen.getByLabelText('Custom answer text');
      expect(otherInput).toHaveAttribute('maxLength', '200');
    });
  });

  // -----------------------------------------------------------------------
  // 5. Step indicator for 3+ questions
  // -----------------------------------------------------------------------

  describe('step navigation (3+ questions)', () => {
    it('shows step indicator "1/3" for first of 3 questions', () => {
      const questions = makeQuestionSet(3);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.getByText('1/3')).toBeInTheDocument();
    });

    it('shows Next button on non-last steps and no Submit', () => {
      const questions = makeQuestionSet(3);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /submit/i })).not.toBeInTheDocument();
    });

    it('navigates forward when Next is clicked after selection', async () => {
      const user = userEvent.setup();
      const questions = makeQuestionSet(3);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      // Step 1: select an option and click Next
      const radios = screen.getAllByRole('radio');
      await user.click(radios[0]!);
      await user.click(screen.getByRole('button', { name: /next/i }));

      expect(screen.getByText('2/3')).toBeInTheDocument();
      expect(screen.getByText('Question 2: Labels?')).toBeInTheDocument();
    });

    it('shows Back button from step 2 onward', async () => {
      const user = userEvent.setup();
      const questions = makeQuestionSet(3);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      // No Back button on step 1
      expect(screen.queryByRole('button', { name: /back/i })).not.toBeInTheDocument();

      // Navigate to step 2
      const radios = screen.getAllByRole('radio');
      await user.click(radios[0]!);
      await user.click(screen.getByRole('button', { name: /next/i }));

      expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
    });

    it('navigates back to previous step', async () => {
      const user = userEvent.setup();
      const questions = makeQuestionSet(3);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      // Step 1 -> Step 2
      const radios = screen.getAllByRole('radio');
      await user.click(radios[0]!);
      await user.click(screen.getByRole('button', { name: /next/i }));
      expect(screen.getByText('2/3')).toBeInTheDocument();

      // Back to Step 1
      await user.click(screen.getByRole('button', { name: /back/i }));
      expect(screen.getByText('1/3')).toBeInTheDocument();
    });

    it('shows Submit button on last step', async () => {
      const user = userEvent.setup();
      const questions = makeQuestionSet(3);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      // Step 1
      await user.click(screen.getAllByRole('radio')[0]!);
      await user.click(screen.getByRole('button', { name: /next/i }));

      // Step 2 (multi-select)
      await user.click(screen.getAllByRole('checkbox')[0]!);
      await user.click(screen.getByRole('button', { name: /next/i }));

      // Step 3 (last step) - should show Submit, not Next
      expect(screen.getByText('3/3')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /next/i })).not.toBeInTheDocument();
    });

    it('Next button is disabled until current step has a selection', () => {
      const questions = makeQuestionSet(3);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const nextButton = screen.getByRole('button', { name: /next/i });
      expect(nextButton).toBeDisabled();
    });
  });

  // -----------------------------------------------------------------------
  // 6. 1-2 questions render without stepping
  // -----------------------------------------------------------------------

  describe('non-stepping mode (1-2 questions)', () => {
    it('renders all questions at once for 2 questions', () => {
      const questions = makeQuestionSet(2);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.getByText('Question 1: Priority?')).toBeInTheDocument();
      expect(screen.getByText('Question 2: Labels?')).toBeInTheDocument();
    });

    it('does not show Back/Next buttons for 1 question', () => {
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.queryByRole('button', { name: /next/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /back/i })).not.toBeInTheDocument();
    });

    it('does not show Back/Next buttons for 2 questions', () => {
      const questions = makeQuestionSet(2);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.queryByRole('button', { name: /next/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /back/i })).not.toBeInTheDocument();
    });

    it('does not show step indicator for fewer than 3 questions', () => {
      const questions = makeQuestionSet(2);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.queryByText(/\d\/\d/)).not.toBeInTheDocument();
    });

    it('requires all questions answered before submit is enabled', async () => {
      const user = userEvent.setup();
      const questions = makeQuestionSet(2);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const submitButton = screen.getByRole('button', { name: /submit/i });
      expect(submitButton).toBeDisabled();

      // Answer only the first question
      const radios = screen.getAllByRole('radio');
      await user.click(radios[0]!);
      expect(submitButton).toBeDisabled();

      // Answer the second question (checkboxes)
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]!);
      expect(submitButton).toBeEnabled();
    });
  });
});
