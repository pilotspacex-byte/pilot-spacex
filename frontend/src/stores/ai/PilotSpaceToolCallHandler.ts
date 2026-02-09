/**
 * PilotSpace Tool Call Handler - Processes tool_use, tool_result, and tool_input_delta events.
 *
 * Extracted from PilotSpaceStreamHandler to reduce file size.
 * Manages tool call lifecycle: creation, input accumulation, result processing,
 * and block ID extraction for auto-scroll.
 *
 * @module stores/ai/PilotSpaceToolCallHandler
 */
import type { ToolCall } from './types/conversation';
import type {
  ToolUseEvent,
  ToolResultEvent,
  ToolInputDeltaEvent,
  ToolAuditEvent,
  FocusBlockEvent,
} from './types/events';
import type { PilotSpaceStore } from './PilotSpaceStore';

/**
 * Tools that operate on note blocks and support early block_id extraction
 * for auto-scroll before content_update arrives.
 */
export const NOTE_TOOLS = [
  'update_note_block',
  'enhance_text',
  'write_to_note',
  'insert_block',
  'remove_block',
  'remove_content',
  'replace_content',
  'extract_issues',
  'create_issue_from_note',
] as const;

/**
 * Strip MCP server prefix from tool name.
 * e.g. "mcp__pilot-notes__update_note_block" -> "update_note_block"
 */
function stripToolPrefix(toolName: string): string {
  return toolName.includes('__') ? toolName.split('__').pop()! : toolName;
}

/**
 * Handles tool call lifecycle events from the SSE stream.
 */
export class PilotSpaceToolCallHandler {
  /** Maps content block index -> tool call ID for tool_input_delta routing */
  private _blockIndexToToolCallId = new Map<number, string>();
  /** Track tool call IDs where block_id has already been extracted from partial input */
  private _blockIdExtractedIds = new Set<string>();
  /** Tracks the last content block index seen for tool_use blocks */
  private _lastToolUseBlockIndex: number | null = null;
  /** Correlation ID for subagent tracking (G12) */
  private _lastParentToolUseId: string | null = null;

  constructor(private store: PilotSpaceStore) {}

  /** Reset all internal state for a new message. */
  resetState(): void {
    this._lastParentToolUseId = null;
    this._blockIndexToToolCallId.clear();
    this._blockIdExtractedIds.clear();
    this._lastToolUseBlockIndex = null;
  }

  /** Get the current parent tool use ID for subagent correlation. */
  get lastParentToolUseId(): string | null {
    return this._lastParentToolUseId;
  }

  /** Set the parent tool use ID from content_block_start events. */
  setParentToolUseId(id: string | null): void {
    if (id) {
      this._lastParentToolUseId = id;
    }
  }

  /** Track the block index for tool_use content blocks. */
  setLastToolUseBlockIndex(index: number): void {
    this._lastToolUseBlockIndex = index;
  }

  /** Handle tool_use -- buffers tool call for attachment on message finalization (T63). */
  handleToolUseStart(event: ToolUseEvent): void {
    const { toolCallId, toolName, toolInput } = event.data;

    // Dedup: if tool call already exists, merge input instead of duplicating.
    const existing = this.store.findPendingToolCall(toolCallId);
    if (existing) {
      if (toolInput && Object.keys(toolInput).length > 0) {
        existing.input = toolInput;
        if (!this._blockIdExtractedIds.has(toolCallId)) {
          this.tryExtractBlockIdFromInput(toolCallId, existing.name, toolInput);
        }
      }
      return;
    }

    // Create tool call entry with optional parent correlation (G12)
    const toolCall: ToolCall = {
      id: toolCallId,
      name: toolName,
      input: toolInput,
      status: 'pending',
      parentToolUseId: this._lastParentToolUseId ?? undefined,
    };

    // Map block index to tool call ID for tool_input_delta routing
    if (this._lastToolUseBlockIndex !== null) {
      this._blockIndexToToolCallId.set(this._lastToolUseBlockIndex, toolCallId);
      this._lastToolUseBlockIndex = null;
    }

    // Buffer tool call
    this.store.addPendingToolCall(toolCall);

    // Extract blockId from note-editing tools for early auto-scroll
    const strippedName = stripToolPrefix(toolName);
    if ((NOTE_TOOLS as readonly string[]).includes(strippedName)) {
      const blockId = toolInput?.block_id ?? toolInput?.blockId;
      if (typeof blockId === 'string' && !blockId.startsWith('¶')) {
        this.store.addPendingAIBlockId(blockId);
        this._blockIdExtractedIds.add(toolCallId);
      } else if (strippedName === 'write_to_note') {
        this._blockIdExtractedIds.add(toolCallId);
        this.store.requestNoteEndScroll();
      }
    }

    this.store.streamingState.phase = 'tool_use';
    this.store.streamingState.activeToolName = toolName;
  }

  /** Handle tool_result -- updates tool call status/result (T66). */
  handleToolResult(event: ToolResultEvent): void {
    this.store.streamingState.activeToolName = null;

    const { status, output, errorMessage } = event.data;
    const toolCallId = event.data.toolCallId ?? event.data.toolUseId;
    if (!toolCallId) return;

    const toolCallStatus: 'pending' | 'completed' | 'failed' =
      status === 'cancelled' ? 'failed' : status;

    // Check pending buffer first
    const pendingTc = this.store.findPendingToolCall(toolCallId);
    if (pendingTc) {
      pendingTc.status = toolCallStatus;
      pendingTc.output = output;
      if (errorMessage) {
        pendingTc.errorMessage = errorMessage;
      }

      if (event.data.toolInput && Object.keys(event.data.toolInput).length > 0) {
        pendingTc.input = event.data.toolInput;
      }

      // Parse accumulated partialInput into structured input
      if (Object.keys(pendingTc.input).length === 0 && pendingTc.partialInput) {
        try {
          pendingTc.input = JSON.parse(pendingTc.partialInput);
        } catch {
          // Incomplete JSON — leave as-is
        }
      }

      // Last-resort block_id extraction
      if (!this._blockIdExtractedIds.has(toolCallId) && Object.keys(pendingTc.input).length > 0) {
        this.tryExtractBlockIdFromInput(toolCallId, pendingTc.name, pendingTc.input);
      }
      return;
    }

    // Fallback: search finalized messages
    for (const message of this.store.messages) {
      if (message.toolCalls) {
        const toolCall = message.toolCalls.find((tc) => tc.id === toolCallId);
        if (toolCall) {
          toolCall.status = toolCallStatus;
          toolCall.output = output;
          if (errorMessage) {
            toolCall.errorMessage = errorMessage;
          }
          break;
        }
      }
    }
  }

  /** Handle tool_input_delta -- accumulates partial JSON on pending tool call (T65). */
  handleToolInputDelta(event: ToolInputDeltaEvent): void {
    const { data } = event;

    const inputText = data.inputDelta ?? data.delta ?? '';
    if (!inputText) return;

    let tc: ToolCall | undefined;
    if (data.toolUseId) {
      tc = this.store.findPendingToolCall(data.toolUseId);
    } else if (data.blockIndex !== undefined) {
      tc = this.findPendingToolCallByBlockIndex(data.blockIndex);
    }

    if (tc) {
      tc.partialInput = (tc.partialInput ?? '') + inputText;

      if (!this._blockIdExtractedIds.has(tc.id)) {
        this.tryExtractBlockIdFromDelta(tc);
      }
    }
  }

  /** Handle tool_audit -- updates tool call with duration info. */
  handleToolAudit(event: ToolAuditEvent): void {
    const { toolUseId, durationMs } = event.data;

    const pendingTc = this.store.findPendingToolCall(toolUseId);
    if (pendingTc) {
      pendingTc.durationMs = durationMs ?? undefined;
      return;
    }

    for (const message of this.store.messages) {
      if (message.toolCalls) {
        const toolCall = message.toolCalls.find((tc) => tc.id === toolUseId);
        if (toolCall) {
          toolCall.durationMs = durationMs ?? undefined;
          break;
        }
      }
    }
  }

  /**
   * Handle focus_block -- authoritative backend signal to scroll to a block.
   * Emits observable state for React to handle scrolling (no direct DOM access).
   */
  handleFocusBlock(event: FocusBlockEvent): void {
    const { blockId, scrollToEnd } = event.data;

    if (scrollToEnd) {
      this.store.requestNoteEndScroll();
      return;
    }

    if (typeof blockId === 'string' && blockId.length > 0) {
      this.store.addPendingAIBlockId(blockId);
    }
  }

  /**
   * Try to extract block_id from accumulated partial tool input.
   * Called during tool_input_delta to enable early auto-scroll.
   */
  private tryExtractBlockIdFromDelta(tc: ToolCall): void {
    const strippedName = stripToolPrefix(tc.name);
    if (!(NOTE_TOOLS as readonly string[]).includes(strippedName)) return;

    const match = tc.partialInput?.match(/"block_id"\s*:\s*"([^"]+)"/);
    if (match?.[1]) {
      this._blockIdExtractedIds.add(tc.id);
      const blockId = match[1];
      if (!blockId.startsWith('¶')) {
        this.store.addPendingAIBlockId(blockId);
      }
    }
  }

  /**
   * Extract block_id from a complete tool input object.
   * Fallback when tool_input_delta or tool_use dedup paths missed it.
   */
  private tryExtractBlockIdFromInput(
    toolCallId: string,
    toolName: string,
    toolInput: Record<string, unknown>
  ): void {
    const strippedName = stripToolPrefix(toolName);
    if (!(NOTE_TOOLS as readonly string[]).includes(strippedName)) return;

    const blockId = toolInput?.block_id ?? toolInput?.blockId;
    if (typeof blockId === 'string' && !blockId.startsWith('¶')) {
      this._blockIdExtractedIds.add(toolCallId);
      this.store.addPendingAIBlockId(blockId);
    } else if (strippedName === 'write_to_note') {
      this._blockIdExtractedIds.add(toolCallId);
      this.store.requestNoteEndScroll();
    }
  }

  /**
   * Find a pending tool call by its block index.
   * Used when tool_input_delta arrives with blockIndex instead of toolUseId.
   */
  private findPendingToolCallByBlockIndex(blockIndex: number): ToolCall | undefined {
    const toolCallId = this._blockIndexToToolCallId.get(blockIndex);
    if (toolCallId) {
      return this.store.findPendingToolCall(toolCallId);
    }
    return undefined;
  }
}
