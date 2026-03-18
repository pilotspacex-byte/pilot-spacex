import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SettingsModalProvider, useSettingsModal } from '../settings-modal-context';

function TestConsumer() {
  const { open, activeSection, openSettings, closeSettings, setActiveSection } = useSettingsModal();

  return (
    <div>
      <span data-testid="open">{String(open)}</span>
      <span data-testid="section">{activeSection}</span>
      <button data-testid="open-general" onClick={() => openSettings('general')}>
        Open General
      </button>
      <button data-testid="open-profile" onClick={() => openSettings('profile')}>
        Open Profile
      </button>
      <button data-testid="open-default" onClick={() => openSettings()}>
        Open Default
      </button>
      <button data-testid="close" onClick={() => closeSettings()}>
        Close
      </button>
      <button data-testid="set-audit" onClick={() => setActiveSection('audit')}>
        Set Audit
      </button>
    </div>
  );
}

function renderWithProvider() {
  return render(
    <SettingsModalProvider>
      <TestConsumer />
    </SettingsModalProvider>
  );
}

describe('SettingsModalContext', () => {
  it('starts closed with general section', () => {
    renderWithProvider();
    expect(screen.getByTestId('open').textContent).toBe('false');
    expect(screen.getByTestId('section').textContent).toBe('general');
  });

  it('openSettings opens modal and sets section', async () => {
    const user = userEvent.setup();
    renderWithProvider();

    await user.click(screen.getByTestId('open-profile'));

    expect(screen.getByTestId('open').textContent).toBe('true');
    expect(screen.getByTestId('section').textContent).toBe('profile');
  });

  it('openSettings defaults to general when no section given', async () => {
    const user = userEvent.setup();
    renderWithProvider();

    await user.click(screen.getByTestId('open-default'));

    expect(screen.getByTestId('open').textContent).toBe('true');
    expect(screen.getByTestId('section').textContent).toBe('general');
  });

  it('closeSettings closes the modal', async () => {
    const user = userEvent.setup();
    renderWithProvider();

    await user.click(screen.getByTestId('open-general'));
    expect(screen.getByTestId('open').textContent).toBe('true');

    await user.click(screen.getByTestId('close'));
    expect(screen.getByTestId('open').textContent).toBe('false');
  });

  it('setActiveSection changes section without affecting open state', async () => {
    const user = userEvent.setup();
    renderWithProvider();

    // Open first
    await user.click(screen.getByTestId('open-general'));
    expect(screen.getByTestId('section').textContent).toBe('general');

    // Change section
    await user.click(screen.getByTestId('set-audit'));
    expect(screen.getByTestId('section').textContent).toBe('audit');
    expect(screen.getByTestId('open').textContent).toBe('true');
  });

  it('throws when useSettingsModal is used outside provider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow(
      'useSettingsModal must be used within SettingsModalProvider'
    );
    spy.mockRestore();
  });
});
