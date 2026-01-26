/**
 * Conversation Store for multi-turn AI chat.
 *
 * Manages chat sessions with:
 * - Observable message history
 * - SSE streaming for AI responses
 * - Session lifecycle (create/resume/timeout)
 * - Message caching
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T215
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { SSEClient, type SSEEvent } from '@/lib/sse-client';
import { aiApi } from '@/services/api/ai';
import type { AIStore } from './AIStore';

export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ConversationSession {
  session_id: string;
  issue_id: string;
  created_at: string;
  expires_at: string;
}

export class ConversationStore {
  messages: ConversationMessage[] = [];
  sessionId: string | null = null;
  currentIssueId: string | null = null;
  isStreaming = false;
  currentStreamContent = '';
  error: string | null = null;

  private client: SSEClient | null = null;
  private sessionCache = new Map<string, ConversationSession>();

  constructor(_rootStore: AIStore) {
    makeAutoObservable(this);
  }

  /**
   * Start or resume conversation session for issue.
   * @param issueId - Issue UUID
   */
  async startSession(issueId: string): Promise<void> {
    // Check if we already have a session for this issue
    const cached = this.sessionCache.get(issueId);
    if (cached && new Date(cached.expires_at) > new Date()) {
      runInAction(() => {
        this.sessionId = cached.session_id;
        this.currentIssueId = issueId;
      });
      await this.loadHistory(cached.session_id);
      return;
    }

    // Create new session
    try {
      const session = await aiApi.createConversationSession(issueId);
      runInAction(() => {
        this.sessionId = session.session_id;
        this.currentIssueId = issueId;
        this.sessionCache.set(issueId, session);
        this.messages = [];
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to start session';
      });
    }
  }

  /**
   * Load conversation history for session.
   * @param sessionId - Session UUID
   */
  async loadHistory(sessionId: string): Promise<void> {
    try {
      const history = await aiApi.getConversationHistory(sessionId);
      runInAction(() => {
        this.messages = history;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load history';
      });
    }
  }

  /**
   * Send message and stream AI response.
   * @param content - User message content
   */
  async sendMessage(content: string): Promise<void> {
    if (!this.sessionId) {
      this.error = 'No active session';
      return;
    }

    // Add user message
    const userMessage: ConversationMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    runInAction(() => {
      this.messages.push(userMessage);
      this.isStreaming = true;
      this.currentStreamContent = '';
      this.error = null;
    });

    // Create SSE client for streaming response
    this.client = new SSEClient({
      url: aiApi.getConversationUrl(),
      body: {
        session_id: this.sessionId,
        message: content,
      },
      onMessage: (event: SSEEvent) => this.handleEvent(event),
      onComplete: () => {
        runInAction(() => {
          this.isStreaming = false;
          this.currentStreamContent = '';
        });
      },
      onError: (err) => {
        runInAction(() => {
          this.isStreaming = false;
          this.error = err.message;
          this.currentStreamContent = '';
        });
      },
    });

    await this.client.connect();
  }

  /**
   * Handle SSE events for streaming AI response.
   */
  private handleEvent(event: SSEEvent): void {
    runInAction(() => {
      const data = event.data as Record<string, unknown>;

      switch (event.type) {
        case 'token': {
          // Accumulate token to current stream content
          const token = data.content as string;
          this.currentStreamContent += token;
          break;
        }
        case 'complete': {
          // Add completed assistant message
          const assistantMessage: ConversationMessage = {
            id: data.message_id as string,
            role: 'assistant',
            content: this.currentStreamContent,
            created_at: new Date().toISOString(),
          };
          this.messages.push(assistantMessage);
          this.currentStreamContent = '';
          break;
        }
        case 'error': {
          this.error = data.message as string;
          this.currentStreamContent = '';
          break;
        }
      }
    });
  }

  /**
   * Abort current streaming response.
   */
  abort(): void {
    this.client?.abort();
    this.client = null;
    this.isStreaming = false;
    this.currentStreamContent = '';
  }

  /**
   * Clear current conversation session.
   */
  clearSession(): void {
    this.abort();
    this.messages = [];
    this.sessionId = null;
    this.currentIssueId = null;
    this.error = null;
  }

  /**
   * Get last message in conversation.
   */
  get lastMessage(): ConversationMessage | undefined {
    return this.messages[this.messages.length - 1];
  }

  /**
   * Get message count.
   */
  get messageCount(): number {
    return this.messages.length;
  }

  /**
   * Check if session is active and not expired.
   */
  get isSessionActive(): boolean {
    if (!this.sessionId || !this.currentIssueId) return false;

    const cached = this.sessionCache.get(this.currentIssueId);
    if (!cached) return false;

    return new Date(cached.expires_at) > new Date();
  }
}
