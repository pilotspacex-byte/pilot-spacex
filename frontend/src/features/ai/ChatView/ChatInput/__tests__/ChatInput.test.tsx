/**
 * Unit tests for ChatInput — contenteditable div behavior.
 *
 * Tests validate the post-migration behavioral contract:
 * - Forward slash "/" at position 0 fires onChange
 * - Backslash "\" is treated as plain text (no menu)
 * - contenteditable div has correct ARIA attributes
 * - getSerializedValue produces @[Type:uuid] for chip spans
 * - Backspace removes chip when cursor is immediately after chip
 * - Enter submits; Shift+Enter does not submit
 * - data-placeholder attribute is used instead of placeholder
 *
 * @module features/ai/ChatView/ChatInput/__tests__/ChatInput.test
 */

// Mock observer from mobx-react-lite to avoid MobX dependency in tests
vi.mock('mobx-react-lite', () => ({
  observer: (component: unknown) => component,
}));

// Mock useSkills hook — no API calls in unit tests
vi.mock('../../hooks/useSkills', () => ({
  useSkills: () => ({ skills: [] }),
}));

// Mock useAttachments hook — not relevant to trigger detection tests
vi.mock('../../hooks/useAttachments', () => ({
  useAttachments: () => ({
    attachments: [],
    attachmentIds: [],
    addFile: vi.fn(),
    addFromDrive: vi.fn(),
    removeFile: vi.fn(),
    reset: vi.fn(),
  }),
}));

// Mock useDriveStatus hook — not relevant to trigger detection tests
vi.mock('../../hooks/useDriveStatus', () => ({
  useDriveStatus: () => ({ data: null }),
}));

// Mock attachmentsApi — no network calls in unit tests
vi.mock('@/services/api/attachments', () => ({
  attachmentsApi: { getDriveAuthUrl: vi.fn() },
}));

// Mock RecordButton — uses useStore (MobX StoreProvider) which is not available in unit tests
vi.mock('../RecordButton', () => ({
  RecordButton: () => null,
}));

// Mock AudioPlaybackPill — not relevant to trigger detection tests
vi.mock('../AudioPlaybackPill', () => ({
  AudioPlaybackPill: () => null,
}));

// Mock useRecentEntities — not relevant to existing trigger detection tests
vi.mock('../../hooks/useRecentEntities', () => ({
  useRecentEntities: () => ({
    recentEntities: [],
    addEntity: vi.fn(),
  }),
}));

// Mock EntityPicker — prevents QueryClient context errors in existing tests
vi.mock('../EntityPicker', () => ({
  EntityPicker: () => null,
}));

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import { ChatInput } from '../ChatInput';

// cmdk and ResizeObserver are not available in JSDOM
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
});

function renderChatInput(
  props: {
    value?: string;
    onChange?: (v: string) => void;
    onSubmit?: (...args: unknown[]) => void;
    isDisabled?: boolean;
  } = {}
) {
  const defaultProps = {
    value: props.value ?? '',
    onChange: props.onChange ?? vi.fn(),
    onSubmit: props.onSubmit ?? vi.fn(),
    isDisabled: props.isDisabled,
  };
  return render(<ChatInput {...defaultProps} />);
}

describe('ChatInput — contenteditable div behavior', () => {
  it('calls onChange with "/" when / is typed at position 0 (first character)', () => {
    const onChange = vi.fn();
    renderChatInput({ value: '', onChange });

    const div = screen.getByTestId('chat-input');
    // Set content and dispatch input event
    div.textContent = '/';
    fireEvent.input(div);

    expect(onChange).toHaveBeenCalled();
  });

  it('does NOT open SkillMenu when / is typed mid-text', () => {
    renderChatInput({ value: 'hello' });

    const div = screen.getByTestId('chat-input');

    // Simulate typing "/" mid-sentence (not at position 0)
    div.textContent = 'hello/';
    fireEvent.input(div);

    // SkillMenu popover search input should NOT be present
    expect(screen.queryByPlaceholderText('Search skills...')).not.toBeInTheDocument();
  });

  it('treats backslash as plain text — no menu opens', () => {
    const onChange = vi.fn();
    renderChatInput({ value: '', onChange });

    const div = screen.getByTestId('chat-input');

    // Simulate typing "\" — backslash should NOT trigger SkillMenu post-migration
    div.textContent = '\\';
    fireEvent.input(div);

    // onChange called (with plain text content)
    expect(onChange).toHaveBeenCalled();

    // No skill menu popover content should appear
    expect(screen.queryByPlaceholderText('Search skills...')).not.toBeInTheDocument();
  });

  it('has placeholder text referencing / for skills', () => {
    renderChatInput();
    const div = screen.getByTestId('chat-input');
    expect(div.getAttribute('data-placeholder')).toBe(
      'Ask anything\u2026 or type / for skills'
    );
  });

  it('renders contenteditable div with correct ARIA attributes', () => {
    renderChatInput();
    const div = screen.getByTestId('chat-input');
    expect(div.getAttribute('role')).toBe('textbox');
    expect(div.getAttribute('aria-multiline')).toBe('true');
    expect(div.getAttribute('aria-label')).toBe('Chat input');
    expect(div.getAttribute('contenteditable')).toBe('true');
  });

  it('sets contentEditable to false when isDisabled is true', () => {
    render(<ChatInput value="" onChange={vi.fn()} onSubmit={vi.fn()} isDisabled />);
    const div = screen.getByTestId('chat-input');
    expect(div.getAttribute('contenteditable')).toBe('false');
  });

  it('serializes chip spans as @[Type:uuid] tokens', () => {
    const onChange = vi.fn();
    renderChatInput({ value: '', onChange });

    const div = screen.getByTestId('chat-input');
    // Manually insert a text node + chip span + text node to simulate chip state
    div.textContent = '';
    div.appendChild(document.createTextNode('Hello '));
    const chip = document.createElement('span');
    chip.setAttribute('data-entity-type', 'Note');
    chip.setAttribute('data-entity-id', 'abc-123');
    chip.setAttribute('contenteditable', 'false');
    chip.textContent = '@My Note';
    div.appendChild(chip);
    div.appendChild(document.createTextNode(' world'));

    fireEvent.input(div);

    expect(onChange).toHaveBeenCalledWith('Hello @[Note:abc-123] world');
  });

  it('removes chip on Backspace when cursor is immediately after chip', () => {
    const onChange = vi.fn();
    renderChatInput({ value: '', onChange });

    const div = screen.getByTestId('chat-input');
    // Insert chip followed by empty text node
    div.textContent = '';
    const chip = document.createElement('span');
    chip.setAttribute('data-entity-type', 'Issue');
    chip.setAttribute('data-entity-id', 'issue-456');
    chip.setAttribute('contenteditable', 'false');
    chip.textContent = '@Bug';
    div.appendChild(chip);
    const textAfter = document.createTextNode('');
    div.appendChild(textAfter);

    // Mock selection at offset 0 of the text node after the chip
    const mockRange = {
      startContainer: textAfter,
      startOffset: 0,
      collapsed: true,
    };
    const mockSelection = {
      rangeCount: 1,
      getRangeAt: () => mockRange,
      removeAllRanges: vi.fn(),
      addRange: vi.fn(),
    };
    const getSelectionSpy = vi.spyOn(window, 'getSelection').mockReturnValue(
      mockSelection as unknown as Selection
    );

    fireEvent.keyDown(div, { key: 'Backspace' });

    // Chip should be removed from DOM
    expect(div.querySelector('[data-entity-type="Issue"]')).toBeNull();
    expect(onChange).toHaveBeenCalled();

    getSelectionSpy.mockRestore();
  });

  it('submits on Enter (without Shift) when content is non-empty', () => {
    const onSubmit = vi.fn();
    renderChatInput({ value: 'hello', onSubmit });

    const div = screen.getByTestId('chat-input');
    div.textContent = 'hello';
    fireEvent.keyDown(div, { key: 'Enter', shiftKey: false });

    expect(onSubmit).toHaveBeenCalled();
  });

  it('does not submit on Shift+Enter', () => {
    const onSubmit = vi.fn();
    renderChatInput({ value: 'hello', onSubmit });

    const div = screen.getByTestId('chat-input');
    div.textContent = 'hello';
    fireEvent.keyDown(div, { key: 'Enter', shiftKey: true });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('calls onChange when /resume is typed in input', () => {
    // Regression test for: dialog opens but closes immediately when /resume selected.
    // Root cause: SkillMenu's onOpenChange focus-restore fired into SessionResumeMenu.
    // Fix: skipFocusOnSkillCloseRef prevents deferred focus when transitioning to resume menu.
    const onChange = vi.fn();
    renderChatInput({ value: '', onChange });

    const div = screen.getByTestId('chat-input');
    div.textContent = '/resume';
    fireEvent.input(div);

    expect(onChange).toHaveBeenCalled();
  });
});
