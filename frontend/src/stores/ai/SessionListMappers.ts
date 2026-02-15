/**
 * SessionListMappers - Mapping functions for session API responses.
 * Converts snake_case backend responses to camelCase frontend types.
 *
 * @module stores/ai/SessionListMappers
 */
import type { ToolCall } from './types/conversation';
import type {
  ContextHistoryResponse,
  MessageResponse,
  SessionSummary,
  SessionSummaryResponse,
} from './types/session';

/**
 * Map a backend session summary response to a frontend SessionSummary.
 */
export function mapSessionSummary(s: SessionSummaryResponse): SessionSummary {
  return {
    sessionId: s.id,
    agentName: s.agent_name,
    contextId: s.context_id,
    contextType: s.context_type,
    contextHistory: s.context_history?.map(mapContextHistory),
    createdAt: new Date(s.created_at),
    updatedAt: new Date(s.updated_at),
    turnCount: s.turn_count,
    expiresAt: new Date(s.expires_at),
    title: s.title,
    forkedFrom: s.forked_from,
    forkCount: s.fork_count,
  };
}

/**
 * Map a backend context history entry to a frontend ContextEntry.
 */
function mapContextHistory(ctx: ContextHistoryResponse) {
  return {
    turn: ctx.turn,
    noteId: ctx.note_id,
    noteTitle: ctx.note_title,
    issueId: ctx.issue_id,
    blockIds: ctx.block_ids,
    selectedText: ctx.selected_text,
    timestamp: ctx.timestamp,
  };
}

/**
 * Map a backend message response to a frontend ChatMessage-compatible object.
 * Used by both resumeSession and loadMoreMessages to avoid duplication.
 *
 * @param msg - Backend message response
 * @param idPrefix - Prefix for fallback IDs (e.g., "restored", "restored-older-5")
 */
export function mapMessageResponse(
  msg: MessageResponse,
  idPrefix: string
): {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata: Record<string, unknown>;
  questionData?: {
    questionId: string;
    questions: Array<{
      question: string;
      options: Array<{ label: string; description?: string }>;
      multiSelect: boolean;
      header?: string;
    }>;
    answers?: Record<string, string>;
  };
  questionDataList?: Array<{
    questionId: string;
    questions: Array<{
      question: string;
      options: Array<{ label: string; description?: string }>;
      multiSelect: boolean;
      header?: string;
    }>;
    answers?: Record<string, string>;
  }>;
  contentBlocks?: Array<
    | { type: 'thinking'; blockIndex: number; content: string }
    | { type: 'text'; content: string }
    | { type: 'tool_call'; toolCallId: string }
  >;
  thinkingBlocks?: Array<{ content: string; blockIndex: number; redacted?: boolean }>;
  toolCalls?: ToolCall[];
} {
  // Reconstruct questionData and questionDataList for assistant messages with Q&A.
  // Backend may send question_data as a single dict (legacy) or a list (new).
  const rawQD = msg.role === 'assistant' ? msg.question_data : undefined;
  const questionDataList = rawQD ? normalizeQuestionData(rawQD) : undefined;
  const questionData = questionDataList?.[0];

  // Detect answer user messages (hide protocol text)
  const isAnswerMessage =
    msg.role === 'user' &&
    (/^\[ANSWER:/.test(msg.content) || /^\[User answered AI question /.test(msg.content));
  const metadata: Record<string, unknown> = { ...msg.metadata };
  if (isAnswerMessage) {
    metadata.isAnswerMessage = true;
  }

  // Map tool_calls from backend (snake_case) to frontend ToolCall (camelCase)
  const toolCalls: ToolCall[] | undefined = msg.tool_calls?.map((tc) => ({
    id: tc.id,
    name: tc.name,
    input: tc.input,
    output: tc.output,
    status: tc.status,
    errorMessage: tc.error_message,
    durationMs: tc.duration_ms,
  }));

  return {
    id: msg.id ?? idPrefix,
    role: msg.role as 'user' | 'assistant' | 'system',
    content: msg.content,
    timestamp: new Date(msg.timestamp),
    metadata,
    questionData,
    questionDataList,
    toolCalls: toolCalls?.length ? toolCalls : undefined,
    contentBlocks: msg.content_blocks?.map((block) => {
      if (block.type === 'thinking') {
        return {
          type: 'thinking' as const,
          blockIndex: block.blockIndex,
          content: block.content,
        };
      }
      if (block.type === 'text') {
        return { type: 'text' as const, content: block.content };
      }
      return { type: 'tool_call' as const, toolCallId: block.toolCallId };
    }),
    thinkingBlocks: msg.thinking_blocks?.map((block) => ({
      content: block.content,
      blockIndex: block.blockIndex,
      redacted: block.redacted,
    })),
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type RawQD = any;

/** Normalize question_data from backend (dict or list) to uniform list format. */
function normalizeQuestionData(raw: RawQD): Array<{
  questionId: string;
  questions: Array<{
    question: string;
    options: Array<{ label: string; description?: string }>;
    multiSelect: boolean;
    header?: string;
  }>;
  answers?: Record<string, string>;
}> {
  const entries: RawQD[] = Array.isArray(raw) ? raw : [raw];
  return entries.map((entry: RawQD) => ({
    questionId: entry.questionId ?? entry.question_id ?? '',
    questions: (entry.questions ?? []).map(
      (q: {
        question: string;
        options: Array<{ label: string; description?: string }>;
        multiSelect?: boolean;
        multi_select?: boolean;
        header?: string;
        skipWhen?: Array<{ questionIndex: number; selectedLabel: string }>;
        skip_when?: Array<{ questionIndex: number; selectedLabel: string }>;
      }) => {
        const options = q.options ?? [];
        // Auto-append "Other" free-text option if not present (matches backend behavior)
        const hasOther = options.some(
          (opt) => typeof opt === 'object' && /^other/i.test((opt.label ?? '').trim())
        );
        const normalizedOptions =
          hasOther || options.length === 0
            ? options
            : [...options, { label: 'Other', description: 'Provide your own answer' }];
        const skipWhen = q.skipWhen ?? q.skip_when;

        return {
          question: q.question,
          options: normalizedOptions,
          multiSelect: q.multiSelect ?? q.multi_select ?? false,
          header: q.header,
          ...(skipWhen?.length ? { skipWhen } : {}),
        };
      }
    ),
    answers: entry.answers,
  }));
}
