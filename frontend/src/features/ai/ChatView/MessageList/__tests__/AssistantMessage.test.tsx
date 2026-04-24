/**
 * AssistantMessage — Phase 87 Plan 03 v3 row anatomy + mode badge tests.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ChatMessage } from '@/stores/ai/types/conversation';

// Mock the store hook (AssistantMessage reads workspaceStore + aiStore)
vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: { currentWorkspace: { id: 'ws-1', slug: 'ws' } },
    aiStore: {
      pilotSpace: {
        noteContext: null,
        projectContext: null,
        sendMessage: vi.fn(),
        submitQuestionAnswer: vi.fn(),
      },
    },
  }),
}));

// Mock TanStack Query (used by skill cards)
vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

// Mock MarkdownContent so we can detect invocation
vi.mock('../MarkdownContent', () => ({
  MarkdownContent: ({ content }: { content: string }) => (
    <div data-testid="md-content">{content}</div>
  ),
}));

// Mock ToolCallList to prove pass-through
vi.mock('../ToolCallList', () => ({
  ToolCallList: ({ toolCalls }: { toolCalls: Array<{ id: string }> }) => (
    <div data-testid="tool-call-list" data-tool-count={toolCalls.length} />
  ),
}));

import { AssistantMessage } from '../AssistantMessage';

function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'a1',
    role: 'assistant',
    content: 'Hello back',
    timestamp: new Date('2026-04-24T11:00:00Z'),
    ...overrides,
  };
}

describe('AssistantMessage — v3 row anatomy (Phase 87 Plan 03)', () => {
  it('renders 32x32 white outer avatar with brand-pill inner + Sparkles icon', () => {
    const { container } = render(<AssistantMessage message={makeMessage()} />);
    const avatar = container.querySelector('[data-message-avatar]');
    expect(avatar).not.toBeNull();
    expect(avatar?.className).toContain('h-8');
    expect(avatar?.className).toContain('w-8');
    expect(avatar?.className).toContain('bg-white');
    const inner = avatar?.querySelector('[data-message-avatar-inner]');
    expect(inner).not.toBeNull();
    expect(inner?.className).toContain('bg-[#29a386]');
    // Sparkles SVG present
    expect(inner?.querySelector('svg')).not.toBeNull();
  });

  it('renders mode badge with correct tokens when message.mode === "act"', () => {
    const { container } = render(
      <AssistantMessage message={makeMessage({ mode: 'act' })} />
    );
    const badge = container.querySelector('[data-mode-badge="act"]');
    expect(badge).not.toBeNull();
    expect(badge?.textContent).toBe('ACT');
    const style = (badge as HTMLElement).style;
    expect(style.color).toBe('rgb(29, 122, 99)'); // #1d7a63
    expect(style.background).toBe('rgba(41, 163, 134, 0.12)');
    expect(badge?.className).toContain('font-mono');
    expect(badge?.className).toContain('uppercase');
  });

  it('renders mode badge with plan tokens when mode === "plan"', () => {
    const { container } = render(
      <AssistantMessage message={makeMessage({ mode: 'plan' })} />
    );
    const badge = container.querySelector('[data-mode-badge="plan"]');
    expect(badge).not.toBeNull();
    expect(badge?.textContent).toBe('PLAN');
    expect((badge as HTMLElement).style.color).toBe('rgb(100, 116, 139)'); // #64748b
  });

  it('renders mode badge with research tokens when mode === "research"', () => {
    const { container } = render(
      <AssistantMessage message={makeMessage({ mode: 'research' })} />
    );
    const badge = container.querySelector('[data-mode-badge="research"]');
    expect(badge?.textContent).toBe('RESEARCH');
    expect((badge as HTMLElement).style.color).toBe('rgb(91, 33, 182)'); // #5b21b6
  });

  it('renders mode badge with draft tokens when mode === "draft"', () => {
    const { container } = render(
      <AssistantMessage message={makeMessage({ mode: 'draft' })} />
    );
    const badge = container.querySelector('[data-mode-badge="draft"]');
    expect(badge?.textContent).toBe('DRAFT');
    expect((badge as HTMLElement).style.color).toBe('rgb(146, 64, 14)'); // #92400e
  });

  it('does NOT render mode badge when message.mode is undefined', () => {
    const { container } = render(<AssistantMessage message={makeMessage()} />);
    expect(container.querySelector('[data-mode-badge]')).toBeNull();
  });

  it('body wrapper uses 14/1.55 leading classes', () => {
    const { container } = render(<AssistantMessage message={makeMessage()} />);
    const body = container.querySelector('[data-message-body]');
    expect(body).not.toBeNull();
    expect(body?.className).toContain('text-[14px]');
    expect(body?.className).toContain('leading-[1.55]');
  });

  it('invokes MarkdownContent with message content (preserves body pipeline)', () => {
    render(<AssistantMessage message={makeMessage({ content: 'Streaming reply' })} />);
    expect(screen.getByTestId('md-content').textContent).toBe('Streaming reply');
  });

  it('preserves body slot region for tool calls / streaming / approvals (regression guard)', () => {
    // Regression guard — body wrapper must remain present so ToolCallList,
    // StreamingContent, ApprovalCardGroup all render in the same slot.
    const { container } = render(<AssistantMessage message={makeMessage()} />);
    const body = container.querySelector('[data-message-body]');
    expect(body).not.toBeNull();
    // Body retains the existing space-y-3 vertical rhythm for tool/approval cards
    expect(body?.className).toContain('space-y-3');
  });

  it('avatar carries aria-hidden (mode badge text is the SR carrier)', () => {
    const { container } = render(<AssistantMessage message={makeMessage()} />);
    const avatar = container.querySelector('[data-message-avatar]');
    expect(avatar?.getAttribute('aria-hidden')).toBe('true');
  });

  it('row container uses v3 spacing (flex gap-4 px-6 py-3)', () => {
    const { container } = render(<AssistantMessage message={makeMessage()} />);
    const row = container.querySelector('[data-message-role="assistant"]');
    expect(row).not.toBeNull();
    expect(row?.className).toContain('flex');
    expect(row?.className).toContain('gap-4');
    expect(row?.className).toContain('px-6');
    expect(row?.className).toContain('py-3');
  });

  it('renders "AI" as the author name', () => {
    const { container } = render(<AssistantMessage message={makeMessage()} />);
    const name = container.querySelector('[data-message-name]');
    expect(name?.textContent).toBe('AI');
  });
});
