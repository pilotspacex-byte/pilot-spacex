/**
 * SystemMessage — renders system-role messages in ChatView.
 *
 * System messages with structuredResult are rendered as rich cards
 * (e.g. SkillCreatorCard for skill_preview, SkillTestResultCard for test_result).
 * Plain system messages fall back to a small centered text label.
 *
 * Phase 64-04
 */

import { memo, useCallback, useState } from 'react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import type { ChatMessage } from '@/stores/ai/types/conversation';
import { useStore } from '@/stores';
import { userSkillsApi } from '@/services/api/user-skills';
import { SkillCreatorCard } from './SkillCreatorCard';
import { SkillTestResultCard } from './SkillTestResultCard';

interface SystemMessageProps {
  message: ChatMessage;
}

/**
 * SystemMessage — routes skill event messages to the appropriate card component.
 *
 * Save calls the user-skills API directly for instant persistence.
 * Test/Refine send contextual chat messages to trigger MCP tool calls.
 */
export const SystemMessage = memo<SystemMessageProps>(function SystemMessage({ message }) {
  const { aiStore, workspaceStore } = useStore();
  const pilotSpace = aiStore.pilotSpace;
  const queryClient = useQueryClient();
  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  const sr = message.structuredResult;

  // Extract skill data once for all handlers
  const skillData = sr?.data ?? {};
  const skillName = (skillData['skillName'] as string) ?? '';

  const handleSkillSave = useCallback(
    async (content: string) => {
      const slug = workspaceStore.currentWorkspace?.slug;
      if (!slug) {
        toast.error('No workspace selected');
        return;
      }
      setIsSaving(true);
      try {
        await userSkillsApi.createUserSkill(slug, {
          skill_name: skillName,
          skill_content: content,
        });
        toast.success(`Skill "${skillName}" saved to your workspace`);
        setIsSaved(true);
        void queryClient.invalidateQueries({ queryKey: ['user-skills', slug] });
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to save skill';
        toast.error(msg);
      } finally {
        setIsSaving(false);
      }
    },
    [skillName, workspaceStore, queryClient]
  );

  const handleSkillTest = useCallback(
    (content: string) => {
      void pilotSpace.sendMessage(
        `Please test the skill "${skillName}" with this content:\n\n${content}`
      );
    },
    [pilotSpace, skillName]
  );

  const handleSkillRefine = useCallback(() => {
    const score = (skillData['score'] as number) ?? 0;
    const failed = (skillData['failed'] as string[]) ?? [];
    void pilotSpace.sendMessage(
      `Please refine the skill "${skillName}" based on the test feedback. Score: ${score}/10. Failed: ${failed.join(', ')}.`
    );
  }, [pilotSpace, skillName, skillData]);

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
        isSaving={isSaving}
        isSaved={isSaved}
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
