/**
 * Phase 88 Plan 01 — `slimToolbar?: boolean` prop contract.
 *
 * Verifies the homepage launchpad calm-composer surface:
 *  - Default (`slimToolbar` omitted/false): full chat-mode left-cluster renders
 *    (attachments + skill / agent / section / resume menu triggers).
 *  - `slimToolbar=true`: left-cluster collapses; only the mode selector remains.
 *  - In both cases: `<ModeSelector>` (radiogroup "Conversation mode") is present.
 *
 * Maps the UI-SPEC §8 contract to the actual ChatInput.tsx left-cluster:
 *  - "Plus / attachments"  → AttachmentButton (aria-label "Attach file")
 *  - "Sliders / settings"  → not present in current file (skipped — no-op gate)
 *  - "Codebase pill"       → not present in current file (skipped — no-op gate)
 *  - "Slash trigger"       → handleInput slash branch — gated in implementation;
 *                            runtime trigger needs real-DOM selection which
 *                            jsdom does not simulate, so the gate is asserted
 *                            indirectly via the SkillMenu trigger button
 *                            disappearance (the only entry point post-Phase 87).
 *  - "Mention trigger"     → handleInput @ branch — same caveat as slash; gated
 *                            in implementation, asserted indirectly via the
 *                            AgentMenu trigger disappearance.
 *
 * @module features/ai/ChatView/ChatInput/__tests__/ChatInput.slimToolbar.test
 */

vi.mock('mobx-react-lite', () => ({
  observer: (component: unknown) => component,
}));

vi.mock('../../hooks/useSkills', () => ({
  useSkills: () => ({ skills: [] }),
}));

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

vi.mock('../../hooks/useDriveStatus', () => ({
  useDriveStatus: () => ({ data: null }),
}));

vi.mock('@/services/api/attachments', () => ({
  attachmentsApi: { getDriveAuthUrl: vi.fn() },
}));

vi.mock('../RecordButton', () => ({
  RecordButton: () => null,
}));

vi.mock('../AudioPlaybackPill', () => ({
  AudioPlaybackPill: () => null,
}));

vi.mock('../../hooks/useRecentEntities', () => ({
  useRecentEntities: () => ({
    recentEntities: [],
    addEntity: vi.fn(),
  }),
}));

vi.mock('../EntityPicker', () => ({
  EntityPicker: () => null,
}));

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import { ChatInput } from '../ChatInput';

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
});

function renderChatInput(props: { slimToolbar?: boolean } = {}) {
  return render(
    <ChatInput
      value=""
      onChange={vi.fn()}
      onSubmit={vi.fn()}
      currentMode="plan"
      onModeChange={vi.fn()}
      noteHeadings={[{ id: 'h1', level: 1, text: 'Heading', position: 0 }]}
      {...props}
    />
  );
}

describe('ChatInput — slimToolbar prop (Phase 88)', () => {
  describe('default (slimToolbar omitted)', () => {
    it('renders the attachments button', () => {
      renderChatInput();
      expect(screen.getByLabelText('Attach file')).toBeInTheDocument();
    });

    it('renders the skill, agent, section, and resume menu triggers', () => {
      renderChatInput();
      expect(screen.getByRole('button', { name: 'Open skill menu' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Open agent menu' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Reference note section' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Resume session' })).toBeInTheDocument();
    });

    it('keeps the mode selector visible', () => {
      renderChatInput();
      expect(
        screen.getByRole('radiogroup', { name: 'Conversation mode' })
      ).toBeInTheDocument();
    });
  });

  describe('slimToolbar=true', () => {
    it('hides the attachments button', () => {
      renderChatInput({ slimToolbar: true });
      expect(screen.queryByLabelText('Attach file')).not.toBeInTheDocument();
    });

    it('hides the skill, agent, section, and resume menu triggers', () => {
      renderChatInput({ slimToolbar: true });
      expect(screen.queryByRole('button', { name: 'Open skill menu' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Open agent menu' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Reference note section' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Resume session' })).not.toBeInTheDocument();
    });

    it('keeps the mode selector visible', () => {
      renderChatInput({ slimToolbar: true });
      expect(
        screen.getByRole('radiogroup', { name: 'Conversation mode' })
      ).toBeInTheDocument();
    });
  });
});
