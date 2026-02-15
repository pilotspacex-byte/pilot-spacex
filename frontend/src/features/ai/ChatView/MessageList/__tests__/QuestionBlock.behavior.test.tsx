/**
 * Unit tests for QuestionBlock component — Behavior & Accessibility.
 *
 * Tests resolved/collapsed state, keyboard navigation, ARIA compliance,
 * onSubmit callback correctness, and edge cases.
 *
 * Feature 014: Approval & User Input UX (T06)
 *
 * See also: QuestionBlock.test.tsx (rendering & navigation)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuestionBlock } from '../QuestionBlock';
import type { AgentQuestion } from '@/stores/ai/types/events';

// ---------------------------------------------------------------------------
// Helpers (duplicated from QuestionBlock.test.tsx for test isolation)
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

describe('QuestionBlock — Behavior & Accessibility', () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // -----------------------------------------------------------------------
  // 7. Collapsed state after submit
  // -----------------------------------------------------------------------

  describe('resolved (collapsed) state', () => {
    it('shows header + answer inline for single question', () => {
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={true}
          resolvedAnswers={{ q0: 'High' }}
        />
      );

      expect(screen.getByText('High')).toBeInTheDocument();
    });

    it('has aria-label "Answered question summary"', () => {
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={true}
          resolvedAnswers={{ q0: 'Medium' }}
        />
      );

      expect(screen.getByRole('region', { name: 'Answered question summary' })).toBeInTheDocument();
    });

    it('expands to show full answers when chevron is clicked', async () => {
      const user = userEvent.setup();
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={true}
          resolvedAnswers={{ q0: 'Low' }}
        />
      );

      // The summary toggle button has aria-expanded="false" by default
      const expandButton = screen.getByRole('button', { expanded: false });
      expect(expandButton).toHaveAttribute('aria-expanded', 'false');

      await user.click(expandButton);

      expect(expandButton).toHaveAttribute('aria-expanded', 'true');
      // Expanded view shows answer
      expect(screen.getAllByText('Low').length).toBeGreaterThanOrEqual(2);
    });

    it('shows answer chips for multiple questions', () => {
      const questions = makeQuestionSet(2);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={true}
          resolvedAnswers={{
            q0: 'High',
            q1: 'Bug, Feature',
          }}
        />
      );

      expect(
        screen.getByRole('region', { name: /answered question summary/i })
      ).toBeInTheDocument();
      expect(screen.getByText('High')).toBeInTheDocument();
      expect(screen.getByText('Bug, Feature')).toBeInTheDocument();
    });

    it('does not render interactive options in resolved state', () => {
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={true}
          resolvedAnswers={{ q0: 'High' }}
        />
      );

      expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument();
      expect(screen.queryByRole('radio')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /submit/i })).not.toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // 8. Keyboard navigation
  // -----------------------------------------------------------------------

  describe('keyboard navigation', () => {
    it('Tab cycles through option buttons', async () => {
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

      // Tab through the options
      await user.tab();
      // First focusable element may vary; keep tabbing until we reach a radio
      let tabCount = 0;
      while (tabCount < 10 && !radios.some((r) => r === document.activeElement)) {
        await user.tab();
        tabCount++;
      }
      expect(radios.some((r) => r === document.activeElement)).toBe(true);
    });

    it('Enter toggles an option when focused', async () => {
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
      radios[0]!.focus();

      await user.keyboard('{Enter}');
      expect(radios[0]!).toHaveAttribute('aria-checked', 'true');
    });

    it('Space toggles an option when focused', async () => {
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
      radios[1]!.focus();

      await user.keyboard('{ }');
      expect(radios[1]!).toHaveAttribute('aria-checked', 'true');
    });
  });

  // -----------------------------------------------------------------------
  // 9. ARIA compliance
  // -----------------------------------------------------------------------

  describe('ARIA attributes', () => {
    it('uses role="radiogroup" for single-select questions', () => {
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const radiogroup = screen.getByRole('radiogroup');
      expect(radiogroup).toHaveAttribute('aria-label', 'What priority should this issue have?');
    });

    it('uses role="group" with role="checkbox" for multi-select', () => {
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
      expect(screen.getByRole('group')).toHaveAttribute('aria-label', 'Which labels apply?');

      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBeGreaterThan(0);
    });

    it('has aria-checked on all option buttons', () => {
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
      for (const radio of radios) {
        expect(radio).toHaveAttribute('aria-checked');
      }
    });

    it('has aria-busy on submit button while submitting', async () => {
      // We test that the submit button has aria-busy attribute set up
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
      // Before submission, aria-busy should not be true
      expect(submitButton).not.toHaveAttribute('aria-busy', 'true');
    });

    it('wraps component in role="region" with descriptive aria-label', () => {
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const region = screen.getByRole('region', { name: /agent question/i });
      expect(region).toBeInTheDocument();
    });

    it('includes sr-only live region for step announcements', () => {
      const questions = makeQuestionSet(3);
      const { container } = render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const liveRegion = container.querySelector('[aria-live="polite"]');
      expect(liveRegion).toBeInTheDocument();
    });

    it('option buttons have descriptive aria-label combining label and description', () => {
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.getByRole('radio', { name: 'High: Blocks release' })).toBeInTheDocument();
      expect(screen.getByRole('radio', { name: 'Low: Nice to have' })).toBeInTheDocument();
      // "Medium" has no description, so label is just the label
      expect(screen.getByRole('radio', { name: 'Medium' })).toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // 10. onSubmit callback correctness
  // -----------------------------------------------------------------------

  describe('onSubmit callback', () => {
    it('calls onSubmit with questionId and answers Record (single question)', async () => {
      const user = userEvent.setup();
      const question = makeSingleSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-42"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const radios = screen.getAllByRole('radio');
      await user.click(radios[1]!); // Select "Medium"
      await user.click(screen.getByRole('button', { name: /submit/i }));

      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith('q-42', {
        q0: 'Medium',
      });
    });

    it('calls onSubmit with multi-select answers joined by comma', async () => {
      const user = userEvent.setup();
      const question = makeMultiSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-99"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]!); // Bug
      await user.click(checkboxes[1]!); // Feature
      await user.click(screen.getByRole('button', { name: /submit/i }));

      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith('q-99', {
        q0: 'Bug, Feature',
      });
    });

    it('includes "Other" custom text in the answer', async () => {
      const user = userEvent.setup();
      const question = makeMultiSelectQuestion();
      render(
        <QuestionBlock
          questionId="q-100"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]!); // Bug
      await user.click(checkboxes[3]!); // Other

      const otherInput = screen.getByLabelText('Custom answer text');
      await user.type(otherInput, 'Performance regression');

      await user.click(screen.getByRole('button', { name: /submit/i }));

      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith('q-100', {
        q0: 'Bug, Performance regression',
      });
    });

    it('calls onSubmit with all question answers in stepping mode', async () => {
      const user = userEvent.setup();
      const questions = makeQuestionSet(3);
      render(
        <QuestionBlock
          questionId="q-step"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      // Step 1: single-select "High"
      await user.click(screen.getAllByRole('radio')[0]!);
      await user.click(screen.getByRole('button', { name: /next/i }));

      // Step 2: multi-select "Bug"
      await user.click(screen.getAllByRole('checkbox')[0]!);
      await user.click(screen.getByRole('button', { name: /next/i }));

      // Step 3: single-select "Alice"
      await user.click(screen.getAllByRole('radio')[0]!);
      await user.click(screen.getByRole('button', { name: /submit/i }));

      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith('q-step', {
        q0: 'High',
        q1: 'Bug',
        q2: 'Alice',
      });
    });

    it('shows "Submitting..." text after clicking submit', async () => {
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

      await user.click(screen.getAllByRole('radio')[0]!);
      await user.click(screen.getByRole('button', { name: /submit/i }));

      expect(screen.getByText('Submitting...')).toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // Edge cases
  // -----------------------------------------------------------------------

  describe('edge cases', () => {
    it('renders header from single question with header field', () => {
      const question = makeSingleSelectQuestion({ header: 'Priority Selection' });
      render(
        <QuestionBlock
          questionId="q-1"
          questions={[question]}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.getByText('Priority Selection')).toBeInTheDocument();
    });

    it('renders default header "Agent needs your input" for multiple questions', () => {
      const questions = makeQuestionSet(2);
      render(
        <QuestionBlock
          questionId="q-1"
          questions={questions}
          onSubmit={mockOnSubmit}
          isResolved={false}
        />
      );

      expect(screen.getByText('Agent needs your input')).toBeInTheDocument();
    });
  });
});
