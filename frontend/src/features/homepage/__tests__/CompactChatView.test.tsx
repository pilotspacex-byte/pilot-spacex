import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { ChatMessage } from '@/stores/ai/types/conversation';

// Mock MobX observer as passthrough
vi.mock('mobx-react-lite', () => ({
  observer: (component: React.FC) => component,
}));

// Mock HomepageUIStore
const mockHomepageStore = {
  chatExpanded: false,
  expandChat: vi.fn(),
  collapseChat: vi.fn(),
};

const mockAIStore = {
  pilotSpace: {
    messages: [] as ChatMessage[],
    isStreaming: false,
    streamContent: '',
    error: null as string | null,
    sendMessage: vi.fn(),
    abort: vi.fn(),
    setWorkspaceId: vi.fn(),
  },
};

vi.mock('@/stores/RootStore', () => ({
  useHomepageStore: () => mockHomepageStore,
  useWorkspaceStore: () => ({
    currentWorkspace: { id: 'ws-1', slug: 'test-ws' },
  }),
  useAIStore: () => mockAIStore,
}));

// Mock StreamingContent
vi.mock('@/features/ai/ChatView/MessageList/StreamingContent', () => ({
  StreamingContent: ({ content }: { content: string }) => (
    <span data-testid="streaming-content">{content}</span>
  ),
}));

import { CompactChatView } from '../components/CompactChatView';
import { CompactChatInput } from '../components/CompactChatView/CompactChatInput';
import { CompactChatPanel } from '../components/CompactChatView/CompactChatPanel';
import { CompactMessageList } from '../components/CompactChatView/CompactMessageList';

describe('CompactChatInput', () => {
  it('renders placeholder text', () => {
    render(<CompactChatInput onFocus={vi.fn()} />);

    expect(screen.getByPlaceholderText("What's on your mind?")).toBeInTheDocument();
  });

  it('calls onFocus when input is focused', () => {
    const handleFocus = vi.fn();
    render(<CompactChatInput onFocus={handleFocus} />);

    fireEvent.focus(screen.getByRole('textbox'));
    expect(handleFocus).toHaveBeenCalledTimes(1);
  });

  it('renders keyboard hint', () => {
    render(<CompactChatInput onFocus={vi.fn()} />);

    expect(screen.getByText('[/]')).toBeInTheDocument();
  });

  it('renders disabled state with settings link', () => {
    render(<CompactChatInput onFocus={vi.fn()} disabled />);

    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('has correct aria-label', () => {
    render(<CompactChatInput onFocus={vi.fn()} />);

    expect(screen.getByLabelText('Chat with PilotSpace AI')).toBeInTheDocument();
  });
});

describe('CompactMessageList', () => {
  const mockMessages: ChatMessage[] = [
    { id: '1', role: 'user', content: 'Hello', timestamp: new Date() },
    { id: '2', role: 'assistant', content: 'Hi there!', timestamp: new Date() },
  ];

  it('renders messages', () => {
    render(<CompactMessageList messages={mockMessages} isStreaming={false} streamContent="" />);

    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
  });

  it('renders streaming content when streaming', () => {
    render(<CompactMessageList messages={[]} isStreaming={true} streamContent="Thinking..." />);

    expect(screen.getByTestId('streaming-content')).toHaveTextContent('Thinking...');
  });

  it('does not render streaming when not streaming', () => {
    render(<CompactMessageList messages={[]} isStreaming={false} streamContent="" />);

    expect(screen.queryByTestId('streaming-content')).not.toBeInTheDocument();
  });

  it('has correct ARIA attributes', () => {
    render(<CompactMessageList messages={[]} isStreaming={false} streamContent="" />);

    const log = screen.getByRole('log');
    expect(log).toHaveAttribute('aria-live', 'polite');
    expect(log).toHaveAttribute('aria-label', 'Chat messages');
  });
});

describe('CompactChatPanel', () => {
  const defaultProps = {
    messages: [] as ChatMessage[],
    isStreaming: false,
    streamContent: '',
    error: null as string | null,
    onSendMessage: vi.fn(),
    onAbort: vi.fn(),
    onMinimize: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders header with PilotSpace AI title', () => {
    render(<CompactChatPanel {...defaultProps} />);

    expect(screen.getByText('PilotSpace AI')).toBeInTheDocument();
  });

  it('calls onMinimize when minimize button is clicked', () => {
    render(<CompactChatPanel {...defaultProps} />);

    fireEvent.click(screen.getByLabelText('Minimize chat'));
    expect(defaultProps.onMinimize).toHaveBeenCalledTimes(1);
  });

  it('calls onSendMessage on Enter keypress', () => {
    render(<CompactChatPanel {...defaultProps} />);

    const textarea = screen.getByLabelText('Chat message input');
    fireEvent.change(textarea, { target: { value: 'Hello AI' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });

    expect(defaultProps.onSendMessage).toHaveBeenCalledWith('Hello AI');
  });

  it('does not send empty messages', () => {
    render(<CompactChatPanel {...defaultProps} />);

    const textarea = screen.getByLabelText('Chat message input');
    fireEvent.keyDown(textarea, { key: 'Enter' });

    expect(defaultProps.onSendMessage).not.toHaveBeenCalled();
  });

  it('calls onMinimize on Escape keypress', () => {
    render(<CompactChatPanel {...defaultProps} />);

    const textarea = screen.getByLabelText('Chat message input');
    fireEvent.keyDown(textarea, { key: 'Escape' });

    expect(defaultProps.onMinimize).toHaveBeenCalledTimes(1);
  });

  it('shows stop button when streaming', () => {
    render(<CompactChatPanel {...defaultProps} isStreaming={true} />);

    expect(screen.getByLabelText('Stop generating')).toBeInTheDocument();
  });

  it('shows send button when not streaming', () => {
    render(<CompactChatPanel {...defaultProps} />);

    expect(screen.getByLabelText('Send message')).toBeInTheDocument();
  });

  it('disables send button when input is empty', () => {
    render(<CompactChatPanel {...defaultProps} />);

    expect(screen.getByLabelText('Send message')).toBeDisabled();
  });

  it('calls onAbort when stop button is clicked', () => {
    render(<CompactChatPanel {...defaultProps} isStreaming={true} />);

    fireEvent.click(screen.getByLabelText('Stop generating'));
    expect(defaultProps.onAbort).toHaveBeenCalledTimes(1);
  });
});

describe('CompactChatView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockHomepageStore.chatExpanded = false;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders collapsed input when chat is not expanded', () => {
    render(<CompactChatView />);

    expect(screen.getByPlaceholderText("What's on your mind?")).toBeInTheDocument();
  });

  it('renders expanded panel when chat is expanded', () => {
    mockHomepageStore.chatExpanded = true;
    render(<CompactChatView />);

    // The animation state sets showPanel=true synchronously, then requestAnimationFrame for animating
    act(() => {
      vi.runAllTimers();
    });

    expect(screen.getByText('PilotSpace AI')).toBeInTheDocument();
  });

  it('collapses on Escape key', () => {
    mockHomepageStore.chatExpanded = true;
    render(<CompactChatView />);
    act(() => {
      vi.runAllTimers();
    });

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(mockHomepageStore.collapseChat).toHaveBeenCalled();
  });
});
