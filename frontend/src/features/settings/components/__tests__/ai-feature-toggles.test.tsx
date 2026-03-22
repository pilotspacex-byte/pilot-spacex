/**
 * Tests for AIFeatureToggles.
 *
 * T181: Toggle switches for ghost text, annotations, AI context, issue extraction, PR review.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

const mockSettings = {
  llmConfigured: true,
  embeddingConfigured: true,
  isSaving: false,
  ghostTextEnabled: true,
  marginAnnotationsEnabled: false,
  aiContextEnabled: true,
  settings: {
    features: {
      issueExtractionEnabled: false,
      prReviewEnabled: true,
    },
  } as Record<string, unknown> | null,
  saveSettings: vi.fn(),
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    ai: { settings: mockSettings },
  }),
}));

import { AIFeatureToggles } from '../ai-feature-toggles';

describe('AIFeatureToggles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSettings.llmConfigured = true;
    mockSettings.embeddingConfigured = true;
    mockSettings.isSaving = false;
    mockSettings.ghostTextEnabled = true;
    mockSettings.marginAnnotationsEnabled = false;
    mockSettings.aiContextEnabled = true;
    mockSettings.settings = {
      features: {
        issueExtractionEnabled: false,
        prReviewEnabled: true,
      },
    };
    mockSettings.saveSettings = vi.fn().mockResolvedValue(undefined);
  });

  it('renders all feature toggles', () => {
    render(<AIFeatureToggles />);

    expect(screen.getByText('Ghost Text Suggestions')).toBeInTheDocument();
    expect(screen.getByText('Margin Annotations')).toBeInTheDocument();
    expect(screen.getByText('AI Context Generation')).toBeInTheDocument();
    expect(screen.getByText('Issue Extraction')).toBeInTheDocument();
    expect(screen.getByText('PR Review')).toBeInTheDocument();
  });

  it('reflects correct toggle states from store', () => {
    render(<AIFeatureToggles />);

    const switches = screen.getAllByRole('switch');
    // Ghost Text = on, Margin Annotations = off, AI Context = on, Issue Extraction = off, PR Review = on
    expect(switches[0]).toBeChecked(); // Ghost Text
    expect(switches[1]).not.toBeChecked(); // Margin Annotations
    expect(switches[2]).toBeChecked(); // AI Context
    expect(switches[3]).not.toBeChecked(); // Issue Extraction
    expect(switches[4]).toBeChecked(); // PR Review
  });

  it('shows guidance message when LLM and Embedding not configured', () => {
    mockSettings.llmConfigured = false;
    mockSettings.embeddingConfigured = false;

    render(<AIFeatureToggles />);

    expect(
      screen.getByText('Configure Embedding and LLM providers above to enable features.')
    ).toBeInTheDocument();
  });

  it('shows guidance message when only LLM not configured', () => {
    mockSettings.llmConfigured = false;
    mockSettings.embeddingConfigured = true;

    render(<AIFeatureToggles />);

    expect(
      screen.getByText('Configure LLM provider above to enable features.')
    ).toBeInTheDocument();
  });

  it('shows guidance message when only Embedding not configured', () => {
    mockSettings.llmConfigured = true;
    mockSettings.embeddingConfigured = false;

    render(<AIFeatureToggles />);

    expect(
      screen.getByText('Configure Embedding provider above to enable features.')
    ).toBeInTheDocument();
  });

  it('does not show guidance message when all providers configured', () => {
    render(<AIFeatureToggles />);

    expect(screen.queryByText(/Configure .* provider/)).not.toBeInTheDocument();
  });

  it('disables toggles when providers not configured', () => {
    mockSettings.llmConfigured = false;

    render(<AIFeatureToggles />);

    const switches = screen.getAllByRole('switch');
    switches.forEach((sw) => {
      expect(sw).toBeDisabled();
    });
  });

  it('disables toggles when saving', () => {
    mockSettings.isSaving = true;

    render(<AIFeatureToggles />);

    const switches = screen.getAllByRole('switch');
    switches.forEach((sw) => {
      expect(sw).toBeDisabled();
    });
  });

  it('calls saveSettings when toggle is clicked', async () => {
    const user = userEvent.setup();
    render(<AIFeatureToggles />);

    // Click Margin Annotations toggle (currently off → on)
    const marginToggle = screen.getByLabelText('Toggle Margin Annotations');
    await user.click(marginToggle);

    expect(mockSettings.saveSettings).toHaveBeenCalledWith({
      features: { margin_annotations_enabled: true },
    });
  });

  it('has aria-labels on all toggles', () => {
    render(<AIFeatureToggles />);

    expect(screen.getByLabelText('Toggle Ghost Text Suggestions')).toBeInTheDocument();
    expect(screen.getByLabelText('Toggle Margin Annotations')).toBeInTheDocument();
    expect(screen.getByLabelText('Toggle AI Context Generation')).toBeInTheDocument();
    expect(screen.getByLabelText('Toggle Issue Extraction')).toBeInTheDocument();
    expect(screen.getByLabelText('Toggle PR Review')).toBeInTheDocument();
  });
});
