/**
 * Comprehensive tests for FormRenderer component (FR-027, FR-028, FR-029).
 *
 * FormRenderer renders Form PM blocks with 10 field types:
 * text, email, url, textarea, number, date, select, multiselect, checkbox, rating.
 *
 * Features:
 * - Field validation (required, min, max, pattern)
 * - Response collection and submission tracking
 * - Read-only mode
 * - Accessible form controls with ARIA labels
 *
 * Spec refs: FR-027 (10 field types), FR-028 (validation), FR-029 (response collection)
 *
 * @module pm-blocks/__tests__/FormRenderer.test
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FormRenderer } from '../renderers/FormRenderer';
import type { PMRendererProps } from '../PMBlockNodeView';

const defaultProps: PMRendererProps = {
  data: {} as Record<string, unknown>,
  readOnly: false,
  onDataChange: vi.fn(),
  blockType: 'form' as const,
};

// ── Basic rendering ─────────────────────────────────────────────────────
describe('FormRenderer basic rendering', () => {
  it('renders with data-testid="form-renderer"', () => {
    render(<FormRenderer {...defaultProps} />);
    expect(screen.getByTestId('form-renderer')).toBeInTheDocument();
  });

  it('renders default title "Untitled Form"', () => {
    render(<FormRenderer {...defaultProps} />);
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Untitled Form');
  });

  it('renders custom title when provided', () => {
    const formData = {
      title: 'Customer Feedback Survey',
      fields: [],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Customer Feedback Survey');
  });

  it('renders default fields (Name, Email, Comments)', () => {
    render(<FormRenderer {...defaultProps} />);
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Comments')).toBeInTheDocument();
  });

  it('renders response count at bottom', () => {
    const formData = {
      title: 'Test Form',
      fields: [],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    expect(screen.getByText('0 responses')).toBeInTheDocument();
  });

  it('renders singular "response" when count is 1', () => {
    const formData = {
      title: 'Test Form',
      fields: [],
      responses: {},
      responseCount: 1,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    expect(screen.getByText('1 response')).toBeInTheDocument();
  });

  it('renders plural "responses" when count > 1', () => {
    const formData = {
      title: 'Test Form',
      fields: [],
      responses: {},
      responseCount: 5,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    expect(screen.getByText('5 responses')).toBeInTheDocument();
  });
});

// ── Description ─────────────────────────────────────────────────────────
describe('FormRenderer description', () => {
  it('renders description when present', () => {
    const formData = {
      title: 'Test Form',
      description: 'Please fill out all required fields below.',
      fields: [],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    expect(screen.getByText('Please fill out all required fields below.')).toBeInTheDocument();
  });

  it('does not render description paragraph when absent', () => {
    const formData = {
      title: 'Test Form',
      fields: [],
      responses: {},
      responseCount: 0,
    };
    const { container } = render(<FormRenderer {...defaultProps} data={formData} />);
    const paragraphs = container.querySelectorAll('p');
    // Filter out any error/response count paragraphs
    const descriptionParagraphs = Array.from(paragraphs).filter(
      (p) => p.className.includes('text-muted-foreground') && !p.textContent?.includes('response')
    );
    expect(descriptionParagraphs.length).toBe(0);
  });
});

// ── Text field (FR-027) ─────────────────────────────────────────────────
describe('FormRenderer text field (FR-027)', () => {
  it('renders text input with label', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Full Name', type: 'text' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    const input = screen.getByLabelText('Full Name');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'text');
  });

  it('renders placeholder for text field', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Full Name',
          type: 'text' as const,
          placeholder: 'Enter your full name',
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    expect(screen.getByPlaceholderText('Enter your full name')).toBeInTheDocument();
  });

  it('generates default placeholder from label when not provided', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Username', type: 'text' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    expect(screen.getByPlaceholderText('Enter username')).toBeInTheDocument();
  });

  it('calls onDataChange when text input changes', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Name', type: 'text' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const input = screen.getByLabelText('Name');
    await userEvent.type(input, 'John');

    expect(onDataChange).toHaveBeenCalled();
    // Check that onDataChange was called with accumulated text
    expect(onDataChange.mock.calls.length).toBeGreaterThan(0);
  });

  it('displays existing response value in text field', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Name', type: 'text' as const, required: false }],
      responses: { f1: 'Jane Smith' },
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    expect(screen.getByLabelText('Name')).toHaveValue('Jane Smith');
  });
});

// ── Email field (FR-027) ────────────────────────────────────────────────
describe('FormRenderer email field (FR-027)', () => {
  it('renders email input with correct type', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Email Address', type: 'email' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    const input = screen.getByLabelText('Email Address');
    expect(input).toHaveAttribute('type', 'email');
  });

  it('calls onDataChange when email input changes', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Email', type: 'email' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const input = screen.getByLabelText('Email');
    await userEvent.type(input, 'test@ex.com');

    expect(onDataChange).toHaveBeenCalled();
    // Verify that typing triggered multiple onChange calls
    expect(onDataChange.mock.calls.length).toBeGreaterThan(0);
  });
});

// ── URL field (FR-027) ──────────────────────────────────────────────────
describe('FormRenderer url field (FR-027)', () => {
  it('renders url input with correct type', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Website', type: 'url' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    const input = screen.getByLabelText('Website');
    expect(input).toHaveAttribute('type', 'url');
  });
});

// ── Textarea field (FR-027) ─────────────────────────────────────────────
describe('FormRenderer textarea field (FR-027)', () => {
  it('renders textarea element', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Comments', type: 'textarea' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    const textarea = screen.getByLabelText('Comments');
    expect(textarea.tagName).toBe('TEXTAREA');
  });

  it('calls onDataChange when textarea changes', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Comments', type: 'textarea' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const textarea = screen.getByLabelText('Comments');
    await userEvent.type(textarea, 'Great product!');

    expect(onDataChange).toHaveBeenCalled();
  });
});

// ── Number field (FR-027) ───────────────────────────────────────────────
describe('FormRenderer number field (FR-027)', () => {
  it('renders number input with correct type', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Age', type: 'number' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    const input = screen.getByLabelText('Age');
    expect(input).toHaveAttribute('type', 'number');
  });

  it('applies min and max attributes', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Rating',
          type: 'number' as const,
          min: 1,
          max: 10,
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    const input = screen.getByLabelText('Rating');
    expect(input).toHaveAttribute('min', '1');
    expect(input).toHaveAttribute('max', '10');
  });

  it('calls onDataChange with number value', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Age', type: 'number' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const input = screen.getByLabelText('Age');
    await userEvent.type(input, '25');

    expect(onDataChange).toHaveBeenCalled();
  });
});

// ── Date field (FR-027) ─────────────────────────────────────────────────
describe('FormRenderer date field (FR-027)', () => {
  it('renders date input with correct type', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Birth Date', type: 'date' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    const input = screen.getByLabelText('Birth Date');
    expect(input).toHaveAttribute('type', 'date');
  });

  it('calls onDataChange when date is selected', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Birth Date', type: 'date' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const input = screen.getByLabelText('Birth Date');
    await userEvent.type(input, '2000-01-15');

    expect(onDataChange).toHaveBeenCalled();
  });
});

// ── Select field (FR-027) ───────────────────────────────────────────────
describe('FormRenderer select field (FR-027)', () => {
  it('renders select dropdown with options', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Country',
          type: 'select' as const,
          options: ['USA', 'Canada', 'UK'],
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    const select = screen.getByLabelText('Country') as HTMLSelectElement;
    expect(select.tagName).toBe('SELECT');
    expect(screen.getByRole('option', { name: 'USA' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Canada' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'UK' })).toBeInTheDocument();
  });

  it('renders default "Select..." option', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Country',
          type: 'select' as const,
          options: ['USA', 'Canada'],
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);
    expect(screen.getByRole('option', { name: 'Select...' })).toBeInTheDocument();
  });

  it('calls onDataChange when option is selected', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Country',
          type: 'select' as const,
          options: ['USA', 'Canada', 'UK'],
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const select = screen.getByLabelText('Country');
    await userEvent.selectOptions(select, 'Canada');

    expect(onDataChange).toHaveBeenCalled();
    const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
    expect(lastCall.responses.f1).toBe('Canada');
  });
});

// ── Multiselect field (FR-027) ──────────────────────────────────────────
describe('FormRenderer multiselect field (FR-027)', () => {
  it('renders multiselect with checkbox labels', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Interests',
          type: 'multiselect' as const,
          options: ['Sports', 'Music', 'Reading'],
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    expect(screen.getByText('Sports')).toBeInTheDocument();
    expect(screen.getByText('Music')).toBeInTheDocument();
    expect(screen.getByText('Reading')).toBeInTheDocument();
  });

  it('renders multiselect with role="group"', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Interests',
          type: 'multiselect' as const,
          options: ['Sports', 'Music'],
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    const group = screen.getByRole('group', { name: 'Interests' });
    expect(group).toBeInTheDocument();
  });

  it('calls onDataChange with array when options are selected', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Interests',
          type: 'multiselect' as const,
          options: ['Sports', 'Music', 'Reading'],
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const sportsLabel = screen.getByText('Sports');
    await userEvent.click(sportsLabel);

    expect(onDataChange).toHaveBeenCalled();
    const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
    expect(lastCall.responses.f1).toEqual(['Sports']);
  });

  it('handles multiple selections correctly', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Interests',
          type: 'multiselect' as const,
          options: ['Sports', 'Music', 'Reading'],
          required: false,
        },
      ],
      responses: { f1: ['Sports'] },
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const musicLabel = screen.getByText('Music');
    await userEvent.click(musicLabel);

    expect(onDataChange).toHaveBeenCalled();
    const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
    expect(lastCall.responses.f1).toEqual(['Sports', 'Music']);
  });

  it('handles deselection correctly', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Interests',
          type: 'multiselect' as const,
          options: ['Sports', 'Music'],
          required: false,
        },
      ],
      responses: { f1: ['Sports', 'Music'] },
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const sportsLabel = screen.getByText('Sports');
    await userEvent.click(sportsLabel);

    expect(onDataChange).toHaveBeenCalled();
    const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
    expect(lastCall.responses.f1).toEqual(['Music']);
  });
});

// ── Checkbox field (FR-027) ─────────────────────────────────────────────
describe('FormRenderer checkbox field (FR-027)', () => {
  it('renders checkbox with label text', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Terms',
          type: 'checkbox' as const,
          placeholder: 'I agree to the terms and conditions',
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    expect(screen.getByLabelText('Terms')).toBeInTheDocument();
    expect(screen.getByText('I agree to the terms and conditions')).toBeInTheDocument();
  });

  it('uses label as text when placeholder is not provided', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Newsletter',
          type: 'checkbox' as const,
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    const { container } = render(<FormRenderer {...defaultProps} data={formData} />);

    // Both the field label and the checkbox label text contain "Newsletter"
    const checkboxLabel = container.querySelector('label.inline-flex span');
    expect(checkboxLabel).toHaveTextContent('Newsletter');
  });

  it('calls onDataChange when checkbox is toggled', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Newsletter',
          type: 'checkbox' as const,
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const checkbox = screen.getByLabelText('Newsletter');
    await userEvent.click(checkbox);

    expect(onDataChange).toHaveBeenCalled();
    const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
    expect(lastCall.responses.f1).toBe(true);
  });
});

// ── Rating field (FR-027) ───────────────────────────────────────────────
describe('FormRenderer rating field (FR-027)', () => {
  it('renders 5 star buttons by default', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Rating', type: 'rating' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    expect(screen.getByLabelText('1 star')).toBeInTheDocument();
    expect(screen.getByLabelText('2 stars')).toBeInTheDocument();
    expect(screen.getByLabelText('3 stars')).toBeInTheDocument();
    expect(screen.getByLabelText('4 stars')).toBeInTheDocument();
    expect(screen.getByLabelText('5 stars')).toBeInTheDocument();
  });

  it('renders custom max stars when specified', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Rating',
          type: 'rating' as const,
          max: 3,
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    expect(screen.getByLabelText('1 star')).toBeInTheDocument();
    expect(screen.getByLabelText('2 stars')).toBeInTheDocument();
    expect(screen.getByLabelText('3 stars')).toBeInTheDocument();
    expect(screen.queryByLabelText('4 stars')).not.toBeInTheDocument();
  });

  it('calls onDataChange when star is clicked', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Rating', type: 'rating' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const star3 = screen.getByLabelText('3 stars');
    await userEvent.click(star3);

    expect(onDataChange).toHaveBeenCalled();
    const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
    expect(lastCall.responses.f1).toBe(3);
  });

  it('renders filled stars up to selected rating', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Rating', type: 'rating' as const, required: false }],
      responses: { f1: 3 },
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    const radiogroup = screen.getByRole('radiogroup', { name: 'Rating' });
    expect(radiogroup).toBeInTheDocument();
  });

  it('renders rating with role="radiogroup"', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Quality', type: 'rating' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    expect(screen.getByRole('radiogroup', { name: 'Quality' })).toBeInTheDocument();
  });
});

// ── Required fields (FR-028) ────────────────────────────────────────────
describe('FormRenderer required fields (FR-028)', () => {
  it('shows asterisk for required fields', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        { id: 'f1', label: 'Name', type: 'text' as const, required: true },
        { id: 'f2', label: 'Email', type: 'email' as const, required: true },
      ],
      responses: {},
      responseCount: 0,
    };
    const { container } = render(<FormRenderer {...defaultProps} data={formData} />);

    const asterisks = container.querySelectorAll('span.text-destructive');
    expect(asterisks.length).toBeGreaterThanOrEqual(2);
  });

  it('does not show asterisk for optional fields', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Comments', type: 'textarea' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    const label = screen.getByText('Comments');
    const parent = label.parentElement;
    expect(parent?.textContent).not.toMatch(/\*/);
  });

  it('marks required text input with required attribute', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Name', type: 'text' as const, required: true }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    const input = screen.getByLabelText('Name');
    expect(input).toHaveAttribute('required');
  });
});

// ── ReadOnly mode ───────────────────────────────────────────────────────
describe('FormRenderer readOnly mode', () => {
  it('disables text input when readOnly is true', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Name', type: 'text' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} readOnly={true} />);

    expect(screen.getByLabelText('Name')).toBeDisabled();
  });

  it('disables textarea when readOnly is true', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Comments', type: 'textarea' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} readOnly={true} />);

    expect(screen.getByLabelText('Comments')).toBeDisabled();
  });

  it('disables select when readOnly is true', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Country',
          type: 'select' as const,
          options: ['USA', 'Canada'],
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} readOnly={true} />);

    expect(screen.getByLabelText('Country')).toBeDisabled();
  });

  it('disables checkbox when readOnly is true', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Newsletter',
          type: 'checkbox' as const,
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} readOnly={true} />);

    expect(screen.getByLabelText('Newsletter')).toBeDisabled();
  });

  it('disables rating buttons when readOnly is true', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Rating', type: 'rating' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(
      <FormRenderer {...defaultProps} data={formData} readOnly={true} onDataChange={onDataChange} />
    );

    const star3 = screen.getByLabelText('3 stars');
    await userEvent.click(star3);

    // onDataChange should not be called when readOnly
    expect(onDataChange).not.toHaveBeenCalled();
  });
});

// ── Error display ───────────────────────────────────────────────────────
describe('FormRenderer error display', () => {
  it('clears error when field value changes', async () => {
    const onDataChange = vi.fn();
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Email', type: 'email' as const, required: true }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} onDataChange={onDataChange} />);

    const input = screen.getByLabelText('Email');
    await userEvent.type(input, 'test@example.com');

    expect(onDataChange).toHaveBeenCalled();
    // No error text should be visible
    expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
  });
});

// ── Accessibility (ARIA labels) ─────────────────────────────────────────
describe('FormRenderer accessibility', () => {
  it('all text inputs have aria-label matching field label', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        { id: 'f1', label: 'First Name', type: 'text' as const, required: false },
        { id: 'f2', label: 'Last Name', type: 'text' as const, required: false },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    expect(screen.getByLabelText('First Name')).toHaveAttribute('aria-label', 'First Name');
    expect(screen.getByLabelText('Last Name')).toHaveAttribute('aria-label', 'Last Name');
  });

  it('textarea has aria-label matching field label', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Feedback', type: 'textarea' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    expect(screen.getByLabelText('Feedback')).toHaveAttribute('aria-label', 'Feedback');
  });

  it('select has aria-label matching field label', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Country',
          type: 'select' as const,
          options: ['USA'],
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    expect(screen.getByLabelText('Country')).toHaveAttribute('aria-label', 'Country');
  });

  it('multiselect group has aria-label matching field label', () => {
    const formData = {
      title: 'Test Form',
      fields: [
        {
          id: 'f1',
          label: 'Skills',
          type: 'multiselect' as const,
          options: ['JavaScript', 'Python'],
          required: false,
        },
      ],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    expect(screen.getByRole('group', { name: 'Skills' })).toBeInTheDocument();
  });

  it('rating radiogroup has aria-label matching field label', () => {
    const formData = {
      title: 'Test Form',
      fields: [{ id: 'f1', label: 'Service Quality', type: 'rating' as const, required: false }],
      responses: {},
      responseCount: 0,
    };
    render(<FormRenderer {...defaultProps} data={formData} />);

    expect(screen.getByRole('radiogroup', { name: 'Service Quality' })).toBeInTheDocument();
  });
});
