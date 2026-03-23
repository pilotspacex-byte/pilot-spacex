/**
 * useIssueAiActions - Extracts AI action button and chat send handlers from IssueDetailPage.
 *
 * Consolidates PilotSpace store interaction logic (send message, action buttons,
 * AI generate from editor) into a single hook.
 */

import { useCallback } from 'react';

interface PilotSpaceActionAPI {
  sendMessage: (content: string) => Promise<void>;
  isStreaming: boolean;
  clearConversation: () => void;
  setIssueContext: (ctx: { issueId: string }) => void;
  setActiveSkill: (skill: string) => void;
}

interface ActionButton {
  name: string;
  binding_metadata: Record<string, unknown>;
}

interface UseIssueAiActionsOptions {
  pilotSpace: PilotSpaceActionAPI;
  issueId: string;
  setIsChatOpen: (open: boolean) => void;
}

export function useIssueAiActions({
  pilotSpace,
  issueId,
  setIsChatOpen,
}: UseIssueAiActionsOptions) {
  const handleChatSend = useCallback(
    (prompt: string) => {
      void pilotSpace.sendMessage(prompt);
    },
    [pilotSpace]
  );

  const handleAiGenerateFromEditor = useCallback(() => {
    if (pilotSpace.isStreaming) return;
    setIsChatOpen(true);
    handleChatSend(
      `Generate a detailed description for this issue. Structure it with: Problem statement, Acceptance criteria, and Technical approach.`
    );
  }, [handleChatSend, pilotSpace, setIsChatOpen]);

  const handleActionButtonClick = useCallback(
    (button: ActionButton) => {
      pilotSpace.clearConversation();
      pilotSpace.setIssueContext({ issueId });
      const skillName =
        (button.binding_metadata.skill_name as string) ??
        (button.binding_metadata.tool_name as string) ??
        button.name;
      pilotSpace.setActiveSkill(skillName);
      void pilotSpace.sendMessage(`Run ${button.name} on this issue`);
      setIsChatOpen(true);
    },
    [pilotSpace, issueId, setIsChatOpen]
  );

  return {
    handleChatSend,
    handleAiGenerateFromEditor,
    handleActionButtonClick,
  };
}
