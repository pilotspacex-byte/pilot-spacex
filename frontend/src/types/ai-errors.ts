/**
 * AI error types matching backend exceptions.
 *
 * Provides type-safe error handling for AI operations with:
 * - Error code classification
 * - Retryability determination
 * - User-friendly messages
 *
 * @module types/ai-errors
 * @see specs/004-mvp-agents-build/tasks/P16-T111-T120.md#T114
 */

/**
 * AI error codes matching backend AIError types.
 */
export enum AIErrorCode {
  /** Provider API error (Anthropic, OpenAI, etc.) */
  PROVIDER_ERROR = 'PROVIDER_ERROR',
  /** Rate limit exceeded - retryable */
  RATE_LIMITED = 'RATE_LIMITED',
  /** Invalid or expired API key */
  INVALID_API_KEY = 'INVALID_API_KEY',
  /** Context exceeds model limit */
  CONTEXT_TOO_LARGE = 'CONTEXT_TOO_LARGE',
  /** Action requires human approval (DD-003) */
  APPROVAL_REQUIRED = 'APPROVAL_REQUIRED',
  /** Approval request expired */
  APPROVAL_EXPIRED = 'APPROVAL_EXPIRED',
  /** Session expired - needs new session */
  SESSION_EXPIRED = 'SESSION_EXPIRED',
  /** Request timeout - retryable */
  TIMEOUT = 'TIMEOUT',
  /** Model refused to respond */
  CONTENT_FILTERED = 'CONTENT_FILTERED',
  /** Insufficient funds/quota */
  QUOTA_EXCEEDED = 'QUOTA_EXCEEDED',
  /** Unknown error */
  UNKNOWN = 'UNKNOWN',
}

/**
 * Structured AI error with classification metadata.
 */
export interface AIError {
  /** Error classification code */
  code: AIErrorCode;
  /** Human-readable error message */
  message: string;
  /** Additional error details */
  details?: Record<string, unknown>;
  /** Whether the error can be retried */
  retryable: boolean;
  /** Suggested retry delay in ms (for rate limits) */
  retryAfterMs?: number;
}

/**
 * Parse an unknown error into a structured AIError.
 *
 * Handles:
 * - Backend error responses with [CODE] prefix
 * - Standard Error objects
 * - Unknown error types
 *
 * @example
 * ```typescript
 * try {
 *   await fetchAIContext(issueId);
 * } catch (error) {
 *   const aiError = parseAIError(error);
 *   if (aiError.retryable) {
 *     // Retry logic
 *   }
 * }
 * ```
 */
export function parseAIError(error: unknown): AIError {
  // Handle null/undefined
  if (error == null) {
    return {
      code: AIErrorCode.UNKNOWN,
      message: 'An unknown error occurred',
      retryable: false,
    };
  }

  // Handle Error objects
  if (error instanceof Error) {
    // Parse backend error responses with [CODE] prefix
    const match = error.message.match(/\[([A-Z_]+)\]/);
    const codeString = match?.[1];

    if (codeString && isValidErrorCode(codeString)) {
      const code = codeString as AIErrorCode;
      const message = error.message.replace(`[${codeString}]`, '').trim();

      return {
        code,
        message: message || getDefaultMessage(code),
        retryable: isRetryableCode(code),
        retryAfterMs: code === AIErrorCode.RATE_LIMITED ? 60000 : undefined,
      };
    }

    // Check for specific error patterns
    if (error.message.includes('timeout') || error.message.includes('Timeout')) {
      return {
        code: AIErrorCode.TIMEOUT,
        message: error.message,
        retryable: true,
      };
    }

    if (error.message.includes('rate limit') || error.message.includes('429')) {
      return {
        code: AIErrorCode.RATE_LIMITED,
        message: error.message,
        retryable: true,
        retryAfterMs: 60000,
      };
    }

    // Generic error
    return {
      code: AIErrorCode.UNKNOWN,
      message: error.message,
      retryable: false,
    };
  }

  // Handle object with message property
  if (typeof error === 'object' && 'message' in error) {
    return parseAIError(new Error(String((error as { message: unknown }).message)));
  }

  // Fallback for unknown types
  return {
    code: AIErrorCode.UNKNOWN,
    message: String(error),
    retryable: false,
  };
}

/**
 * Check if an error code is valid.
 */
function isValidErrorCode(code: string): code is AIErrorCode {
  return Object.values(AIErrorCode).includes(code as AIErrorCode);
}

/**
 * Check if an error code is retryable.
 */
function isRetryableCode(code: AIErrorCode): boolean {
  return [AIErrorCode.RATE_LIMITED, AIErrorCode.TIMEOUT, AIErrorCode.PROVIDER_ERROR].includes(code);
}

/**
 * Get default message for an error code.
 */
function getDefaultMessage(code: AIErrorCode): string {
  switch (code) {
    case AIErrorCode.PROVIDER_ERROR:
      return 'AI provider error';
    case AIErrorCode.RATE_LIMITED:
      return 'Rate limit exceeded';
    case AIErrorCode.INVALID_API_KEY:
      return 'Invalid API key';
    case AIErrorCode.CONTEXT_TOO_LARGE:
      return 'Content too large';
    case AIErrorCode.APPROVAL_REQUIRED:
      return 'Approval required';
    case AIErrorCode.APPROVAL_EXPIRED:
      return 'Approval expired';
    case AIErrorCode.SESSION_EXPIRED:
      return 'Session expired';
    case AIErrorCode.TIMEOUT:
      return 'Request timed out';
    case AIErrorCode.CONTENT_FILTERED:
      return 'Content was filtered';
    case AIErrorCode.QUOTA_EXCEEDED:
      return 'Quota exceeded';
    default:
      return 'An error occurred';
  }
}

/**
 * Check if an AIError is retryable.
 */
export function isRetryableError(error: AIError): boolean {
  return error.retryable;
}

/**
 * Get user-friendly error message for display.
 *
 * @example
 * ```typescript
 * const aiError = parseAIError(error);
 * toast.error(getErrorUserMessage(aiError));
 * ```
 */
export function getErrorUserMessage(error: AIError): string {
  switch (error.code) {
    case AIErrorCode.RATE_LIMITED:
      return 'Too many requests. Please wait a moment and try again.';
    case AIErrorCode.INVALID_API_KEY:
      return 'Invalid API key. Please check your workspace AI settings.';
    case AIErrorCode.CONTEXT_TOO_LARGE:
      return 'Content is too large for AI processing. Try with a smaller selection.';
    case AIErrorCode.APPROVAL_REQUIRED:
      return 'This action requires admin approval.';
    case AIErrorCode.APPROVAL_EXPIRED:
      return 'The approval request has expired. Please try again.';
    case AIErrorCode.SESSION_EXPIRED:
      return 'Session expired. Starting a new conversation.';
    case AIErrorCode.TIMEOUT:
      return 'Request timed out. Please try again.';
    case AIErrorCode.CONTENT_FILTERED:
      return 'The AI declined to process this content.';
    case AIErrorCode.QUOTA_EXCEEDED:
      return 'AI usage quota exceeded. Please contact your administrator.';
    case AIErrorCode.PROVIDER_ERROR:
      return 'AI service temporarily unavailable. Please try again.';
    default:
      return error.message || 'An error occurred. Please try again.';
  }
}

/**
 * Create an AIError from an error code.
 *
 * @example
 * ```typescript
 * throw createAIError(AIErrorCode.APPROVAL_REQUIRED, 'This action needs approval');
 * ```
 */
export function createAIError(
  code: AIErrorCode,
  message?: string,
  details?: Record<string, unknown>
): AIError {
  return {
    code,
    message: message ?? getDefaultMessage(code),
    details,
    retryable: isRetryableCode(code),
  };
}
