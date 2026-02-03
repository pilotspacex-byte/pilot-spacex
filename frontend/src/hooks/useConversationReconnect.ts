/**
 * useConversationReconnect - Handles SSE reconnection with automatic retry
 *
 * Features:
 * - Detects when user navigates back to conversation
 * - Checks job status (active, completed, waiting approval)
 * - Fetches missed events during disconnect
 * - Reconnects to SSE stream with exponential backoff
 * - Stores partial responses locally for offline viewing
 *
 * Usage:
 * ```tsx
 * const ConversationView = ({ conversationId }) => {
 *   const {
 *     status,
 *     messages,
 *     pendingApproval,
 *     reconnecting,
 *     sendMessage
 *   } = useConversationReconnect(conversationId);
 *
 *   if (status === 'WAITING_APPROVAL') {
 *     return <ApprovalDialog approval={pendingApproval} />;
 *   }
 *
 *   return <MessageList messages={messages} />;
 * };
 * ```
 */

import { useEffect, useState, useCallback, useRef } from 'react';

interface ConversationStatus {
  conversation_id: string;
  session_status: string;
  total_turns: number;
  last_activity_at: string;
  recent_turns: Message[];
  active_job: JobStatus | null;
  pending_approvals: Approval[];
}

interface JobStatus {
  job_id: string;
  conversation_id: string;
  status: 'QUEUED' | 'PROCESSING' | 'WAITING_APPROVAL' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  can_reconnect: boolean;
  stream_url?: string;
  response?: string;
  pending_approval?: Approval;
  partial_response?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  completed: boolean;
}

interface Approval {
  id: string;
  tool_name: string;
  tool_params: Record<string, unknown>;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  requested_at: string;
  timeout_at?: string;
}

interface SSEEvent {
  type: string;
  data: unknown;
  index?: number;
}

export function useConversationReconnect(conversationId: string) {
  const [status, setStatus] = useState<ConversationStatus | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [reconnecting, setReconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // SSE connection refs
  const eventSourceRef = useRef<EventSource | null>(null);
  const lastEventIndexRef = useRef(0);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Step 1: Fetch conversation status on mount or return from navigation
   */
  const fetchConversationStatus = useCallback(async () => {
    try {
      setReconnecting(true);

      const response = await fetch(`/api/v1/ai/chat/conversations/${conversationId}/status`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.statusText}`);
      }

      const data: ConversationStatus = await response.json();
      setStatus(data);
      setMessages(data.recent_turns);

      console.log('[Reconnect] Conversation status:', data.session_status);

      // Handle different states
      if (data.active_job) {
        await handleActiveJob(data.active_job);
      }

      setReconnecting(false);
    } catch (err) {
      console.error('[Reconnect] Failed to fetch status:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setReconnecting(false);
    }
  }, [conversationId]);

  /**
   * Step 2: Handle active job (processing or waiting approval)
   */
  const handleActiveJob = async (job: JobStatus) => {
    console.log('[Reconnect] Active job detected:', job.status);

    // Show partial response while reconnecting
    if (job.partial_response) {
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== 'partial'),
        {
          id: 'partial',
          role: 'assistant',
          content: job.partial_response!,
          timestamp: new Date().toISOString(),
          completed: false,
        },
      ]);
    }

    if (job.status === 'WAITING_APPROVAL') {
      // User needs to approve - no need to reconnect stream
      console.log('[Reconnect] Waiting for approval, showing UI');
      return;
    }

    if (job.status === 'PROCESSING' && job.can_reconnect && job.stream_url) {
      // Fetch missed events
      await fetchMissedEvents(job.job_id);

      // Reconnect to SSE stream
      await connectSSE(job.stream_url, job.job_id);
    }

    if (job.status === 'COMPLETED' && job.response) {
      // Job finished while user was away
      console.log('[Reconnect] Job completed, showing result');
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== 'partial'),
        {
          id: job.job_id,
          role: 'assistant',
          content: job.response!,
          timestamp: new Date().toISOString(),
          completed: true,
        },
      ]);
    }
  };

  /**
   * Step 3: Fetch events that occurred during disconnect
   */
  const fetchMissedEvents = async (jobId: string) => {
    try {
      console.log('[Reconnect] Fetching missed events from index', lastEventIndexRef.current);

      const response = await fetch(
        `/api/v1/ai/chat/stream/${jobId}/events?after_event=${lastEventIndexRef.current}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch missed events');
      }

      const data = await response.json();

      console.log('[Reconnect] Missed events:', data.missed_events);

      // Replay missed events
      data.events.forEach((event: SSEEvent) => {
        handleSSEEvent(event, jobId);

        // Update last event index
        if (event.index !== undefined) {
          lastEventIndexRef.current = Math.max(lastEventIndexRef.current, event.index);
        }
      });
    } catch (err) {
      console.error('[Reconnect] Failed to fetch missed events:', err);
      // Continue with reconnection anyway
    }
  };

  /**
   * Step 4: Connect to SSE stream with automatic retry
   */
  const connectSSE = async (streamUrl: string, jobId: string) => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    console.log('[Reconnect] Connecting to SSE:', streamUrl);

    try {
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleSSEEvent(data, jobId);

          // Store last event index for recovery
          if (data.index !== undefined) {
            lastEventIndexRef.current = data.index;
            localStorage.setItem(`last_event_${jobId}`, String(data.index));
          }

          // Reset reconnect attempts on successful event
          reconnectAttemptsRef.current = 0;
        } catch (err) {
          console.error('[Reconnect] Failed to parse SSE event:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('[Reconnect] SSE error:', err);
        eventSource.close();

        // Attempt to reconnect with exponential backoff
        scheduleReconnect(streamUrl, jobId);
      };

      eventSource.addEventListener('message_stop', () => {
        console.log('[Reconnect] Stream completed');
        eventSource.close();
      });
    } catch (err) {
      console.error('[Reconnect] Failed to connect SSE:', err);
      scheduleReconnect(streamUrl, jobId);
    }
  };

  /**
   * Step 5: Handle SSE events (update UI)
   */
  const handleSSEEvent = (event: SSEEvent, jobId: string) => {
    switch (event.type) {
      case 'message_start':
        console.log('[SSE] Message started');
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== 'partial'),
          {
            id: jobId,
            role: 'assistant',
            content: '',
            timestamp: new Date().toISOString(),
            completed: false,
          },
        ]);
        break;

      case 'text_delta':
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === jobId || msg.id === 'partial'
              ? { ...msg, content: msg.content + event.data.content }
              : msg
          )
        );
        break;

      case 'tool_use':
        console.log('[SSE] Tool use:', event.data.tool_name);
        // Could show tool indicator in UI
        break;

      case 'approval_required':
        console.log('[SSE] Approval required:', event.data);
        setStatus((prev) =>
          prev
            ? {
                ...prev,
                pending_approvals: [
                  {
                    id: event.data.approval_id,
                    tool_name: event.data.tool,
                    tool_params: event.data.params,
                    risk_level: event.data.risk_level,
                    requested_at: new Date().toISOString(),
                  },
                ],
              }
            : null
        );
        break;

      case 'message_stop':
        console.log('[SSE] Message completed');
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === jobId || msg.id === 'partial' ? { ...msg, completed: true, id: jobId } : msg
          )
        );
        break;

      case 'error':
        console.error('[SSE] Error:', event.data.message);
        setError(event.data.message);
        break;

      case 'cancelled':
        console.log('[SSE] Cancelled:', event.data.reason);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === jobId
              ? { ...msg, content: msg.content + '\n\n[Cancelled by user]', completed: true }
              : msg
          )
        );
        break;
    }
  };

  /**
   * Step 6: Schedule reconnect with exponential backoff
   */
  const scheduleReconnect = (streamUrl: string, jobId: string) => {
    reconnectAttemptsRef.current += 1;

    const maxAttempts = 5;
    if (reconnectAttemptsRef.current > maxAttempts) {
      console.error('[Reconnect] Max reconnect attempts reached');
      setError('Unable to reconnect to conversation. Please refresh the page.');
      return;
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, 16s
    const delay = Math.min(1000 * 2 ** (reconnectAttemptsRef.current - 1), 16000);

    console.log(
      `[Reconnect] Scheduling reconnect attempt ${reconnectAttemptsRef.current}/${maxAttempts} in ${delay}ms`
    );

    reconnectTimeoutRef.current = setTimeout(() => {
      console.log('[Reconnect] Attempting reconnect...');
      setReconnecting(true);
      connectSSE(streamUrl, jobId);
      setReconnecting(false);
    }, delay);
  };

  /**
   * Send a new message
   */
  const sendMessage = async (message: string) => {
    try {
      setError(null);

      // Add user message to UI
      setMessages((prev) => [
        ...prev,
        {
          id: `user-${Date.now()}`,
          role: 'user',
          content: message,
          timestamp: new Date().toISOString(),
          completed: true,
        },
      ]);

      const response = await fetch(`/api/v1/ai/chat/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify({
          message,
          stream: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.statusText}`);
      }

      const data = await response.json();

      // Reset event index for new job
      lastEventIndexRef.current = 0;
      localStorage.setItem(`last_event_${data.job_id}`, '0');

      // Connect to SSE stream
      await connectSSE(data.stream_url, data.job_id);
    } catch (err) {
      console.error('[Send] Failed to send message:', err);
      setError(err instanceof Error ? err.message : 'Failed to send message');
    }
  };

  /**
   * Approve pending tool use
   */
  const approveAction = async (
    approvalId: string,
    action: 'approve' | 'reject' | 'edit',
    modifiedParams?: Record<string, unknown>
  ) => {
    try {
      const response = await fetch(`/api/v1/ai/chat/approvals/${approvalId}/decide`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify({
          action,
          modified_params: modifiedParams,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit approval');
      }

      // Clear pending approvals
      setStatus((prev) =>
        prev
          ? {
              ...prev,
              pending_approvals: [],
            }
          : null
      );

      // Conversation will resume automatically via SSE
    } catch (err) {
      console.error('[Approval] Failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to submit approval');
    }
  };

  /**
   * Cancel active job
   */
  const cancelConversation = async () => {
    if (!status?.active_job) return;

    try {
      await fetch(`/api/v1/ai/chat/conversations/${conversationId}/cancel`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });

      // Close SSE connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    } catch (err) {
      console.error('[Cancel] Failed:', err);
    }
  };

  /**
   * Lifecycle: Fetch status on mount and cleanup on unmount
   */
  useEffect(() => {
    // Fetch status when component mounts (user navigates to page)
    fetchConversationStatus();

    // Cleanup on unmount (user navigates away)
    return () => {
      console.log('[Reconnect] Component unmounting, closing SSE');

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [conversationId]);

  /**
   * Page visibility: Reconnect when user returns to tab
   */
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('[Reconnect] Page visible again, checking status');
        fetchConversationStatus();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetchConversationStatus]);

  return {
    status: status?.session_status,
    messages,
    pendingApproval: status?.pending_approvals[0] || null,
    reconnecting,
    error,
    sendMessage,
    approveAction,
    cancelConversation,
    refetchStatus: fetchConversationStatus,
  };
}
