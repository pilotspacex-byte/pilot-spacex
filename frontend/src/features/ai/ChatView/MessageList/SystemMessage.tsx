/**
 * SystemMessage — renders system-role messages in ChatView.
 *
 * System messages with structuredResult are rendered as rich cards
 * (e.g. SkillCreatorCard for skill_preview, SkillTestResultCard for test_result).
 * Plain system messages fall back to a small centered text label.
 *
 * Phase 64-04
 */

import { memo, useCallback } from 'react';
import type { ChatMessage } from '@/stores/ai/types/conversation';
import { useStore } from '@/stores';
import { SkillCreatorCard } from './SkillCreatorCard';
import { SkillTestResultCard } from './SkillTestResultCard';

interface SystemMessageProps {
  message: ChatMessage;
}

/**
 * SystemMessage — routes skill event messages to the appropriate card component.
 *
 * Uses `sendMessage` to trigger follow-up messages for onSave / onTest / onRefine:
 * - onSave → "Save this skill to my workspace" (triggers save_skill MCP tool)
 * - onTest → "Test this skill" (triggers test_skill MCP tool)
 * - onRefine → "Refine this skill based on the test feedback" (triggers update_skill MCP tool)
 *
 * This is "natural conversation" per the locked design decision — no special loop
 * infrastructure, just user messages that the agent processes normally.
 */
export const SystemMessage = memo<SystemMessageProps>(function SystemMessage({ message }) {
  const { aiStore } = useStore();
  const pilotSpace = aiStore.pilotSpace;

  const handleSkillSave = useCallback(
    (_content: string) => {
      void pilotSpace.sendMessage('Save this skill to my workspace');
    },
    [pilotSpace]
  );

  const handleSkillTest = useCallback(
    (_content: string) => {
      void pilotSpace.sendMessage('Test this skill');
    },
    [pilotSpace]
  );

  const handleSkillRefine = useCallback(() => {
    void pilotSpace.sendMessage('Refine this skill based on the test feedback');
  }, [pilotSpace]);

  const sr = message.structuredResult;

  if (sr?.schemaType === 'skill_preview') {
    const data = sr.data;
    return (
      <SkillCreatorCard
        skillName={(data['skillName'] as string) ?? ''}
        frontmatter={(data['frontmatter'] as Record<string, string>) ?? {}}
        content={(data['content'] as string) ?? ''}
        isUpdate={(data['isUpdate'] as boolean) ?? false}
        onSave={handleSkillSave}
        onTest={handleSkillTest}
      />
    );
  }

  if (sr?.schemaType === 'test_result') {
    const data = sr.data;
    return (
      <SkillTestResultCard
        skillName={(data['skillName'] as string) ?? ''}
        score={(data['score'] as number) ?? 0}
        passed={(data['passed'] as string[]) ?? []}
        failed={(data['failed'] as string[]) ?? []}
        suggestions={(data['suggestions'] as string[]) ?? []}
        sampleOutput={(data['sampleOutput'] as string) ?? ''}
        onRefine={handleSkillRefine}
      />
    );
  }

  // Generic system message fallback
  if (message.content) {
    return (
      <div className="px-4 py-2 text-xs text-center text-muted-foreground">{message.content}</div>
    );
  }

  return null;
});

SystemMessage.displayName = 'SystemMessage';
