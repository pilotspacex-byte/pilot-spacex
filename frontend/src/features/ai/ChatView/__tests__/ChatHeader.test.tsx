/**
 * Unit tests for ChatHeader component.
 *
 * Validates:
 * - Default title renders as "PilotSpace Agent"
 * - Bot icon with correct styling
 * - onClose callback fires when X close button is clicked
 * - onNewSession callback fires when new session button is clicked
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatHeader } from '../ChatHeader';

// Mock mobx-react-lite observer to pass through the component
vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

describe('ChatHeader', () => {
  it('should render "PilotSpace Agent" as default title when no title prop is provided', () => {
    render(<ChatHeader />);

    expect(screen.getByText('PilotSpace Agent')).toBeInTheDocument();
  });

  it('should render custom title when provided', () => {
    render(<ChatHeader title="Custom Title" />);

    expect(screen.getByText('Custom Title')).toBeInTheDocument();
    expect(screen.queryByText('PilotSpace Agent')).not.toBeInTheDocument();
  });

  it('should render Bot icon in ai-muted container', () => {
    const { container } = render(<ChatHeader />);

    // Bot icon container should use flat bg-ai-muted with rounded-md
    const iconContainer = container.querySelector('.bg-ai-muted.rounded-md');
    expect(iconContainer).toBeInTheDocument();

    // Should NOT have the old purple-pink gradient
    const gradientElement = container.querySelector('.from-purple-500');
    expect(gradientElement).not.toBeInTheDocument();
  });

  it('should not render close button when onClose is not provided', () => {
    render(<ChatHeader />);

    expect(screen.queryByTestId('close-chat-button')).not.toBeInTheDocument();
  });

  it('should render close button when onClose is provided', () => {
    const handleClose = vi.fn();
    render(<ChatHeader onClose={handleClose} />);

    const closeButton = screen.getByTestId('close-chat-button');
    expect(closeButton).toBeInTheDocument();
  });

  it('should call onClose when close button is clicked', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    render(<ChatHeader onClose={handleClose} />);

    const closeButton = screen.getByTestId('close-chat-button');
    await user.click(closeButton);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('should not render new session button when onNewSession is not provided', () => {
    render(<ChatHeader />);

    expect(screen.queryByTestId('new-session-button')).not.toBeInTheDocument();
  });

  it('should render new session button when onNewSession is provided', () => {
    const handleNewSession = vi.fn();
    render(<ChatHeader onNewSession={handleNewSession} />);

    const newSessionButton = screen.getByTestId('new-session-button');
    expect(newSessionButton).toBeInTheDocument();
  });

  it('should call onNewSession when new session button is clicked', async () => {
    const user = userEvent.setup();
    const handleNewSession = vi.fn();
    render(<ChatHeader onNewSession={handleNewSession} />);

    const newSessionButton = screen.getByTestId('new-session-button');
    await user.click(newSessionButton);

    expect(handleNewSession).toHaveBeenCalledTimes(1);
  });

  it('should disable new session button when isStreaming is true', () => {
    const handleNewSession = vi.fn();
    render(<ChatHeader onNewSession={handleNewSession} isStreaming />);

    const newSessionButton = screen.getByTestId('new-session-button');
    expect(newSessionButton).toBeDisabled();
  });
});
