/**
 * Tests for PolicyTemplatePicker — clicking a template opens a confirmation
 * dialog; confirming fires the apply mutation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const applyMutate = vi.fn();

vi.mock('../../hooks/use-ai-permissions', () => ({
  useApplyPolicyTemplate: () => ({ mutate: applyMutate, isPending: false }),
}));

import { PolicyTemplatePicker } from '../policy-template-picker';

function renderPicker() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <PolicyTemplatePicker workspaceId="ws-uuid" />
    </QueryClientProvider>
  );
}

describe('PolicyTemplatePicker', () => {
  beforeEach(() => applyMutate.mockClear());

  it('renders the three template buttons', () => {
    renderPicker();
    expect(screen.getByTestId('template-conservative')).toBeInTheDocument();
    expect(screen.getByTestId('template-standard')).toBeInTheDocument();
    expect(screen.getByTestId('template-trusted')).toBeInTheDocument();
  });

  it('opens confirmation on click and fires mutation on confirm', async () => {
    const user = userEvent.setup();
    renderPicker();
    await user.click(screen.getByTestId('template-trusted'));
    // AlertDialog title appears
    expect(
      await screen.findByText(/Apply "trusted" policy template\?/i)
    ).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /apply template/i }));
    expect(applyMutate).toHaveBeenCalledTimes(1);
    expect(applyMutate.mock.calls[0]![0]).toBe('trusted');
  });

  it('does not fire mutation on cancel', async () => {
    const user = userEvent.setup();
    renderPicker();
    await user.click(screen.getByTestId('template-conservative'));
    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(applyMutate).not.toHaveBeenCalled();
  });
});
