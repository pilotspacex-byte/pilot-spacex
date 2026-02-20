/**
 * AssistantMessage - Display assistant messages with markdown support
 * Minimal design: no avatar, primary-colored agent name
 */

import { memo, useState, useCallback, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import type { ChatMessage, ContentBlock } from '@/stores/ai/types/conversation';
import type { ExtractedIssue } from '@/stores/ai/types/events';
import { useStore } from '@/stores';
import { aiApi } from '@/services/api/ai';
import { ToolCallList } from './ToolCallList';
import { ThinkingBlock } from './ThinkingBlock';
import { ReasoningGroup } from './ReasoningGroup';
import { StructuredResultCard } from './StructuredResultCard';
import { MarkdownContent } from './MarkdownContent';
import { CitationList } from './CitationList';
import { QuestionBlock, ResolvedSummary } from './QuestionBlock';

/** Check if a thinking block is the last thinking block in the content blocks sequence */
function isLastThinkingBlock(block: ContentBlock, blocks: ContentBlock[]): boolean {
  if (block.type !== 'thinking') return false;
  for (let i = blocks.length - 1; i >= 0; i--) {
    if (blocks[i]!.type === 'thinking') {
      return blocks[i]! === block;
    }
  }
  return false;
}

/** A reasoning block is a thinking or tool_call block */
function isReasoningBlock(block: ContentBlock): boolean {
  return block.type === 'thinking' || block.type === 'tool_call';
}

/** Group content blocks: consecutive reasoning blocks become groups, text blocks stand alone */
type BlockGroup =
  | { kind: 'reasoning'; blocks: ContentBlock[] }
  | { kind: 'text'; block: ContentBlock };

function groupContentBlocks(blocks: ContentBlock[]): BlockGroup[] {
  const groups: BlockGroup[] = [];
  let currentReasoning: ContentBlock[] = [];

  for (const block of blocks) {
    if (isReasoningBlock(block)) {
      currentReasoning.push(block);
    } else {
      if (currentReasoning.length > 0) {
        groups.push({ kind: 'reasoning', blocks: currentReasoning });
        currentReasoning = [];
      }
      groups.push({ kind: 'text', block });
    }
  }

  if (currentReasoning.length > 0) {
    groups.push({ kind: 'reasoning', blocks: currentReasoning });
  }

  return groups;
}

interface AssistantMessageProps {
  message: ChatMessage;
  className?: string;
}

export const AssistantMessage = memo<AssistantMessageProps>(({ message, className }) => {
  const store = useStore();
  const [isCreatingIssues, setIsCreatingIssues] = useState(false);

  const handleCreateIssues = useCallback(
    async (selectedIndices: number[]) => {
      const noteId = store.aiStore.pilotSpace.noteContext?.noteId;
      const workspaceId = store.workspaceStore.currentWorkspace?.id;

      if (!noteId || !workspaceId) {
        toast.error('Missing context', {
          description: 'Could not determine note or workspace. Please try again.',
        });
        return;
      }

      const allIssues = (message.structuredResult?.data?.issues ?? []) as ExtractedIssue[];
      const selected = selectedIndices
        .map((i) => allIssues[i])
        .filter((issue): issue is ExtractedIssue => issue !== undefined);

      if (selected.length === 0) return;

      setIsCreatingIssues(true);
      try {
        const result = await aiApi.createExtractedIssues(
          workspaceId,
          noteId,
          selected.map((issue) => ({
            title: issue.title,
            description: issue.description || undefined,
            priority: issue.priority,
            type: issue.issue_type,
            source_block_id: issue.source_block_id,
          }))
        );
        toast.success(
          `Created ${result.created_count} issue${result.created_count !== 1 ? 's' : ''}`,
          {
            description: 'Issues have been created and linked to the note.',
          }
        );
      } catch (error) {
        toast.error('Failed to create issues', {
          description: error instanceof Error ? error.message : 'An unexpected error occurred.',
        });
      } finally {
        setIsCreatingIssues(false);
      }
    },
    [store, message.structuredResult]
  );

  return (
    <div className={cn('px-4 py-3', className)} data-testid="message-assistant">
      <div className="flex items-baseline gap-2 mb-2.5">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-primary" aria-hidden="true" />
          <span className="text-[15px] font-semibold text-primary">PilotSpace Agent</span>
        </span>
        <time className="text-[11px] text-muted-foreground/70">
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </time>
      </div>

      <div className="space-y-3 overflow-hidden">
        {/* Ordered content blocks: render in server-received order when available */}
        {message.contentBlocks ? (
          <GroupedContentBlocks contentBlocks={message.contentBlocks} message={message} />
        ) : (
          <FallbackContentBlocks message={message} />
        )}

        {message.structuredResult && (
          <StructuredResultCard
            schemaType={message.structuredResult.schemaType}
            data={message.structuredResult.data}
            onCreateIssues={
              message.structuredResult.schemaType === 'extraction_result'
                ? handleCreateIssues
                : undefined
            }
            isCreatingIssues={isCreatingIssues}
          />
        )}

        {message.citations && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}

        {/* Inline question: merged wizard for questionDataList, fallback to legacy questionData */}
        {message.questionDataList && message.questionDataList.length > 0 ? (
          <MergedQuestionSection questionDataList={message.questionDataList} />
        ) : (
          <>
            {message.questionData && !message.questionData.answers && (
              <InlineQuestionBlock
                questionId={message.questionData.questionId}
                questions={message.questionData.questions}
              />
            )}
            {message.questionData?.answers && (
              <ResolvedSummaryInline
                questions={message.questionData.questions}
                answers={message.questionData.answers}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
});

AssistantMessage.displayName = 'AssistantMessage';

/** Renders content blocks grouped into reasoning sections */
const GroupedContentBlocks = memo<{
  contentBlocks: ContentBlock[];
  message: ChatMessage;
}>(function GroupedContentBlocks({ contentBlocks, message }) {
  const groups = useMemo(() => groupContentBlocks(contentBlocks), [contentBlocks]);

  return (
    <>
      {groups.map((group, gIdx) => {
        if (group.kind === 'text') {
          const block = group.block;
          if (message.questionData || message.questionDataList?.length) return null;
          if (block.type !== 'text') return null;
          return <MarkdownContent key={`text-${gIdx}`} content={block.content} />;
        }

        // Reasoning group: wrap in collapsible if 2+ steps, otherwise render inline
        const reasoningBlocks = group.blocks;
        const stepCount = reasoningBlocks.length;
        const totalDurationMs = reasoningBlocks.reduce((sum, b) => {
          if (b.type === 'thinking') return sum + (b.durationMs ?? 0);
          if (b.type === 'tool_call') {
            const tc = message.toolCalls?.find((t) => t.id === b.toolCallId);
            return sum + (tc?.durationMs ?? 0);
          }
          return sum;
        }, 0);

        const renderedBlocks = reasoningBlocks.map((block) => {
          if (block.type === 'thinking') {
            return (
              <ThinkingBlock
                key={`thinking-${block.blockIndex}`}
                content={block.content}
                durationMs={
                  block.durationMs ??
                  (isLastThinkingBlock(block, contentBlocks)
                    ? message.thinkingDurationMs
                    : undefined)
                }
                isStreaming={false}
              />
            );
          }
          if (block.type === 'tool_call') {
            const tc = message.toolCalls?.find((t) => t.id === block.toolCallId);
            return tc ? <ToolCallList key={`tool-${block.toolCallId}`} toolCalls={[tc]} /> : null;
          }
          return null;
        });

        if (stepCount >= 2) {
          return (
            <ReasoningGroup
              key={`reasoning-${gIdx}`}
              stepCount={stepCount}
              totalDurationMs={totalDurationMs}
            >
              {renderedBlocks}
            </ReasoningGroup>
          );
        }

        return <div key={`reasoning-${gIdx}`}>{renderedBlocks}</div>;
      })}
    </>
  );
});

GroupedContentBlocks.displayName = 'GroupedContentBlocks';

/** Fallback rendering for messages without contentBlocks */
const FallbackContentBlocks = memo<{ message: ChatMessage }>(function FallbackContentBlocks({
  message,
}) {
  const hasMultipleReasoningBlocks =
    (message.thinkingBlocks?.length ?? 0) + (message.toolCalls?.length ?? 0) >= 2;

  const thinkingElements =
    message.thinkingBlocks && message.thinkingBlocks.length > 0
      ? message.thinkingBlocks.map((block) => (
          <ThinkingBlock
            key={block.blockIndex}
            content={block.content}
            durationMs={
              block.durationMs ??
              (block === message.thinkingBlocks![message.thinkingBlocks!.length - 1]
                ? message.thinkingDurationMs
                : undefined)
            }
            isStreaming={false}
          />
        ))
      : message.thinkingContent
        ? [
            <ThinkingBlock
              key="single-thinking"
              content={message.thinkingContent}
              durationMs={message.thinkingDurationMs}
              isStreaming={false}
            />,
          ]
        : [];

  const toolElements =
    message.toolCalls && message.toolCalls.length > 0 ? (
      <ToolCallList toolCalls={message.toolCalls} />
    ) : null;

  const reasoningContent = (
    <>
      {thinkingElements}
      {toolElements}
    </>
  );

  const totalDurationMs =
    (message.thinkingDurationMs ?? 0) +
    (message.toolCalls?.reduce((s, t) => s + (t.durationMs ?? 0), 0) ?? 0);

  return (
    <>
      {hasMultipleReasoningBlocks ? (
        <ReasoningGroup
          stepCount={thinkingElements.length + (message.toolCalls?.length ?? 0)}
          totalDurationMs={totalDurationMs}
        >
          {reasoningContent}
        </ReasoningGroup>
      ) : (
        reasoningContent
      )}

      {message.content && !message.questionData && !message.questionDataList?.length && (
        <MarkdownContent content={message.content} />
      )}
    </>
  );
});

FallbackContentBlocks.displayName = 'FallbackContentBlocks';

/** Thin wrapper around ResolvedSummary that manages local expand/collapse state. */
const ResolvedSummaryInline = memo<{
  questions: import('@/stores/ai/types/events').AgentQuestion[];
  answers: Record<string, string>;
}>(function ResolvedSummaryInline({ questions, answers }) {
  const [isExpanded, setIsExpanded] = useState(false);
  return (
    <ResolvedSummary
      resolvedAnswers={answers}
      questions={questions}
      isExpanded={isExpanded}
      onToggle={() => setIsExpanded((v) => !v)}
    />
  );
});

ResolvedSummaryInline.displayName = 'ResolvedSummaryInline';

/** Inline QuestionBlock wrapper that wires onSubmit to PilotSpaceStore. */
const InlineQuestionBlock = memo<{
  questionId: string;
  questions: import('@/stores/ai/types/events').AgentQuestion[];
}>(function InlineQuestionBlock({ questionId, questions }) {
  const rootStore = useStore();
  const pilotSpace = rootStore.aiStore.pilotSpace;

  const handleSubmit = useCallback(
    async (_qId: string, answers: Record<string, string>) => {
      const answerText = JSON.stringify(answers);
      await pilotSpace.submitQuestionAnswer(_qId, answerText, answers);
    },
    [pilotSpace]
  );

  return (
    <QuestionBlock
      questionId={questionId}
      questions={questions}
      onSubmit={handleSubmit}
      isResolved={false}
    />
  );
});

InlineQuestionBlock.displayName = 'InlineQuestionBlock';

/** Renders merged questions from multiple ask_user calls as one wizard or resolved summary. */
const MergedQuestionSection = memo<{
  questionDataList: NonNullable<ChatMessage['questionDataList']>;
}>(function MergedQuestionSection({ questionDataList }) {
  const allQuestions = questionDataList.flatMap((qd) => qd.questions);
  const allResolved = questionDataList.every((qd) => qd.answers);
  const primaryId = questionDataList[0]?.questionId;

  if (!primaryId || allQuestions.length === 0) return null;

  if (allResolved) {
    // Merge all answers into one record for ResolvedSummary
    const mergedAnswers: Record<string, string> = {};
    let offset = 0;
    for (const qd of questionDataList) {
      if (qd.answers) {
        for (const [key, value] of Object.entries(qd.answers)) {
          // Re-key answers sequentially: q0, q1, q2, ... across all question sets
          const idx = parseInt(key.replace('q', ''), 10);
          if (!isNaN(idx)) {
            mergedAnswers[`q${offset + idx}`] = value;
          } else {
            mergedAnswers[key] = value;
          }
        }
      }
      offset += qd.questions.length;
    }
    return <ResolvedSummaryInline questions={allQuestions} answers={mergedAnswers} />;
  }

  return <InlineQuestionBlock questionId={primaryId} questions={allQuestions} />;
});

MergedQuestionSection.displayName = 'MergedQuestionSection';
